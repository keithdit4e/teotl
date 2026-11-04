"""Guardrail enforcement engine. Operates at the tool execution layer."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from teotl.core.paths import teotl_home
from teotl.core.types import UI, Action, Decision, EventResult, RiskLevel, ToolCall
from teotl.primitives.guardrails.classifier import classify
from teotl.primitives.guardrails.policy import Policy
from teotl.primitives.guardrails.trust import TrustTracker

logger = logging.getLogger(__name__)


class AuditLog:
    """Append-only audit trail for guardrail decisions."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or teotl_home() / "audit.jsonl"

    def log(self, action: Action, decision: str, reason: str = "") -> None:
        """Append an audit entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action.type.value,
            "target": action.target,
            "risk": action.risk.value,
            "decision": decision,
            "reason": reason,
            "details": action.details,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")


class GuardrailEngine:
    """
    Declarative policy enforcement. No context tokens consumed.

    Hooks into the event bus via the tool_call event. Every tool call
    is classified, evaluated against the policy, and either allowed,
    confirmed with the user, or blocked.

    The LLM never sees the guardrail logic — it just gets "blocked: reason"
    as a tool result if an action is denied.
    """

    def __init__(self, policy: str | Policy | Path = "standard") -> None:
        if isinstance(policy, str):
            self.policy = Policy.from_preset(policy)
        elif isinstance(policy, Path):
            self.policy = Policy.from_file(policy)
        else:
            self.policy = policy

        trust_config = self.policy.trust_config
        self.trust = TrustTracker(
            auto_approve_after=trust_config.get("auto_approve_after", 3),
            session_scoped=trust_config.get("session_scoped", True),
            persist_patterns=trust_config.get("persist_patterns", False),
        )
        self.audit = AuditLog()
        # Risk levels declared for custom tools (Agent.register_tool(risk=...))
        self.tool_risk: dict[str, RiskLevel] = {}
        # Unattended behavior (no one to ask): "safe_zone", "refuse" or "approve"
        self.unattended_mode = "safe_zone"
        self.safe_zone: list[Path] = []
        # Per-agent rules: {"commands": {"allow": [...], "block": [...]},
        #                   "tools": {"name": "allow" | "block"}}
        self.rules: dict[str, Any] = {}
        # Tool calls approved automatically in "approve" mode (drained by Agent.run)
        self.auto_approved: list[ToolCall] = []

    def set_tool_risk(self, tool_name: str, risk: str) -> None:
        """Set the risk level guardrails use for a custom tool ("low" to "critical")."""
        self.tool_risk[tool_name] = RiskLevel(risk)

    async def evaluate(self, event: EventResult, *, ui: UI = None, **kwargs: Any) -> EventResult:
        """
        Event handler for tool_call events.

        Called by the event bus before every tool execution.
        Classifies the action, checks policy, and returns allow/block.
        """
        tool_call: ToolCall = event.data

        # 1. Classify the action
        action = classify(tool_call, tool_risk=self.tool_risk)

        # 2. Check policy, then the agent's own rules. A block rule blocks anything;
        #    an allow rule only lifts "ask first" to "allow" (it can't unblock).
        decision = self.policy.decide(action)
        rule = self._rule_decision(tool_call, action)
        if rule == Decision.BLOCK:
            decision = Decision.BLOCK
        elif rule == Decision.ALLOW and decision == Decision.CONFIRM:
            decision = Decision.ALLOW

        # 3. Apply progressive trust
        if decision == Decision.CONFIRM and self.trust.is_trusted(action):
            decision = Decision.ALLOW
            logger.debug(f"Auto-approved by trust: {action.target}")

        # 4. Execute decision
        if decision == Decision.BLOCK:
            reason = (
                f"`{tool_call.name}` is blocked by this agent's rules"
                if rule == Decision.BLOCK
                else self.policy.block_reason(action)
            )
            self.audit.log(action, "blocked", reason)
            logger.info(f"Blocked: {reason}")
            return EventResult(data=tool_call, blocked=True, reason=reason)

        if decision == Decision.CONFIRM and getattr(ui, "unattended", False):
            return self._decide_unattended(action, tool_call)

        if decision == Decision.CONFIRM:
            if ui is None:
                # No UI available — block by default (safe-by-default)
                reason = "Action requires confirmation but no UI available"
                self.audit.log(action, "blocked_no_ui", reason)
                return EventResult(data=tool_call, blocked=True, reason=reason)

            description = self._describe_action(action, tool_call)
            approved = await ui.confirm(f"🛡️ {description}")

            if approved:
                self.trust.record_approval(action)
                self.audit.log(action, "approved_by_user")
                return EventResult(data=tool_call, blocked=False)
            else:
                self.audit.log(action, "denied_by_user")
                return EventResult(data=tool_call, blocked=True, reason="Denied by user")

        # Allow
        self.audit.log(action, "allowed")
        return EventResult(data=tool_call, blocked=False)

    def _rule_decision(self, tool_call: ToolCall, action: Action) -> Decision | None:
        """The agent's own allow/block rules for this call, if any match."""
        if not self.rules:
            return None
        tool_rule = (self.rules.get("tools") or {}).get(tool_call.name)
        if tool_rule in ("allow", "block"):
            return Decision.ALLOW if tool_rule == "allow" else Decision.BLOCK
        if tool_call.name == "bash":
            command = str(tool_call.args.get("command", "")).strip()
            commands = self.rules.get("commands") or {}
            if any(fnmatch(command, p) for p in commands.get("block", [])):
                return Decision.BLOCK
            if any(fnmatch(command, p) for p in commands.get("allow", [])):
                return Decision.ALLOW
        return None

    def _decide_unattended(self, action: Action, tool_call: ToolCall) -> EventResult:
        """An "ask first" action with nobody to ask."""
        from teotl.primitives.guardrails.unattended import inside_safe_zone

        if self.unattended_mode == "approve":
            self.audit.log(action, "auto_approved_unattended")
            self.auto_approved.append(tool_call)
            logger.warning(f"Auto-approved without asking (unattended: approve): {action.target}")
            return EventResult(data=tool_call, blocked=False)

        if self.unattended_mode == "safe_zone":
            inside, why = inside_safe_zone(tool_call.name, tool_call.args, self.safe_zone)
            if inside:
                self.audit.log(action, "allowed_safe_zone")
                return EventResult(data=tool_call, blocked=False)
            reason = (
                f"Refused: this needs confirmation and no one is watching ({why}). "
                "Allow it in the agent's rules, or add its folder to safe_zone."
            )
        else:
            reason = (
                "Refused: this needs confirmation and no one is watching (unattended: refuse)."
            )
        self.audit.log(action, "refused_unattended", reason)
        logger.info(reason)
        return EventResult(data=tool_call, blocked=True, reason=reason)

    def _describe_action(self, action: Action, tool_call: ToolCall) -> str:
        """Generate a human-readable description of the action."""
        if tool_call.name == "bash":
            cmd = tool_call.args.get("command", "")
            if len(cmd) > 80:
                cmd = cmd[:77] + "..."
            return f"Run command: {cmd}"
        elif action.type.value == "write":
            return f"Write to: {action.target}"
        elif action.type.value == "network":
            host = action.details.get("host", action.target)
            return f"Network access: {host}"
        elif action.type.value == "destructive":
            return f"⚠️  Destructive: {action.target}"
        else:
            return f"Execute: {tool_call.name}({', '.join(f'{k}={v}' for k, v in tool_call.args.items())})"

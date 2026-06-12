"""Guardrail enforcement engine. Operates at the tool execution layer."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from teotl.core.types import UI, Action, Decision, EventResult, ToolCall
from teotl.primitives.guardrails.classifier import classify
from teotl.primitives.guardrails.policy import Policy
from teotl.primitives.guardrails.trust import TrustTracker

logger = logging.getLogger(__name__)


class AuditLog:
    """Append-only audit trail for guardrail decisions."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".forge" / "audit.jsonl"

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

    async def evaluate(self, event: EventResult, *, ui: UI = None, **kwargs: Any) -> EventResult:
        """
        Event handler for tool_call events.

        Called by the event bus before every tool execution.
        Classifies the action, checks policy, and returns allow/block.
        """
        tool_call: ToolCall = event.data

        # 1. Classify the action
        action = classify(tool_call)

        # 2. Check policy
        decision = self.policy.decide(action)

        # 3. Apply progressive trust
        if decision == Decision.CONFIRM and self.trust.is_trusted(action):
            decision = Decision.ALLOW
            logger.debug(f"Auto-approved by trust: {action.target}")

        # 4. Execute decision
        if decision == Decision.BLOCK:
            reason = self.policy.block_reason(action)
            self.audit.log(action, "blocked", reason)
            logger.info(f"Blocked: {reason}")
            return EventResult(data=tool_call, blocked=True, reason=reason)

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

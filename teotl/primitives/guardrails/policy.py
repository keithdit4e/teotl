"""Declarative policy definition and loading."""

from __future__ import annotations

import json
import logging
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from teotl.core.types import Action, ActionType, Decision

logger = logging.getLogger(__name__)


class Policy:
    """
    Declarative guardrail policy. Loaded from JSON, preset name, or dict.

    Determines whether an action should be allowed, require confirmation,
    or be blocked entirely. Zero context cost — operates outside the prompt.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.level: str = config.get("level", "standard")
        self.filesystem = config.get("filesystem", {})
        self.bash = config.get("bash", {})
        self.network = config.get("network", {})
        self.integrations = config.get("integrations", {})
        self.limits = config.get("limits", {})
        self.trust_config = config.get("trust", {})
        self._raw = config

    # -------------------------------------------------------------------
    # Factory methods
    # -------------------------------------------------------------------

    @classmethod
    def from_preset(cls, name: str) -> Policy:
        """Load a built-in preset: minimal, standard, or strict."""
        from teotl.primitives.guardrails.presets import PRESETS

        if name not in PRESETS:
            raise ValueError(f"Unknown preset: {name}. Available: {list(PRESETS.keys())}")
        return cls(PRESETS[name])

    @classmethod
    def from_file(cls, path: Path | str) -> Policy:
        """Load policy from a JSON or YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Policy file not found: {path}")

        with open(path) as f:
            # Try YAML first if extension suggests it
            if path.suffix in (".yaml", ".yml"):
                try:
                    import yaml

                    return cls(yaml.safe_load(f))
                except ImportError:
                    raise ImportError("PyYAML not installed. Install with: pip install pyyaml")
            # Otherwise try JSON
            else:
                return cls(json.load(f))

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> Policy:
        """Create policy from a dictionary."""
        return cls(config)

    # -------------------------------------------------------------------
    # Decision logic
    # -------------------------------------------------------------------

    def decide(self, action: Action) -> Decision:
        """
        Evaluate an action against the policy.

        Returns:
            Decision.ALLOW - proceed without asking
            Decision.CONFIRM - ask user before proceeding
            Decision.BLOCK - refuse to execute
        """
        # Check filesystem rules
        if action.type in (ActionType.READ, ActionType.WRITE) and action.target:
            fs_decision = self._check_filesystem(action)
            if fs_decision is not None:
                return fs_decision

        # Check bash rules
        if action.type == ActionType.EXECUTE:
            bash_decision = self._check_bash(action)
            if bash_decision is not None:
                return bash_decision

        # Check network rules
        if action.type == ActionType.NETWORK:
            net_decision = self._check_network(action)
            if net_decision is not None:
                return net_decision

        # Check integration-specific rules
        integration = action.details.get("integration")
        if integration:
            int_decision = self._check_integration(integration, action)
            if int_decision is not None:
                return int_decision

        # Default by risk level
        return self._default_for_risk(action)

    def block_reason(self, action: Action) -> str:
        """Human-readable reason for blocking an action."""
        if action.type == ActionType.DESTRUCTIVE:
            return f"Destructive action blocked by policy: {action.target}"
        if action.target:
            return f"Action on '{action.target}' blocked by {self.level} policy"
        return f"Action blocked by {self.level} policy"

    # -------------------------------------------------------------------
    # Rule checkers
    # -------------------------------------------------------------------

    def _check_filesystem(self, action: Action) -> Decision | None:
        """Check filesystem allow/deny rules."""
        target = str(Path(action.target).expanduser())

        # Deny list takes priority
        for pattern in self.filesystem.get("deny", []):
            pattern = str(Path(pattern).expanduser())
            if fnmatch(target, pattern):
                return Decision.BLOCK

        # Allow list
        for pattern in self.filesystem.get("allow", []):
            pattern = str(Path(pattern).expanduser())
            if fnmatch(target, pattern):
                if action.type == ActionType.WRITE and self.filesystem.get(
                    "confirm_write_outside_scope"
                ):
                    return Decision.CONFIRM
                return Decision.ALLOW

        # Not in any list — confirm writes, allow reads
        if action.type == ActionType.WRITE:
            return Decision.CONFIRM
        return None  # Fall through to default

    def _check_bash(self, action: Action) -> Decision | None:
        """Check bash command rules."""
        command = action.details.get("command", "")
        primary = action.details.get("primary_command", "")

        # Block list (exact patterns)
        for pattern in self.bash.get("block", []):
            if pattern.endswith("*"):
                if command.startswith(pattern[:-1]):
                    return Decision.BLOCK
            elif pattern in command:
                return Decision.BLOCK

        # Allow list (primary command)
        for allowed in self.bash.get("allow", []):
            if primary == allowed:
                return Decision.ALLOW

        # Confirm list (primary command)
        for confirm_cmd in self.bash.get("confirm", []):
            if primary == confirm_cmd:
                return Decision.CONFIRM

        return None  # Fall through to default

    def _check_network(self, action: Action) -> Decision | None:
        """Check network access rules."""
        if not self.network.get("allow_outbound", True):
            host = action.details.get("host", "")
            if host in self.network.get("allowed_hosts", []):
                return Decision.ALLOW
            if self.network.get("confirm_new_hosts", True):
                return Decision.CONFIRM
            return Decision.BLOCK
        return None

    def _check_integration(self, integration: str, action: Action) -> Decision | None:
        """Check integration-specific rules."""
        rules = self.integrations.get(integration, {})
        operation = action.details.get("operation", "")

        if operation in rules:
            decision_str = rules[operation]
            return Decision(decision_str)

        return None

    def _default_for_risk(self, action: Action) -> Decision:
        """Default decision based on risk level and policy strictness."""
        from teotl.core.types import RiskLevel

        defaults = {
            "minimal": {
                RiskLevel.LOW: Decision.ALLOW,
                RiskLevel.MEDIUM: Decision.ALLOW,
                RiskLevel.HIGH: Decision.CONFIRM,
                RiskLevel.CRITICAL: Decision.CONFIRM,
            },
            "standard": {
                RiskLevel.LOW: Decision.ALLOW,
                RiskLevel.MEDIUM: Decision.CONFIRM,
                RiskLevel.HIGH: Decision.CONFIRM,
                RiskLevel.CRITICAL: Decision.BLOCK,
            },
            "strict": {
                RiskLevel.LOW: Decision.CONFIRM,
                RiskLevel.MEDIUM: Decision.CONFIRM,
                RiskLevel.HIGH: Decision.BLOCK,
                RiskLevel.CRITICAL: Decision.BLOCK,
            },
        }

        level_defaults = defaults.get(self.level, defaults["standard"])
        return level_defaults.get(action.risk, Decision.CONFIRM)

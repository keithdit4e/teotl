"""Progressive trust: reduce confirmation fatigue over time."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from teotl.core.types import Action


@dataclass
class TrustRecord:
    """Record of user approvals for a pattern."""

    pattern: str
    approvals: int = 0
    last_approved: datetime | None = None


class TrustTracker:
    """
    Tracks user approvals to reduce confirmation fatigue.

    After a user approves the same type of action N times,
    the tracker auto-approves similar future actions.

    Trust is session-scoped by default (resets between sessions).
    Can optionally persist patterns across sessions.
    """

    def __init__(
        self,
        auto_approve_after: int = 3,
        session_scoped: bool = True,
        persist_patterns: bool = False,
    ) -> None:
        self.auto_approve_after = auto_approve_after
        self.session_scoped = session_scoped
        self.persist_patterns = persist_patterns
        self._records: dict[str, TrustRecord] = defaultdict(lambda: TrustRecord(pattern=""))

    def is_trusted(self, action: Action) -> bool:
        """Check if this action pattern has been approved enough times."""
        pattern = self._action_to_pattern(action)
        record = self._records.get(pattern)
        if record is None:
            return False
        return record.approvals >= self.auto_approve_after

    def record_approval(self, action: Action) -> None:
        """Record that the user approved this action."""
        pattern = self._action_to_pattern(action)
        if pattern not in self._records:
            self._records[pattern] = TrustRecord(pattern=pattern)
        self._records[pattern].approvals += 1
        self._records[pattern].last_approved = datetime.now()

    def reset(self) -> None:
        """Reset all trust records (e.g., at session start)."""
        self._records.clear()

    def _action_to_pattern(self, action: Action) -> str:
        """
        Convert an action to a trust pattern.

        Patterns are generalized to match similar actions:
        - "bash:git push" (specific command)
        - "write:~/projects" (write to a directory)
        - "network:api.github.com" (network access to a host)
        """
        if action.type.value == "execute":
            cmd = action.details.get("primary_command", action.target)
            return f"bash:{cmd}"
        elif action.type.value in ("read", "write"):
            # Generalize to parent directory
            from pathlib import Path

            target = action.target
            try:
                parent = str(Path(target).parent)
            except Exception:
                parent = target
            return f"{action.type.value}:{parent}"
        elif action.type.value == "network":
            host = action.details.get("host", action.target)
            return f"network:{host}"
        else:
            return f"{action.type.value}:{action.target}"

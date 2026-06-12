"""Undo extension: file snapshot and rollback."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ulid

from teotl.primitives.guardrails.classifier import classify

if TYPE_CHECKING:
    from teotl.core.types import EventResult

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    original: Path
    backup: Path
    timestamp: datetime
    tool_call_id: str = ""


class UndoExtension:
    """
    Snapshots files before write operations and provides /undo rollback.

    Hooks into tool_call to snapshot before writes,
    and registers /undo as a slash command.
    """

    name = "undo"
    version = "1.0.0"

    def __init__(self, snapshot_dir: Path | None = None, max_snapshots: int = 50) -> None:
        self.snapshot_dir = snapshot_dir or Path.home() / ".forge" / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.max_snapshots = max_snapshots
        self.snapshots: list[Snapshot] = []

    def activate(self, agent: Any) -> None:
        agent.events.on("tool_call", self._snapshot_before_write, priority=-10)
        agent.register_command("/undo", self._undo_command)

    def deactivate(self, agent: Any) -> None:
        agent.events.off("tool_call", self._snapshot_before_write)

    async def _snapshot_before_write(self, event: EventResult, **kwargs: Any) -> EventResult:
        """Take a snapshot before write/destructive operations."""
        if event.blocked:
            return event  # Already blocked, no need to snapshot

        tool_call = event.data
        action = classify(tool_call)

        if action.type.value in ("write", "destructive"):
            target = Path(action.target).expanduser()
            if target.exists() and target.is_file():
                try:
                    snapshot_name = f"{ulid.new().str}-{target.name}"
                    snapshot_path = self.snapshot_dir / snapshot_name
                    shutil.copy2(target, snapshot_path)

                    self.snapshots.append(
                        Snapshot(
                            original=target,
                            backup=snapshot_path,
                            timestamp=datetime.now(),
                            tool_call_id=tool_call.id,
                        )
                    )

                    # Enforce max snapshots
                    while len(self.snapshots) > self.max_snapshots:
                        old = self.snapshots.pop(0)
                        old.backup.unlink(missing_ok=True)

                    logger.debug(f"Snapshot: {target} → {snapshot_path}")
                except Exception as e:
                    logger.warning(f"Failed to snapshot {target}: {e}")

        return event

    async def _undo_command(self, args: str, ui: Any) -> str:
        """Handle /undo command."""
        if not self.snapshots:
            return "Nothing to undo."

        snapshot = self.snapshots.pop()
        try:
            shutil.copy2(snapshot.backup, snapshot.original)
            snapshot.backup.unlink(missing_ok=True)
            return f"✅ Restored `{snapshot.original}` to state before last edit."
        except Exception as e:
            return f"❌ Failed to restore: {e}"

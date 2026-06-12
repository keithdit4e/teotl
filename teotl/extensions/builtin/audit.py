"""Audit extension: append-only activity logging."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teotl.core.types import EventResult

logger = logging.getLogger(__name__)


class AuditExtension:
    """
    Logs all tool calls and their results to an append-only JSONL file.

    Useful for debugging, compliance, and understanding agent behavior.
    """

    name = "audit"
    version = "1.0.0"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".forge" / "audit.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def activate(self, agent: Any) -> None:
        agent.events.on("tool_call", self._log_tool_call, priority=100)
        agent.events.on("tool_result", self._log_tool_result, priority=100)
        agent.events.on("error", self._log_error, priority=100)

    def deactivate(self, agent: Any) -> None:
        agent.events.off("tool_call", self._log_tool_call)
        agent.events.off("tool_result", self._log_tool_result)
        agent.events.off("error", self._log_error)

    async def _log_tool_call(self, event: EventResult, **kwargs: Any) -> EventResult:
        tool_call = event.data
        self._write(
            {
                "type": "tool_call",
                "timestamp": datetime.now().isoformat(),
                "tool": tool_call.name,
                "args": tool_call.args,
                "blocked": event.blocked,
                "reason": event.reason,
            }
        )
        return event

    async def _log_tool_result(self, event: EventResult, **kwargs: Any) -> EventResult:
        result = event.data
        self._write(
            {
                "type": "tool_result",
                "timestamp": datetime.now().isoformat(),
                "call_id": result.call_id if hasattr(result, "call_id") else "",
                "is_error": result.is_error if hasattr(result, "is_error") else False,
                "output_length": len(str(result.output)) if hasattr(result, "output") else 0,
            }
        )
        return event

    async def _log_error(self, event: EventResult, **kwargs: Any) -> EventResult:
        self._write(
            {
                "type": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(event.data),
            }
        )
        return event

    def _write(self, entry: dict) -> None:
        try:
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Audit write failed: {e}")

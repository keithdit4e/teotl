"""A saved record of each MCP server's tools, so changes don't slip through.

MCP servers can add tools, drop them, or change a tool behind the same name
(its description, arguments or annotations) at any time, including mid-session.
Approving a server once shouldn't approve whatever it turns into later, so
Teotl keeps an inventory per server: each tool's name and a fingerprint of what
it advertises.

Every time a server's tool list is read (on connect, when the server says its
list changed, and on a timer) it is compared with the inventory:

- the first list Teotl sees from a server is its baseline and is approved
  (``review="changes"``, the default), or held for review (``review="all"``);
- a tool that appears later is **held**: guardrails ask first, or refuse when
  no one is watching, and allow rules don't apply to it;
- a tool whose fingerprint changed is held again, even if it was approved;
- a tool that disappears is dropped; if it comes back unchanged it's approved.

Held tools stay held until approved: ``teotl mcp approve server.tool``, a handler
on the agent's ``mcp_tools_changed`` event, or the server's ``auto_approve``
patterns. Blocked tools (``teotl mcp block``) are never called.

The inventory lives at ``~/.teotl/mcp/tool_inventory.json``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from fnmatch import fnmatch
from typing import TYPE_CHECKING, Any

from teotl.core.paths import teotl_home

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

REVIEW_MODES = ("changes", "all", "off")
APPROVED, PENDING, BLOCKED = "approved", "pending", "blocked"


def fingerprint(description: str, schema: Any, annotations: Any) -> str:
    """A hash of everything a tool advertises."""
    payload = json.dumps(
        {"description": description, "schema": schema, "annotations": annotations},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class ToolChanges:
    """What changed in one server's tool list since the inventory last saw it."""

    server: str
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    held: list[str] = field(default_factory=list)  # tools now waiting for approval
    baseline: bool = False  # the first list seen from this server
    _bridge: Any = field(default=None, repr=False, compare=False)

    def __bool__(self) -> bool:
        return bool(self.added or self.changed or self.removed)

    def approve(self, tool: str) -> None:
        """Approve a held tool (by name, or a pattern like ``read_*``)."""
        self._apply(tool, APPROVED)

    def block(self, tool: str) -> None:
        """Block a tool so it is never called."""
        self._apply(tool, BLOCKED)

    def _apply(self, tool: str, status: str) -> None:
        if self._bridge is None:
            raise RuntimeError("These changes aren't attached to a connected MCP bridge")
        self._bridge.set_status(self.server, tool, status)

    def summary(self) -> str:
        parts = []
        for label, names in (
            ("new", self.added),
            ("changed", self.changed),
            ("removed", self.removed),
        ):
            if names:
                parts.append(f"{label}: {', '.join(names)}")
        return f"MCP server {self.server}: " + ("; ".join(parts) or "no changes")


class ToolInventory:
    """The approved tools of every MCP server, kept on disk between runs."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or teotl_home() / "mcp" / "tool_inventory.json"
        self._data: dict[str, Any] = {"servers": {}}
        self.load()

    # -- storage ----------------------------------------------------------

    def load(self) -> None:
        """Re-read the file (picks up `teotl mcp approve` from another process)."""
        try:
            data = json.loads(self.path.read_text())
            if isinstance(data, dict) and isinstance(data.get("servers"), dict):
                self._data = data
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as e:
            logger.error(f"Could not read the MCP tool inventory {self.path}: {e}")

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".inventory-")
            with os.fdopen(fd, "w") as f:
                json.dump(self._data, f, indent=1, sort_keys=True)
            os.replace(tmp, self.path)
        except OSError as e:
            logger.error(f"Could not save the MCP tool inventory {self.path}: {e}")

    def servers(self) -> dict[str, Any]:
        return self._data["servers"]

    def tools(self, server: str) -> dict[str, dict[str, Any]]:
        return (self.servers().get(server) or {}).get("tools", {})

    # -- review -----------------------------------------------------------

    def review(
        self,
        server: str,
        identity: str,
        tools: dict[str, dict[str, Any]],
        *,
        mode: str = "changes",
        auto_approve: list[str] | None = None,
    ) -> ToolChanges:
        """Compare a fresh tool list with the inventory and record it.

        ``tools`` maps each tool's name to ``{"fingerprint", "description", "risk"}``.
        """
        self.load()
        now = datetime.now().isoformat(timespec="seconds")
        record = self.servers().get(server)
        changes = ToolChanges(server=server)
        if record is None or record.get("identity") != identity:
            if record is not None:
                logger.warning(
                    f"MCP server {server!r} now runs something else ({identity}); "
                    "starting its tool inventory again"
                )
            record = {"identity": identity, "first_seen": now, "tools": {}}
            self.servers()[server] = record
            changes.baseline = True
        known: dict[str, dict[str, Any]] = record["tools"]

        for name, info in tools.items():
            entry = known.get(name)
            if entry is None:
                status = APPROVED if changes.baseline and mode == "changes" else PENDING
                entry = known[name] = {
                    "status": status,
                    "reason": "new",
                    "first_seen": now,
                    "approved_fingerprint": info["fingerprint"] if status == APPROVED else None,
                }
                if not changes.baseline:
                    changes.added.append(name)
            elif entry.get("removed"):
                changes.added.append(name)
            if (
                entry.get("status") == APPROVED
                and entry.get("approved_fingerprint") != info["fingerprint"]
            ):
                entry["status"], entry["reason"] = PENDING, "changed"
                if name not in changes.added:
                    changes.changed.append(name)
            elif (
                entry.get("status") == PENDING
                and entry.get("fingerprint") not in (None, info["fingerprint"])
                and name not in changes.added
            ):
                changes.changed.append(name)  # changed again while waiting
            if entry.get("status") == PENDING and any(fnmatch(name, p) for p in auto_approve or []):
                entry["status"], entry["approved_fingerprint"] = APPROVED, info["fingerprint"]
                entry["approved_by"] = "auto_approve"
            entry.update(
                fingerprint=info["fingerprint"],
                description=(info.get("description") or "").split("\n", 1)[0][:200],
                risk=info.get("risk"),
                last_seen=now,
                removed=False,
            )
            if entry["status"] == PENDING:
                changes.held.append(name)

        for name, entry in known.items():
            if name not in tools and not entry.get("removed"):
                entry["removed"] = True
                entry["removed_at"] = now
                changes.removed.append(name)

        record["last_checked"] = now
        self.save()
        return changes

    def status(self, server: str, tool: str) -> str | None:
        entry = self.tools(server).get(tool)
        return None if entry is None else entry.get("status")

    def set_status(self, server: str, pattern: str, status: str) -> list[str]:
        """Approve or block tools by name or pattern. Returns the tools changed."""
        if status not in (APPROVED, PENDING, BLOCKED):
            raise ValueError(f"Invalid status {status!r}")
        self.load()
        matched = []
        for name, entry in self.tools(server).items():
            if fnmatch(name, pattern):
                entry["status"] = status
                if status == APPROVED:
                    entry["approved_fingerprint"] = entry.get("fingerprint")
                    entry["approved_by"] = "user"
                entry["status_changed"] = datetime.now().isoformat(timespec="seconds")
                matched.append(name)
        if matched:
            self.save()
        return matched

    def forget(self, server: str) -> bool:
        """Drop a server's inventory; its next tool list becomes the baseline."""
        self.load()
        if self.servers().pop(server, None) is None:
            return False
        self.save()
        return True

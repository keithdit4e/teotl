"""Use tools from MCP servers, without filling the prompt with their schemas.

An MCP server can expose dozens of tools, each with a JSON schema. Loading them
all costs thousands of tokens on every model call. In ``compact`` mode (the
default) the agent gets two tools instead:

- ``mcp_discover(server, tool?)``: list a server's tools (one line each), or show
  one tool's full schema;
- ``mcp_execute(server, tool, args)``: call a tool.

``full`` mode registers every MCP tool directly (``server__tool``), which suits
small servers and models that do better with real schemas.

Guardrails see the real MCP tool (``server.tool``) on every call, not a generic
``mcp_execute``. Its risk comes from your ``risk`` settings, else from the
server's tool annotations: read-only tools are low risk, tools marked
non-destructive are medium, and everything else is high (ask first). Annotations
are hints from the server, so set ``risk`` for servers you don't trust.

Tool lists are checked against a saved inventory (see ``mcp_inventory``): tools
that appear or change after a server's first connection are held for approval,
and the list is read again whenever the server says it changed, when the agent
asks for a tool that isn't on it, and every ``refresh_seconds``.

Requires the ``mcp`` extra: ``pip install "teotl[mcp]"``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import TYPE_CHECKING, Any

from teotl.core.types import RiskLevel, ToolDefinition, ToolErrorOutput
from teotl.primitives.integrations.mcp_inventory import (
    APPROVED,
    BLOCKED,
    PENDING,
    REVIEW_MODES,
    ToolChanges,
    ToolInventory,
    fingerprint,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

MODES = ("compact", "full")
DISCOVER_TOOL = "mcp_discover"
EXECUTE_TOOL = "mcp_execute"
FULL_SEPARATOR = "__"
MAX_LIST_PAGES = 100


@dataclass
class MCPServerConfig:
    """One MCP server: a local command (stdio) or a URL (streamable HTTP).

    ``risk`` overrides the risk of this server's tools, by tool name or pattern:
    ``{"read_*": "low", "delete_*": "critical", "*": "medium"}``.

    ``review`` overrides the bridge's review mode for this server ("changes",
    "all" or "off"), and ``auto_approve`` lists tool name patterns approved even
    when they are new or changed.
    """

    name: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    cwd: str | None = None
    url: str | None = None
    risk: dict[str, str] = field(default_factory=dict)
    review: str | None = None
    auto_approve: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if bool(self.command) == bool(self.url):
            raise ValueError(f"MCP server {self.name!r}: set exactly one of `command` or `url`")
        if self.review is not None and self.review not in REVIEW_MODES:
            raise ValueError(
                f"MCP server {self.name!r}: review must be one of {', '.join(REVIEW_MODES)}"
            )

    @property
    def identity(self) -> str:
        """What this server runs; if it changes, its inventory starts again."""
        return self.url or " ".join([self.command or "", *self.args])

    @classmethod
    def from_dict(cls, name: str, spec: dict[str, Any]) -> MCPServerConfig:
        """Accept the `mcpServers` entries used by Claude Desktop, Cursor and others."""
        known = {"command", "args", "env", "cwd", "url", "risk", "review", "auto_approve"}
        unknown = set(spec) - known - {"type", "transport"}
        if unknown:
            logger.warning(f"MCP server {name!r}: ignoring unknown keys {sorted(unknown)}")
        return cls(name=name, **{k: v for k, v in spec.items() if k in known})


def parse_servers(servers: Any) -> list[MCPServerConfig]:
    """Configs from a list of MCPServerConfig/dicts, or a {name: spec} mapping."""
    if not servers:
        return []
    if isinstance(servers, dict):
        servers = servers.get("mcpServers", servers)
        return [MCPServerConfig.from_dict(n, s) for n, s in servers.items()]
    result = []
    for s in servers:
        if isinstance(s, MCPServerConfig):
            result.append(s)
        else:
            spec = dict(s)
            result.append(MCPServerConfig.from_dict(spec.pop("name"), spec))
    return result


@dataclass
class MCPTool:
    server: str
    name: str
    description: str
    schema: dict[str, Any]
    risk: RiskLevel
    read_only: bool = False
    fingerprint: str = ""
    status: str = APPROVED  # approved, pending (held for review) or blocked
    reason: str = ""  # why it's held: "new" or "changed"
    # The tool exactly as the server listed it (an mcp Tool), for proxies that
    # pass tools on unchanged
    raw: Any = field(default=None, repr=False, compare=False)

    @property
    def qualified(self) -> str:
        return f"{self.server}.{self.name}"


def _get(obj: Any, snake: str, camel: str, default: Any = None) -> Any:
    """Read a field from mcp 2.x (snake_case) or 1.x (camelCase) models."""
    value = getattr(obj, snake, None)
    return getattr(obj, camel, default) if value is None else value


def _risk_from_annotations(annotations: Any) -> tuple[RiskLevel, bool]:
    if annotations is None:
        return (RiskLevel.HIGH, False)
    if _get(annotations, "read_only_hint", "readOnlyHint") is True:
        return (RiskLevel.LOW, True)
    if _get(annotations, "destructive_hint", "destructiveHint") is False:
        return (RiskLevel.MEDIUM, False)
    return (RiskLevel.HIGH, False)  # the MCP default: may be destructive


class MCPCallRefusedError(Exception):
    """A tool call the bridge won't make: unknown, blocked, or held for review."""


def _full_name(server: str, tool: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]", "_", f"{server}{FULL_SEPARATOR}{tool}")
    return name[:64]


class MCPBridge:
    """Connects to MCP servers and exposes their tools to an agent."""

    def __init__(
        self,
        servers: Any = None,
        mode: str = "compact",
        max_output_chars: int = 20_000,
        connect_timeout: float = 30.0,
        *,
        review: str = "changes",
        inventory: ToolInventory | None = None,
        refresh_seconds: float = 300.0,
        transport: Callable[[MCPServerConfig], Any] | None = None,
    ) -> None:
        """``transport``, if given, opens each server's connection instead of the default: it receives the
        server's ``MCPServerConfig`` and returns an async context manager yielding ``(read, write)``, like
        the MCP SDK's ``stdio_client`` / ``streamable_http_client``. Use it to add authentication (for
        example signed headers on every request). ``MCPBridge.default_transport(config)`` is the default,
        so a factory can handle some servers itself and pass the rest on."""
        if mode not in MODES:
            raise ValueError(f"Invalid MCP mode {mode!r}: use one of {', '.join(MODES)}")
        if review not in REVIEW_MODES:
            raise ValueError(f"Invalid MCP review {review!r}: use one of {', '.join(REVIEW_MODES)}")
        self.review = review
        self.transport = transport
        # Created on connect when any server is reviewed
        self.inventory = inventory
        self.refresh_seconds = refresh_seconds
        # Called with ToolChanges whenever a server's tool list changes
        self.on_change: list[Callable[[ToolChanges], Awaitable[None] | None]] = []
        self._last_refresh: dict[str, float] = {}
        self._refresh_locks: dict[str, asyncio.Lock] = {}
        self._pending_refresh: dict[str, asyncio.Task] = {}
        # Held tools someone approved for this session (shared with the guardrails).
        # A held tool runs only if it's here: the list can change between the
        # guardrail check and the call, so the bridge checks again itself.
        self.session_approved: set[str] = set()
        # The command people run to approve a held tool, named in messages
        self.approve_command = "teotl mcp approve"
        self.servers: dict[str, MCPServerConfig] = {s.name: s for s in parse_servers(servers)}
        self.mode = mode
        self.max_output_chars = max_output_chars
        self.connect_timeout = connect_timeout
        self.tools: dict[str, list[MCPTool]] = {}
        self.errors: dict[str, str] = {}
        self._sessions: dict[str, Any] = {}
        # One task per server owns its connection: the MCP transports must be opened
        # and closed in the same task, and when an event loop ends (asyncio.run
        # returns) cancelling that task closes the connection cleanly
        self._tasks: dict[str, asyncio.Task] = {}
        self._stop: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # -- connection -------------------------------------------------------

    @property
    def connected(self) -> bool:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return False
        return self._loop is loop and self._stop is not None

    async def connect(self) -> None:
        """Connect to every server and list its tools. A failing server is skipped."""
        if self.connected:
            return
        try:
            import mcp  # noqa: F401
        except ImportError as e:
            raise ImportError('MCP servers need the mcp extra: pip install "teotl[mcp]"') from e

        # Connections from an earlier event loop are gone with that loop
        self._sessions.clear()
        self._tasks.clear()
        self._refresh_locks.clear()
        self._pending_refresh.clear()
        if self.inventory is None and self._needs_inventory():
            self.inventory = ToolInventory()
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        for config in self.servers.values():
            ready: asyncio.Future = self._loop.create_future()
            task = asyncio.create_task(self._serve(config, ready, self._stop))
            try:
                async with asyncio.timeout(self.connect_timeout):
                    session = await asyncio.shield(ready)
                self._sessions[config.name] = session
                self._tasks[config.name] = task
                await self.refresh(config.name)
                self.errors.pop(config.name, None)
                logger.info(f"MCP server {config.name}: {len(self.tools[config.name])} tools")
            except Exception as e:
                task.cancel()
                self._sessions.pop(config.name, None)
                self._tasks.pop(config.name, None)
                self.errors[config.name] = f"{type(e).__name__}: {e}"
                logger.warning(f"Could not connect to MCP server {config.name!r}: {e}")

    async def _serve(
        self, config: MCPServerConfig, ready: asyncio.Future, stop: asyncio.Event
    ) -> None:
        """Open one server's connection, hand over the session, hold it until stopped."""
        from mcp import ClientSession

        try:
            async with AsyncExitStack() as stack:
                opener = self.transport or self._transport
                read, write = await stack.enter_async_context(opener(config))
                session = await stack.enter_async_context(
                    ClientSession(read, write, message_handler=self._message_handler(config.name))
                )
                await session.initialize()
                if not ready.done():
                    ready.set_result(session)
                await stop.wait()
        except BaseException as e:
            if not ready.done():
                ready.set_exception(
                    e if isinstance(e, Exception) else ConnectionError("connection cancelled")
                )
            if not isinstance(e, Exception):
                raise
            logger.debug(f"MCP server {config.name} connection ended: {e}")

    def _message_handler(self, server: str) -> Callable[[Any], Awaitable[None]]:
        async def handle(message: Any) -> None:
            # Must not wait on the server here (the session is reading messages),
            # so the new list is read in its own task
            from mcp.types import ToolListChangedNotification

            if isinstance(message, ToolListChangedNotification) or (
                getattr(getattr(message, "root", None), "method", None)
                == "notifications/tools/list_changed"
            ):
                logger.info(f"MCP server {server} says its tools changed")
                self._schedule_refresh(server)

        return handle

    def _schedule_refresh(self, server: str) -> None:
        if self._loop is None or server not in self._sessions:
            return
        pending = self._pending_refresh.get(server)
        if pending is not None and not pending.done():
            return
        self._pending_refresh[server] = self._loop.create_task(self._refresh_quietly(server))

    async def _refresh_quietly(self, server: str) -> None:
        try:
            await self.refresh(server)
        except Exception as e:
            logger.warning(f"Could not re-read the tools of MCP server {server!r}: {e}")

    async def close(self) -> None:
        """Close every server connection."""
        for task in self._pending_refresh.values():
            task.cancel()
        self._pending_refresh.clear()
        if self._stop is not None and self.connected:
            self._stop.set()
            tasks = list(self._tasks.values())
            if tasks:
                _, pending = await asyncio.wait(tasks, timeout=10)
                for task in pending:
                    task.cancel()
        self._sessions.clear()
        self._tasks.clear()
        self._stop = None

    @staticmethod
    def default_transport(config: MCPServerConfig) -> Any:
        """The connection teotl opens for a server when no ``transport`` is given."""
        return MCPBridge._transport(config)

    @staticmethod
    def _transport(config: MCPServerConfig) -> Any:
        if config.url:
            from mcp.client.streamable_http import streamable_http_client

            return streamable_http_client(config.url)
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        return stdio_client(
            StdioServerParameters(
                command=config.command or "",
                args=list(config.args),
                env=config.env,
                cwd=config.cwd,
            )
        )

    def _needs_inventory(self) -> bool:
        return any(self._review_mode(c) != "off" for c in self.servers.values())

    def _review_mode(self, config: MCPServerConfig) -> str:
        return config.review or self.review

    async def _list_tools(self, config: MCPServerConfig, session: Any) -> list[MCPTool]:
        """Every tool the server lists, following its pages."""
        from mcp.types import PaginatedRequestParams

        listed: list[Any] = []
        cursor = None
        for _ in range(MAX_LIST_PAGES):
            params = PaginatedRequestParams(cursor=cursor) if cursor else None
            result = await session.list_tools(params=params)
            listed.extend(result.tools)
            cursor = _get(result, "next_cursor", "nextCursor")
            if not cursor:
                break
        else:
            logger.warning(f"MCP server {config.name}: stopped after {MAX_LIST_PAGES} pages")

        tools = []
        for tool in listed:
            annotations = getattr(tool, "annotations", None)
            risk, read_only = _risk_from_annotations(annotations)
            for pattern, level in config.risk.items():
                if fnmatch(tool.name, pattern):
                    risk = RiskLevel(level)
                    break
            description = (tool.description or "").strip()
            schema = _get(tool, "input_schema", "inputSchema", {}) or {}
            dumped = annotations.model_dump(exclude_none=True) if annotations else None
            tools.append(
                MCPTool(
                    server=config.name,
                    name=tool.name,
                    description=description,
                    schema=schema,
                    risk=risk,
                    read_only=read_only,
                    fingerprint=fingerprint(description, schema, dumped),
                    raw=tool,
                )
            )
        return tools

    async def refresh(self, server: str) -> ToolChanges | None:
        """Read a server's tool list again and check it against the inventory."""
        session = self._sessions.get(server)
        if session is None:
            return None
        config = self.servers[server]
        lock = self._refresh_locks.setdefault(server, asyncio.Lock())
        async with lock:
            tools = await self._list_tools(config, session)
            self._last_refresh[server] = time.monotonic()
            mode = self._review_mode(config)
            if mode == "off" or self.inventory is None:
                old = {t.name: t.fingerprint for t in self.tools.get(server, [])}
                new = {t.name: t.fingerprint for t in tools}
                changes = ToolChanges(
                    server=server,
                    added=[n for n in new if n not in old] if server in self.tools else [],
                    changed=[n for n in new if n in old and old[n] != new[n]],
                    removed=[n for n in old if n not in new],
                )
            else:
                changes = self.inventory.review(
                    server,
                    config.identity,
                    {
                        t.name: {
                            "fingerprint": t.fingerprint,
                            "description": t.description,
                            "risk": t.risk.value,
                        }
                        for t in tools
                    },
                    mode=mode,
                    auto_approve=config.auto_approve,
                )
                self._apply_inventory(server, tools)
            self.tools[server] = tools
        changes._bridge = self
        if changes or changes.held:
            logger.info(changes.summary())
        if changes:
            await self._notify(changes)
        return changes

    def _apply_inventory(self, server: str, tools: list[MCPTool]) -> None:
        if self.inventory is None:
            return
        entries = self.inventory.tools(server)
        for t in tools:
            entry = entries.get(t.name) or {}
            t.status = entry.get("status", APPROVED)
            t.reason = entry.get("reason", "") if t.status == PENDING else ""

    async def _notify(self, changes: ToolChanges) -> None:
        for callback in list(self.on_change):
            try:
                result = callback(changes)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"MCP tool-change handler failed: {e}", exc_info=True)

    def set_status(self, server: str, tool: str, status: str) -> list[str]:
        """Approve or block a tool (name or pattern) in the inventory and here."""
        if self.inventory is None:
            raise RuntimeError("Tool review is off, so there is no inventory to change")
        matched = self.inventory.set_status(server, tool, status)
        self._apply_inventory(server, self.tools.get(server, []))
        return matched

    def reload_inventory(self) -> None:
        """Pick up approvals made elsewhere (`teotl mcp approve`)."""
        if self.inventory is not None:
            self.inventory.load()
            for server, tools in self.tools.items():
                self._apply_inventory(server, tools)

    async def _settle(self, server: str) -> None:
        """Wait for a pending re-read, or re-read if the list is old."""
        pending = self._pending_refresh.get(server)
        if pending is not None and not pending.done():
            await asyncio.shield(pending)
        last = self._last_refresh.get(server, 0.0)
        if self.refresh_seconds and time.monotonic() - last > self.refresh_seconds:
            await self._refresh_quietly(server)

    # -- what the agent sees ----------------------------------------------

    def all_tools(self) -> list[MCPTool]:
        return [t for tools in self.tools.values() for t in tools]

    def held(self) -> dict[str, str]:
        """Tools waiting for approval (`server.tool` -> "new" or "changed")."""
        return {t.qualified: t.reason or "new" for t in self.all_tools() if t.status == PENDING}

    def blocked(self) -> set[str]:
        return {t.qualified for t in self.all_tools() if t.status == BLOCKED}

    def find(self, server: str, tool: str) -> MCPTool | None:
        return next((t for t in self.tools.get(server, []) if t.name == tool), None)

    def tool_for_full_name(self, name: str) -> MCPTool | None:
        return next((t for t in self.all_tools() if _full_name(t.server, t.name) == name), None)

    def get_tools(self) -> list[ToolDefinition]:
        """Tool definitions to register with the agent (after connect())."""
        if not self.servers:
            return []
        if self.mode == "full":
            return [
                ToolDefinition(
                    name=_full_name(t.server, t.name),
                    description=f"[{t.server}] {t.description}"[:1024],
                    parameters=t.schema or {"type": "object", "properties": {}},
                )
                for t in self.all_tools()
                if t.status == APPROVED
            ]
        names = ", ".join(self.servers)
        return [
            ToolDefinition(
                name=DISCOVER_TOOL,
                description=(
                    f"List the tools on an MCP server (servers: {names}). "
                    "Pass `tool` to see that tool's full argument schema before calling it."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "server": {"type": "string", "description": f"One of: {names}"},
                        "tool": {"type": "string", "description": "Optional: one tool's name"},
                    },
                    "required": ["server"],
                },
            ),
            ToolDefinition(
                name=EXECUTE_TOOL,
                description="Call a tool on an MCP server. Use mcp_discover first.",
                parameters={
                    "type": "object",
                    "properties": {
                        "server": {"type": "string", "description": "Server name"},
                        "tool": {"type": "string", "description": "Tool name"},
                        "args": {"type": "object", "description": "The tool's arguments"},
                    },
                    "required": ["server", "tool"],
                },
            ),
        ]

    def tool_risk(self) -> dict[str, RiskLevel]:
        """Risk per qualified tool name (`server.tool`), for the guardrails."""
        return {t.qualified: t.risk for t in self.all_tools()}

    # -- tool handlers ----------------------------------------------------

    def _unknown_server(self, server: str) -> str | None:
        if server in self._sessions:
            return None
        if server in self.errors:
            return f"Error: MCP server {server!r} isn't connected ({self.errors[server]})"
        return f"Error: unknown MCP server {server!r}. Servers: {', '.join(self.servers)}"

    async def discover(self, server: str, tool: str | None = None) -> str:
        """One line per tool, or one tool's full schema.

        Held tools are listed by name only: a new or changed description is
        exactly what a tampered server would use to steer the model.
        """
        if error := self._unknown_server(server):
            return error
        await self._settle(server)
        if tool:
            found = self.find(server, tool)
            if found is None:
                await self.refresh(server)
                found = self.find(server, tool)
            if found is None or found.status == BLOCKED:
                return f"Error: {server} has no tool {tool!r}. Call mcp_discover({server!r})."
            if found.status == PENDING:
                return self._held_message(found)
            return json.dumps(
                {"name": found.name, "description": found.description, "arguments": found.schema},
                indent=1,
            )
        lines = []
        for t in self.tools.get(server, []):
            if t.status == BLOCKED:
                continue
            if t.status == PENDING:
                lines.append(f"- {t.name}: (needs approval: {_reason_text(t)})")
                continue
            summary = t.description.split("\n", 1)[0][:160]
            lines.append(f"- {t.name}{' (read-only)' if t.read_only else ''}: {summary}")
        return f"Tools on {server} (call mcp_discover with `tool` for arguments):\n" + "\n".join(
            lines
        )

    async def execute(self, server: str, tool: str, args: dict[str, Any] | None = None) -> str:
        """Call a tool and return its output as text.

        Errors start with "Error:" and are returned as ``ToolErrorOutput``, so the agent records them as
        failed calls: the server's own error results (``isError``), refusals, and transport failures.
        """
        try:
            result = await self.call_tool(server, tool, args)
        except MCPCallRefusedError as e:
            return ToolErrorOutput(f"Error: {e}")
        except Exception as e:
            return ToolErrorOutput(f"Error: {server}.{tool} failed: {type(e).__name__}: {e}")
        return self._format(result)

    async def call_tool(self, server: str, tool: str, args: dict[str, Any] | None = None) -> Any:
        """Call a tool and return the server's result unchanged (an mcp CallToolResult).

        Raises MCPCallRefusedError for an unknown server or tool, a blocked tool, or a
        held tool nobody approved this session. Errors from the call itself
        propagate.
        """
        if error := self._unknown_server(server):
            raise MCPCallRefusedError(error.removeprefix("Error: "))
        await self._settle(server)
        found = self.find(server, tool)
        if found is None:
            # Maybe the server added it without saying so: read the list again
            await self.refresh(server)
            found = self.find(server, tool)
        if found is None:
            raise MCPCallRefusedError(
                f"{server} has no tool {tool!r}. Call mcp_discover({server!r})."
            )
        if found.status == BLOCKED:
            raise MCPCallRefusedError(f"{server}.{tool} is blocked in the MCP tool inventory.")
        if found.status == PENDING and found.qualified not in self.session_approved:
            raise MCPCallRefusedError(self._held_message(found))
        return await self._sessions[server].call_tool(tool, arguments=args or {})

    def sync_guardrails(self, engine: Any) -> None:
        """Bring a GuardrailEngine in line with this bridge: risk, held and blocked tools."""
        self.reload_inventory()
        engine.tool_risk.update(self.tool_risk())
        engine.held_tools = self.held()
        engine.blocked_tools = self.blocked()
        engine.session_approved = self.session_approved
        engine.approve_command = self.approve_command

    def _held_message(self, tool: MCPTool) -> str:
        return (
            f"{tool.qualified} is {_reason_text(tool)}, so its details are hidden until "
            f"someone approves it (`{self.approve_command} {tool.qualified}`). "
            "Calling it asks first."
        )

    def _format(self, result: Any) -> str:
        parts = []
        for item in getattr(result, "content", None) or []:
            text = getattr(item, "text", None)
            if text is not None:
                parts.append(text)
            else:
                parts.append(f"[{getattr(item, 'type', 'content')} omitted]")
        structured = _get(result, "structured_content", "structuredContent")
        if not parts and structured is not None:
            parts.append(json.dumps(structured))
        output = "\n".join(parts)
        if len(output) > self.max_output_chars:
            output = (
                output[: self.max_output_chars]
                + f"\n...(truncated: {len(output)} characters in all)"
            )
        if _get(result, "is_error", "isError"):
            return ToolErrorOutput(f"Error: {output or 'the tool reported an error'}")
        return output or "(no output)"


def _reason_text(tool: MCPTool) -> str:
    if tool.reason == "changed":
        return "changed since it was approved"
    return "new since the server was approved"


def qualified_mcp_target(tool_call_name: str, args: dict[str, Any]) -> str | None:
    """`server.tool` for an mcp_execute call, else None."""
    if tool_call_name == EXECUTE_TOOL:
        return f"{args.get('server', '')}.{args.get('tool', '')}"
    return None

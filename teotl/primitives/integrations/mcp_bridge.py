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

Requires the ``mcp`` extra: ``pip install "teotl[mcp]"``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Any

from teotl.core.types import RiskLevel, ToolDefinition

logger = logging.getLogger(__name__)

MODES = ("compact", "full")
DISCOVER_TOOL = "mcp_discover"
EXECUTE_TOOL = "mcp_execute"
FULL_SEPARATOR = "__"


@dataclass
class MCPServerConfig:
    """One MCP server: a local command (stdio) or a URL (streamable HTTP).

    ``risk`` overrides the risk of this server's tools, by tool name or pattern:
    ``{"read_*": "low", "delete_*": "critical", "*": "medium"}``.
    """

    name: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    cwd: str | None = None
    url: str | None = None
    risk: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if bool(self.command) == bool(self.url):
            raise ValueError(f"MCP server {self.name!r}: set exactly one of `command` or `url`")

    @classmethod
    def from_dict(cls, name: str, spec: dict[str, Any]) -> MCPServerConfig:
        """Accept the `mcpServers` entries used by Claude Desktop, Cursor and others."""
        known = {"command", "args", "env", "cwd", "url", "risk"}
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
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"Invalid MCP mode {mode!r}: use one of {', '.join(MODES)}")
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
                self.tools[config.name] = await self._list_tools(config, session)
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
                read, write = await stack.enter_async_context(self._transport(config))
                session = await stack.enter_async_context(ClientSession(read, write))
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

    async def close(self) -> None:
        """Close every server connection."""
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

    async def _list_tools(self, config: MCPServerConfig, session: Any) -> list[MCPTool]:
        result = await session.list_tools()
        tools = []
        for tool in result.tools:
            risk, read_only = _risk_from_annotations(getattr(tool, "annotations", None))
            for pattern, level in config.risk.items():
                if fnmatch(tool.name, pattern):
                    risk = RiskLevel(level)
                    break
            tools.append(
                MCPTool(
                    server=config.name,
                    name=tool.name,
                    description=(tool.description or "").strip(),
                    schema=_get(tool, "input_schema", "inputSchema", {}) or {},
                    risk=risk,
                    read_only=read_only,
                )
            )
        return tools

    # -- what the agent sees ----------------------------------------------

    def all_tools(self) -> list[MCPTool]:
        return [t for tools in self.tools.values() for t in tools]

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
        """One line per tool, or one tool's full schema."""
        if error := self._unknown_server(server):
            return error
        if tool:
            found = self.find(server, tool)
            if found is None:
                return f"Error: {server} has no tool {tool!r}. Call mcp_discover({server!r})."
            return json.dumps(
                {"name": found.name, "description": found.description, "arguments": found.schema},
                indent=1,
            )
        lines = []
        for t in self.tools.get(server, []):
            summary = t.description.split("\n", 1)[0][:160]
            lines.append(f"- {t.name}{' (read-only)' if t.read_only else ''}: {summary}")
        return f"Tools on {server} (call mcp_discover with `tool` for arguments):\n" + "\n".join(
            lines
        )

    async def execute(self, server: str, tool: str, args: dict[str, Any] | None = None) -> str:
        if error := self._unknown_server(server):
            return error
        if self.find(server, tool) is None:
            return f"Error: {server} has no tool {tool!r}. Call mcp_discover({server!r})."
        try:
            result = await self._sessions[server].call_tool(tool, arguments=args or {})
        except Exception as e:
            return f"Error: {server}.{tool} failed: {type(e).__name__}: {e}"
        return self._format(result)

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
            return f"Error: {output or 'the tool reported an error'}"
        return output or "(no output)"


def qualified_mcp_target(tool_call_name: str, args: dict[str, Any]) -> str | None:
    """`server.tool` for an mcp_execute call, else None."""
    if tool_call_name == EXECUTE_TOOL:
        return f"{args.get('server', '')}.{args.get('tool', '')}"
    return None

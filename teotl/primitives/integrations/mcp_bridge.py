"""
MCP escape hatch: meta-tool pattern.

When a skill doesn't exist but an MCP server does, use this bridge.
Registers only 2 tools (discover + execute) instead of N tool schemas.
Reduces context overhead by 85-95%.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from teotl.core.types import ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str  # e.g., "npx"
    args: list[str]  # e.g., ["-y", "@modelcontextprotocol/server-github"]
    env: dict[str, str] | None = None


class MCPBridge:
    """
    Meta-tool pattern for MCP servers.

    Instead of loading all N tools from an MCP server (~N×250 tokens),
    register only 2 tools: discover + execute (~600 tokens fixed).

    Usage:
        bridge = MCPBridge([MCPServerConfig(name="github", url="...")])
        tools = bridge.get_tools()  # Returns exactly 2 ToolDefinitions
    """

    def __init__(self, servers: list[MCPServerConfig] | None = None) -> None:
        self.servers: dict[str, MCPServerConfig] = {}
        for s in servers or []:
            self.servers[s.name] = s
        self._tool_cache: dict[str, list[dict]] = {}
        self._sessions: dict[str, ClientSession] = {}
        self._cleanup_stack: list[Any] = []  # Store context managers for cleanup

    def get_tools(self) -> list[ToolDefinition]:
        """Returns exactly 2 tools regardless of how many MCP servers."""
        if not self.servers:
            return []

        server_names = ", ".join(self.servers.keys())

        return [
            ToolDefinition(
                name="mcp_discover",
                description=(
                    f"List available tools from an MCP server. Available servers: {server_names}"
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "server": {
                            "type": "string",
                            "description": f"Server name. One of: {server_names}",
                        }
                    },
                    "required": ["server"],
                },
            ),
            ToolDefinition(
                name="mcp_execute",
                description="Execute a specific tool on an MCP server by name.",
                parameters={
                    "type": "object",
                    "properties": {
                        "server": {"type": "string", "description": "Server name"},
                        "tool": {"type": "string", "description": "Tool name from discover"},
                        "args": {"type": "object", "description": "Tool arguments"},
                    },
                    "required": ["server", "tool"],
                },
            ),
        ]

    async def _get_session(self, server_name: str) -> ClientSession:
        """Get or create MCP client session for a server."""
        if server_name in self._sessions:
            return self._sessions[server_name]

        config = self.servers.get(server_name)
        if not config:
            raise ValueError(f"Unknown MCP server: {server_name}. Available: {list(self.servers.keys())}")

        logger.info(f"Connecting to MCP server: {server_name}")

        # Create stdio connection to MCP server
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or {}
        )

        # Connect via stdio and create session (enter context managers)
        stdio_ctx = stdio_client(server_params)
        read, write = await stdio_ctx.__aenter__()
        self._cleanup_stack.append(('stdio', stdio_ctx))

        session_ctx = ClientSession(read, write)
        session = await session_ctx.__aenter__()
        self._cleanup_stack.append(('session', session_ctx))

        await session.initialize()

        logger.info(f"Connected to MCP server: {server_name}")
        self._sessions[server_name] = session
        return session

    async def discover(self, server_name: str) -> list[dict]:
        """List tools available on an MCP server. Results are cached."""
        # Return cached tools if available
        if server_name in self._tool_cache:
            return self._tool_cache[server_name]

        try:
            session = await self._get_session(server_name)
            result = await session.list_tools()

            tools = [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                }
                for tool in result.tools
            ]

            logger.info(f"Discovered {len(tools)} tools from {server_name}")
            self._tool_cache[server_name] = tools
            return tools

        except Exception as e:
            logger.error(f"Failed to discover tools from {server_name}: {e}")
            raise

    async def execute(self, server_name: str, tool: str, args: dict | None = None) -> str:
        """Execute a specific tool on an MCP server."""
        try:
            session = await self._get_session(server_name)

            logger.debug(f"Executing {server_name}/{tool} with args: {args}")
            result = await session.call_tool(tool, arguments=args or {})

            # MCP returns content array, extract text
            if result.content:
                output = "\n".join(
                    item.text for item in result.content
                    if hasattr(item, 'text')
                )
                logger.debug(f"Tool {tool} returned {len(output)} chars")
                return output

            return ""

        except Exception as e:
            logger.error(f"Failed to execute {server_name}/{tool}: {e}")
            raise

    async def close(self):
        """Close all MCP sessions."""
        # Exit all context managers in reverse order
        for ctx_type, ctx in reversed(self._cleanup_stack):
            try:
                logger.debug(f"Closing {ctx_type} context")
                await ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing {ctx_type} context: {e}")

        self._sessions.clear()
        self._cleanup_stack.clear()
        logger.info("All MCP sessions closed")

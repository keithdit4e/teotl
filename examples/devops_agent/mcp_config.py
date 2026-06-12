"""MCP Configuration for DevOps Agent.

Configures MCP servers for GitHub operations.
"""

import os
from teotl.primitives.integrations.mcp_bridge import MCPBridge, MCPServerConfig


def create_mcp_bridge() -> MCPBridge:
    """Create MCP bridge with GitHub server configured.

    Returns:
        MCPBridge instance with GitHub MCP server configured.

    Environment Variables Required:
        GITHUB_TOKEN: GitHub personal access token for API access
    """

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError(
            "GITHUB_TOKEN environment variable required for GitHub MCP server. "
            "Get a token from: https://github.com/settings/tokens"
        )

    servers = [
        MCPServerConfig(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": github_token
            }
        )
    ]

    return MCPBridge(servers)

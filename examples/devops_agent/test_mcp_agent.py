"""Test MCP integration in the agent.

Tests that the agent is created with MCP tools and can use them.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider

console = Console()


async def test_mcp_tools_registration():
    """Test that MCP tools are registered with the agent."""
    console.print("\n[bold]Testing MCP Tools Registration...[/bold]\n")

    # Check GITHUB_TOKEN
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        console.print("[red]❌ GITHUB_TOKEN not set[/red]")
        return False

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]❌ ANTHROPIC_API_KEY not set[/red]")
        return False

    try:
        from mcp_config import create_mcp_bridge

        # Create MCP bridge
        console.print("[yellow]Creating MCP bridge...[/yellow]")
        mcp_bridge = create_mcp_bridge()
        mcp_tools = mcp_bridge.get_tools()
        console.print(f"[green]✓[/green] MCP bridge created with {len(mcp_tools)} tools")

        # Show tool names
        for tool in mcp_tools:
            console.print(f"  - [cyan]{tool.name}[/cyan]: {tool.description[:60]}...")

        # Create agent with MCP tools
        console.print("\n[yellow]Creating agent with MCP tools...[/yellow]")
        provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key=api_key)

        agent = Agent(
            provider=provider,
            tools=mcp_tools,
            instructions="You are a test agent with MCP tools.",
        )
        console.print("[green]✓[/green] Agent created successfully")

        # Test a simple interaction that uses MCP discover
        console.print("\n[yellow]Testing MCP tool discovery...[/yellow]")
        response = await agent.run(
            "Please use the mcp_discover tool to list all available GitHub tools. "
            "Just call mcp_discover with server='github' and show me the first 5 tools."
        )

        console.print("\n[bold]Agent Response:[/bold]")
        console.print(response.text[:500] + "..." if len(response.text) > 500 else response.text)

        # Clean up
        await mcp_bridge.close()
        console.print("\n[green]✓[/green] MCP bridge closed")

        # Check if response mentions tools
        if "tool" in response.text.lower() or "github" in response.text.lower():
            console.print("\n[green]✓[/green] Agent successfully used MCP tools")
            return True
        else:
            console.print("\n[yellow]⚠[/yellow]  Agent response doesn't mention tools")
            return False

    except Exception as e:
        console.print(f"\n[red]❌ Test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run MCP agent integration test."""
    console.print("\n" + "=" * 70)
    console.print("[bold blue]MCP Agent Integration Test[/bold blue]")
    console.print("=" * 70)

    success = await test_mcp_tools_registration()

    console.print("\n" + "=" * 70)
    if success:
        console.print("[bold green]✅ MCP agent integration working![/bold green]")
        console.print("\nThe agent can access and use MCP tools.")
    else:
        console.print("[bold red]❌ MCP agent integration failed[/bold red]")
        console.print("\nCheck the errors above.")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

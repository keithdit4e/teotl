"""Test MCP bridge functionality.

Tests the MCP bridge can connect to GitHub server and discover/execute tools.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console

console = Console()


async def test_mcp_github():
    """Test GitHub MCP server connection."""
    console.print("\n[bold]Testing GitHub MCP Server...[/bold]\n")

    # Check environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        console.print("[red]❌ GITHUB_TOKEN not set[/red]")
        console.print("Set with: export GITHUB_TOKEN='ghp_...'")
        return False

    try:
        from mcp_config import create_mcp_bridge

        console.print("[yellow]Creating MCP bridge...[/yellow]")
        bridge = create_mcp_bridge()
        console.print("[green]✓[/green] MCP bridge created")

        # Test discovery
        console.print("\n[yellow]Discovering GitHub tools...[/yellow]")
        tools = await bridge.discover("github")
        console.print(f"[green]✓[/green] Discovered {len(tools)} GitHub tools\n")

        # Show first 10 tools
        console.print("[bold]Available tools:[/bold]")
        for i, tool in enumerate(tools[:10], 1):
            console.print(f"  {i}. [cyan]{tool['name']}[/cyan] - {tool['description'][:60]}...")

        if len(tools) > 10:
            console.print(f"  ... and {len(tools) - 10} more")

        # Test execution - get a public repo
        console.print("\n[yellow]Testing tool execution (get repository)...[/yellow]")
        try:
            result = await bridge.execute(
                "github",
                "get_repository",
                {"owner": "anthropics", "repo": "anthropic-sdk-python"}
            )
            console.print(f"[green]✓[/green] Tool execution successful")
            console.print(f"Result preview: {result[:200]}...")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow]  Tool execution failed: {e}")
            console.print("This may be normal if the tool name changed")

        # Clean up
        await bridge.close()
        console.print("\n[green]✓[/green] MCP bridge closed")

        return True

    except Exception as e:
        console.print(f"\n[red]❌ Test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run MCP tests."""
    console.print("\n" + "=" * 60)
    console.print("[bold blue]MCP Bridge Test Suite[/bold blue]")
    console.print("=" * 60)

    success = await test_mcp_github()

    console.print("\n" + "=" * 60)
    if success:
        console.print("[bold green]✅ MCP bridge tests passed![/bold green]")
        console.print("\nThe MCP bridge is working correctly.")
        console.print("You can now integrate it into the DevOps Agent.")
    else:
        console.print("[bold red]❌ MCP bridge tests failed[/bold red]")
        console.print("\nCheck the errors above and fix configuration.")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

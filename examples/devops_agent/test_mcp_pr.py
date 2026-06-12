#!/usr/bin/env python3
"""Test MCP PR creation in isolation.

This tests if the MCP GitHub server can create PRs at all,
separate from the agent.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console

console = Console()


async def test_mcp_pr_creation():
    """Test creating a PR via MCP directly."""
    console.print("\n[bold blue]Testing MCP PR Creation[/bold blue]\n")

    # Check environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        console.print("[red]❌ GITHUB_TOKEN not set[/red]")
        return False

    try:
        from mcp_config import create_mcp_bridge

        # Create MCP bridge
        console.print("[yellow]→[/yellow] Creating MCP bridge...")
        mcp_bridge = create_mcp_bridge()
        console.print("[green]✓[/green] MCP bridge created\n")

        # Discover tools
        console.print("[yellow]→[/yellow] Discovering GitHub tools...")
        tools = await mcp_bridge.discover("github")
        console.print(f"[green]✓[/green] Found {len(tools)} tools\n")

        # Check if create_pull_request exists
        pr_tool = next((t for t in tools if t["name"] == "create_pull_request"), None)

        if not pr_tool:
            console.print("[red]❌ create_pull_request tool not found[/red]")
            console.print("\nAvailable tools:")
            for tool in sorted(tools, key=lambda x: x["name"]):
                console.print(f"  • {tool['name']}")
            await mcp_bridge.close()
            return False

        console.print("[green]✓[/green] create_pull_request tool found")
        console.print(f"\n[bold]Tool details:[/bold]")
        console.print(f"  Name: {pr_tool['name']}")
        console.print(f"  Description: {pr_tool['description']}")
        console.print(f"  Parameters: {pr_tool.get('parameters', 'N/A')}")

        # Try to create a test PR
        console.print("\n[yellow]→[/yellow] Testing PR creation on devops-agent-test...")
        console.print("  Using branch: fix/issue-3 → main")

        try:
            result = await mcp_bridge.execute(
                "github",
                "create_pull_request",
                {
                    "owner": "keithdit4e",
                    "repo": "devops-agent-test",
                    "title": "Test: MCP PR Creation",
                    "body": "This is a test PR created by MCP bridge directly.\n\nTesting if MCP can create PRs.",
                    "head": "fix/issue-3",
                    "base": "main"
                }
            )

            console.print(f"\n[green]✓[/green] PR created successfully!")
            console.print(f"\n[bold]Result:[/bold]")
            console.print(result)

            await mcp_bridge.close()
            return True

        except Exception as e:
            console.print(f"\n[red]❌ PR creation failed: {e}[/red]")
            import traceback
            console.print("\n[dim]Traceback:[/dim]")
            traceback.print_exc()

            await mcp_bridge.close()
            return False

    except Exception as e:
        console.print(f"\n[red]❌ Test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


async def main():
    console.print("=" * 70)
    console.print("[bold blue]MCP PR Creation Test[/bold blue]")
    console.print("=" * 70)

    success = await test_mcp_pr_creation()

    console.print("\n" + "=" * 70)
    if success:
        console.print("[bold green]✅ MCP can create PRs![/bold green]\n")
        console.print("This means the agent should be able to as well.")
        console.print("Issue is likely in agent instructions or guardrails.\n")
    else:
        console.print("[bold red]❌ MCP cannot create PRs[/bold red]\n")
        console.print("This is a fundamental MCP server limitation.")
        console.print("We'll need a workaround (use gh CLI instead).\n")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

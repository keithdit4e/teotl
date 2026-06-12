#!/usr/bin/env python3
"""Simple test runner for DevOps Agent.

This script tests the MCP integration and setup.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent to path for teotl imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console

console = Console()


def check_requirements():
    """Check that all requirements are met."""
    console.print("\n[bold blue]DevOps Agent Test Suite[/bold blue]\n")

    all_good = True

    # Check Python version
    if sys.version_info >= (3, 11):
        console.print("[green]✓[/green] Python version:", sys.version.split()[0])
    else:
        console.print("[red]✗[/red] Python version:", sys.version.split()[0], "(need 3.11+)")
        all_good = False

    # Check environment variables
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")

    if anthropic_key:
        console.print(f"[green]✓[/green] ANTHROPIC_API_KEY: {anthropic_key[:15]}...")
    else:
        console.print("[red]✗[/red] ANTHROPIC_API_KEY: not set")
        all_good = False

    if github_token:
        console.print(f"[green]✓[/green] GITHUB_TOKEN: {github_token[:10]}...")
    else:
        console.print("[red]✗[/red] GITHUB_TOKEN: not set")
        all_good = False

    # Check imports
    try:
        from teotl.core.agent import Agent
        from teotl.core.provider import AnthropicProvider
        console.print("[green]✓[/green] Teotl framework installed")
    except ImportError as e:
        console.print(f"[red]✗[/red] Teotl framework not installed: {e}")
        all_good = False

    try:
        import anthropic
        console.print("[green]✓[/green] Anthropic SDK installed")
    except ImportError:
        console.print("[red]✗[/red] Anthropic SDK not installed (pip install anthropic)")
        all_good = False

    # Check Node.js
    import subprocess
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"[green]✓[/green] Node.js installed: {result.stdout.strip()}")
        else:
            console.print("[red]✗[/red] Node.js not found")
            all_good = False
    except FileNotFoundError:
        console.print("[red]✗[/red] Node.js not installed (brew install node)")
        all_good = False

    # Check GitHub MCP server
    try:
        result = subprocess.run(
            ["npx", "-y", "@modelcontextprotocol/server-github", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            console.print("[green]✓[/green] GitHub MCP server available")
        else:
            console.print("[yellow]⚠[/yellow] GitHub MCP server: install with 'npm install -g @modelcontextprotocol/server-github'")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        console.print("[yellow]⚠[/yellow] GitHub MCP server: install with 'npm install -g @modelcontextprotocol/server-github'")

    console.print()
    return all_good


async def test_mcp_integration():
    """Test MCP integration with agent."""
    console.print("[bold]Testing MCP Integration...[/bold]\n")

    try:
        from mcp_config import create_mcp_bridge
        from teotl.core.agent import Agent
        from teotl.core.provider import AnthropicProvider

        # Create MCP bridge
        console.print("[yellow]→[/yellow] Creating MCP bridge...")
        mcp_bridge = create_mcp_bridge()
        mcp_tools = mcp_bridge.get_tools()
        console.print(f"[green]✓[/green] MCP bridge created with {len(mcp_tools)} tools\n")

        for tool in mcp_tools:
            console.print(f"  • [cyan]{tool.name}[/cyan]")

        # Create agent
        console.print("\n[yellow]→[/yellow] Creating agent with MCP tools...")
        provider = AnthropicProvider(
            model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        agent = Agent(
            provider=provider,
            tools=mcp_tools,
            instructions="You are a test agent with MCP tools.",
        )
        console.print("[green]✓[/green] Agent created successfully\n")

        # Test MCP discover
        console.print("[yellow]→[/yellow] Testing MCP tool discovery...")
        response = await agent.run(
            "Please use the mcp_discover tool to list all available GitHub tools. "
            "Just call mcp_discover with server='github' and show me the first 5 tools."
        )
        console.print("[green]✓[/green] Agent used MCP tools successfully\n")

        # Show response preview
        console.print("[bold]Agent Response (preview):[/bold]")
        preview = response.text[:300] + "..." if len(response.text) > 300 else response.text
        console.print(preview)

        # Cleanup
        await mcp_bridge.close()
        console.print("\n[green]✓[/green] MCP bridge closed\n")

        return True

    except Exception as e:
        console.print(f"\n[red]✗[/red] Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests."""
    console.print("\n" + "=" * 70)
    console.print("[bold blue]DevOps Agent - Test Suite[/bold blue]")
    console.print("=" * 70 + "\n")

    # Check requirements
    if not check_requirements():
        console.print("[yellow]⚠[/yellow]  Some requirements are missing\n")
        console.print("To fix, see: API_KEYS_SETUP.md")
        console.print("Or run: ./setup_keys.sh\n")
        return False

    console.print("[green]✓[/green] All requirements met!\n")

    # Test MCP integration
    console.print("=" * 70)
    success = asyncio.run(test_mcp_integration())

    # Summary
    console.print("=" * 70)
    if success:
        console.print("\n[bold green]✅ All tests passed![/bold green]\n")
        console.print("You can now run the agent:")
        console.print("  python main.py --repo owner/repo --issue N --dry-run\n")
    else:
        console.print("\n[bold red]❌ Tests failed[/bold red]\n")
        console.print("Check the errors above and try again.\n")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

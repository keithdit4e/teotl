"""Test script for DevOps Agent

This script helps test the agent on simple issues without requiring real GitHub repos.
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console

console = Console()


async def test_github_cli():
    """Test GitHub CLI is installed and authenticated."""
    console.print("[bold]Testing GitHub CLI...[/bold]\n")

    import subprocess
    import os

    # Check if gh CLI is installed
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True, text=True, check=True)
        console.print(f"[green]✓[/green] GitHub CLI installed: {result.stdout.split()[2]}")
    except FileNotFoundError:
        console.print("[red]❌ GitHub CLI not found[/red]")
        console.print("Install with: brew install gh")
        return False
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error checking gh version: {e}[/red]")
        return False

    # Check if authenticated
    try:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[green]✓[/green] GitHub CLI authenticated")
        else:
            console.print("[yellow]⚠[/yellow]  GitHub CLI not authenticated")
            console.print("Run: gh auth login")
            return False
    except Exception as e:
        console.print(f"[red]❌ Error checking auth status: {e}[/red]")
        return False

    # Test fetching a known public repo
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "anthropics/anthropic-sdk-python", "--json", "name"],
            capture_output=True,
            text=True,
            check=True
        )
        import json
        repo_data = json.loads(result.stdout)
        console.print(f"[green]✓[/green] Successfully fetched repo: {repo_data['name']}")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Failed to fetch repo: {e.stderr}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ GitHub CLI test failed: {e}[/red]")
        return False


async def test_agent_creation():
    """Test agent can be created with all skills."""
    console.print("\n[bold]Testing Agent Creation...[/bold]\n")

    try:
        from teotl.core.agent import Agent
        from teotl.core.provider import AnthropicProvider
        from teotl.primitives.skills.registry import SkillRegistry
    except ImportError as e:
        console.print(f"[red]❌ Failed to import required modules: {e}[/red]")
        return False

    import os

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        console.print("[red]❌ ANTHROPIC_API_KEY not set[/red]")
        return False

    try:
        # Create providers
        planner = AnthropicProvider(model="claude-sonnet-4-20250514", api_key=anthropic_key)
        worker = AnthropicProvider(model="claude-haiku-4-20250514", api_key=anthropic_key)
        console.print("[green]✓[/green] Created providers (Sonnet + Haiku)")

        # Create skill registry with enabled skills
        registry = SkillRegistry(enabled=["git", "filesystem", "github"])
        console.print(f"[green]✓[/green] Registered {registry.registered_count} skills")

        # Create agent
        agent = Agent.create_planner_worker(
            planner=planner,
            worker=worker,
            instructions="You are a test agent.",
            skills=registry,
            policy="standard",
        )

        console.print("[green]✓[/green] Created planner-worker agent")

        return True

    except Exception as e:
        console.print(f"[red]❌ Agent creation failed: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


async def test_mcp_server():
    """Test MCP server is installed and working."""
    console.print("\n[bold]Testing MCP Server...[/bold]\n")

    import subprocess

    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
        console.print(f"[green]✓[/green] Node.js installed: {result.stdout.strip()}")
    except (FileNotFoundError, subprocess.CalledProcessError):
        console.print("[red]❌ Node.js not found[/red]")
        console.print("Install with: brew install node")
        return False

    # Check GitHub MCP server
    try:
        result = subprocess.run(
            ["npx", "-y", "@modelcontextprotocol/server-github", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        console.print("[green]✓[/green] GitHub MCP server available")
    except subprocess.TimeoutExpired:
        console.print("[green]✓[/green] GitHub MCP server available (stdio mode)")
    except Exception as e:
        console.print(f"[red]❌ GitHub MCP server error: {e}[/red]")
        console.print("Install with: npm install -g @modelcontextprotocol/server-github")
        return False

    # Test MCP bridge
    try:
        from mcp_config import create_mcp_bridge

        bridge = create_mcp_bridge()
        console.print("[green]✓[/green] MCP bridge created")

        # Test discovery
        tools = await bridge.discover("github")
        console.print(f"[green]✓[/green] Discovered {len(tools)} GitHub tools")

        await bridge.close()
        return True

    except ValueError as e:
        if "GITHUB_TOKEN" in str(e):
            console.print("[yellow]⚠[/yellow]  GITHUB_TOKEN not set (MCP server requires it)")
            return False
        raise
    except Exception as e:
        console.print(f"[red]❌ MCP bridge test failed: {e}[/red]")
        return False


async def run_tests():
    """Run all tests."""
    console.print("\n" + "=" * 60)
    console.print("[bold blue]DevOps Agent Test Suite[/bold blue]")
    console.print("=" * 60 + "\n")

    results = {}

    # Test 1: GitHub CLI
    results['github_cli'] = await test_github_cli()

    # Test 2: MCP Server
    results['mcp_server'] = await test_mcp_server()

    # Test 3: Agent Creation
    results['agent_creation'] = await test_agent_creation()

    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold]Test Results:[/bold]")
    console.print("=" * 60 + "\n")

    for test_name, passed in results.items():
        status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
        console.print(f"  {status} - {test_name}")

    all_passed = all(results.values())

    console.print()
    if all_passed:
        console.print("[bold green]🎉 All tests passed![/bold green]")
        console.print("Agent is ready to use.")
    else:
        console.print("[bold red]❌ Some tests failed[/bold red]")
        console.print("Check error messages above and fix issues before running agent.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)

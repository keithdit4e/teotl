"""DevOps Automation Agent - Autonomous GitHub Issue Fixer

This agent autonomously investigates GitHub issues and creates fixes.

Usage:
    python main.py --repo owner/repo --issue 42
    python main.py --repo owner/repo --mode daemon
"""

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path for teotl imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.skills.registry import SkillRegistry
from teotl.primitives.guardrails.policy import Policy
from teotl.primitives.guardrails.presets import PRESETS

# MCP integration
from mcp_config import create_mcp_bridge

console = Console()


def parse_investigation_summary(response_text: str) -> dict[str, str]:
    """Parse investigation summary from agent response.

    Args:
        response_text: Full agent response text

    Returns:
        Dictionary with parsed fields or empty dict if not found
    """
    summary = {}

    # Look for the summary section
    if "INVESTIGATION SUMMARY:" in response_text:
        lines = response_text.split("\n")
        in_summary = False

        for line in lines:
            if "INVESTIGATION SUMMARY:" in line:
                in_summary = True
                continue

            if in_summary and ":" in line and line.strip().startswith("-"):
                # Parse "- Key: Value" format
                parts = line.strip()[1:].split(":", 1)  # Remove "-" and split
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    summary[key] = value

    return summary


def extract_pr_url(text: str) -> str | None:
    """Extract GitHub PR URL from text.

    Args:
        text: Text that may contain a PR URL

    Returns:
        PR URL if found, None otherwise
    """
    import re

    # Match GitHub PR URLs
    pattern = r'https://github\.com/[^/]+/[^/]+/pull/\d+'
    match = re.search(pattern, text)

    if match:
        return match.group(0)

    return None


def display_results(response_text: str, summary: dict[str, str], pr_url: str | None):
    """Display formatted results.

    Args:
        response_text: Full agent response
        summary: Parsed summary dict
        pr_url: Pull request URL if created
    """
    console.print("\n" + "=" * 70)
    console.print("[bold green]🎉 Investigation Complete![/bold green]")
    console.print("=" * 70 + "\n")

    if summary:
        console.print("[bold]📊 Summary:[/bold]\n")

        if "Root Cause" in summary:
            console.print(f"  [yellow]Root Cause:[/yellow] {summary['Root Cause']}")

        if "Files Modified" in summary:
            console.print(f"  [cyan]Files Modified:[/cyan] {summary['Files Modified']}")

        if "Changes Made" in summary:
            console.print(f"  [cyan]Changes Made:[/cyan] {summary['Changes Made']}")

        if "Tests Added" in summary:
            console.print(f"  [green]Tests Added:[/green] {summary['Tests Added']}")

        if "Tests Status" in summary:
            status = summary['Tests Status']
            color = "green" if "passing" in status.lower() else "yellow"
            console.print(f"  [{color}]Tests Status:[/{color}] {status}")

        if "PR Created" in summary:
            created = summary['PR Created']
            color = "green" if created.lower() == "yes" else "yellow"
            console.print(f"  [{color}]PR Created:[/{color}] {created}")

        console.print()

    if pr_url:
        console.print(f"[bold green]🔗 Pull Request:[/bold green] {pr_url}\n")

    # Show full response for debugging
    if summary and any(key in summary for key in ["Root Cause", "Files Modified", "Changes Made"]):
        console.print("[dim]Full agent response available if needed[/dim]")
    else:
        console.print("[bold]Agent Response:[/bold]\n")
        console.print(response_text)


@click.command()
@click.option("--repo", required=True, help="GitHub repository (owner/repo)")
@click.option("--issue", type=int, help="Issue number to investigate")
@click.option("--mode", default="single", help="Mode: single or daemon")
@click.option("--config", type=Path, help="Config file path")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--dry-run", is_flag=True, help="Dry run (no GitHub interaction)")
def main(
    repo: str, issue: int | None, mode: str, config: Path | None, debug: bool, dry_run: bool
):
    """DevOps Automation Agent - Autonomous GitHub Issue Fixer"""

    console.print(
        Panel.fit(
            "[bold blue]🤖 DevOps Automation Agent[/bold blue]\n"
            "[dim]Autonomous GitHub Issue Fixer[/dim]",
            border_style="blue",
        )
    )
    console.print(f"📦 Repository: [bold]{repo}[/bold]")

    if mode == "single" and issue:
        console.print(f"📋 Investigating issue [bold]#{issue}[/bold]")
        asyncio.run(investigate_issue(repo, issue, debug, dry_run))
    elif mode == "daemon":
        console.print("👀 Monitoring repository for new issues...")
        asyncio.run(monitor_repository(repo, debug, dry_run))
    else:
        console.print("[red]❌ Error: Specify --issue for single mode or --mode daemon[/red]")
        sys.exit(1)


async def investigate_issue(repo: str, issue_number: int, debug: bool, dry_run: bool):
    """Investigate and fix a single issue.

    Args:
        repo: Repository in format "owner/repo"
        issue_number: Issue number to investigate
        debug: Enable debug logging
        dry_run: Dry run mode (no actual changes)
    """
    # Check for required environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not github_token:
        console.print("[red]❌ Error: GITHUB_TOKEN environment variable required[/red]")
        console.print("   Set with: export GITHUB_TOKEN='ghp_...'")
        sys.exit(1)

    # API key only needed for actual runs, not dry-run
    if not dry_run and not anthropic_key:
        console.print("[red]❌ Error: ANTHROPIC_API_KEY environment variable required[/red]")
        console.print("   Set with: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    console.print()
    console.print("[bold]Step 1:[/bold] Fetching issue details...")

    # Fetch issue details using gh CLI
    try:
        import subprocess
        import json

        result = subprocess.run(
            ["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "number,title,body,state,labels,url"],
            capture_output=True,
            text=True,
            check=True
        )
        issue_data = json.loads(result.stdout)
        # Convert labels array to list of strings
        issue_data['labels'] = [label['name'] for label in issue_data.get('labels', [])]
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Failed to fetch issue: {e.stderr}[/red]")
        console.print("[yellow]Make sure gh CLI is installed and authenticated:[/yellow]")
        console.print("  brew install gh")
        console.print("  gh auth login")
        sys.exit(1)
    except FileNotFoundError:
        console.print("[red]❌ GitHub CLI (gh) not found[/red]")
        console.print("Install with: brew install gh")
        console.print("Then authenticate: gh auth login")
        sys.exit(1)

    console.print(f"   [green]✓[/green] Issue #{issue_data['number']}: {issue_data['title']}")
    console.print(f"   State: {issue_data['state']}, Labels: {', '.join(issue_data['labels'])}")

    if dry_run:
        console.print("\n[yellow]🔍 DRY RUN MODE - No changes will be made[/yellow]")
        console.print("\nIssue details:")
        console.print(f"  Title: {issue_data['title']}")
        console.print(f"  Body: {issue_data['body'][:200]}...")
        console.print("\nIn full mode, the agent would:")
        console.print("  1. Clone the repository")
        console.print("  2. Reproduce the bug")
        console.print("  3. Investigate root cause")
        console.print("  4. Create a fix")
        console.print("  5. Add regression tests")
        console.print("  6. Create pull request")
        return

    console.print("\n[bold]Step 2:[/bold] Creating agent with MCP integration...")

    # Create MCP bridge for GitHub operations
    try:
        mcp_bridge = create_mcp_bridge()
        mcp_tools = mcp_bridge.get_tools()
        console.print(f"   [green]✓[/green] MCP bridge created ({len(mcp_tools)} meta-tools)")
    except Exception as e:
        console.print(f"[red]❌ Failed to create MCP bridge: {e}[/red]")
        sys.exit(1)

    # Create provider (using Sonnet for now - worker pattern TBD)
    provider = AnthropicProvider(model="claude-sonnet-4-20250514", api_key=anthropic_key)

    # Create skill registry with enabled skills
    registry = SkillRegistry(enabled=["git", "filesystem", "github"])

    console.print("   [green]✓[/green] Provider: claude-sonnet-4")
    console.print("   [green]✓[/green] Skills: git, filesystem, github")
    console.print("   [green]✓[/green] MCP Tools: mcp_discover, mcp_execute")

    # Create custom policy for DevOps agent (extends standard + allows gh CLI)
    devops_policy_config = PRESETS["standard"].copy()
    devops_policy_config["bash"]["allow"].extend(["gh", "gh pr", "gh pr create"])
    devops_policy = Policy(devops_policy_config)

    console.print("   [green]✓[/green] Policy: standard + gh CLI whitelist")

    # Create agent with enhanced instructions and MCP tools
    agent = Agent(
        provider=provider,
        tools=mcp_tools,  # Add MCP meta-tools
        instructions=f"""You are a DevOps automation agent. Your task is to investigate and fix GitHub issue #{issue_number}.

=== ISSUE DETAILS ===
Repository: {repo}
Issue #{issue_number}: {issue_data['title']}

Description:
{issue_data['body']}

Labels: {', '.join(issue_data['labels']) if issue_data['labels'] else 'None'}
State: {issue_data['state']}
URL: {issue_data['url']}

=== YOUR OBJECTIVE ===
Autonomously investigate this issue and create a pull request with a fix.

=== USING MCP TOOLS FOR GITHUB OPERATIONS ===

You have access to GitHub operations via Model Context Protocol (MCP).

**Pattern for using MCP:**
1. First discover available tools: `mcp_discover(server="github")`
2. Then execute a tool: `mcp_execute(server="github", tool="tool_name", args={{...}})`

**GitHub Operations via MCP:**
- Get file contents: `mcp_execute(server="github", tool="get_file_contents", args={{"owner": "{repo.split('/')[0]}", "repo": "{repo.split('/')[1]}", "path": "path/to/file"}})`
- Create issue comment: `mcp_execute(server="github", tool="create_issue_comment", args={{"owner": "...", "repo": "...", "issue_number": {issue_number}, "body": "..."}})`

**When to discover tools:**
- Run `mcp_discover(server="github")` once at the start to see all 26 available GitHub tools
- Then use `mcp_execute` for each operation you need

**IMPORTANT:** For pull requests, you MUST use gh CLI, not MCP (see PHASE 5).

=== STEP-BY-STEP WORKFLOW ===

PHASE 1: SETUP & UNDERSTANDING
1. Create working directory: /tmp/devops-agent-{issue_number}
2. Clone repository: git clone https://github.com/{repo}.git
3. Examine repository structure to understand the project
4. Read relevant documentation (README.md, CONTRIBUTING.md if they exist)

PHASE 2: INVESTIGATION
5. Identify files mentioned in the issue or likely related to the bug
6. Read those files to understand the current implementation
7. If the issue includes steps to reproduce, try to reproduce the bug
8. Identify the root cause of the issue

PHASE 3: FIX CREATION
9. Create a new branch: git checkout -b fix/issue-{issue_number}
10. Make minimal, targeted changes to fix the issue
11. IMPORTANT: Only modify what's necessary - no refactoring or unrelated changes

PHASE 4: TESTING
12. If the project has tests, run them: look for pytest, npm test, make test, etc.
13. Add a regression test for this bug fix if the project has a test suite
14. Ensure all tests pass

PHASE 5: PULL REQUEST
15. Stage changes: git add <modified-files>
16. Commit with semantic message: git commit -m "fix: <description> (#{issue_number})"
17. Push branch: git push origin fix/issue-{issue_number}
18. Create pull request:
    gh pr create --repo {repo} --base main --head fix/issue-{issue_number} --title "Fix: <short description> (#{issue_number})" --body "Description of changes\n\nFixes #{issue_number}"

=== CRITICAL GUIDELINES ===

✓ DO:
- Make minimal changes (only fix this specific issue)
- Add regression tests when possible
- Use clear, semantic commit messages
- Execute gh pr create to create the pull request
- Include issue number in commit and PR
- Explain your changes clearly in the PR description

✗ DON'T:
- Refactor unrelated code
- Change code style or formatting (unless that's the issue)
- Modify multiple unrelated files
- Skip the PR creation step
- Make assumptions without verifying

=== OUTPUT FORMAT ===
At the end, provide a summary in this format:

INVESTIGATION SUMMARY:
- Root Cause: [What caused the issue]
- Files Modified: [List of files changed]
- Changes Made: [Brief description]
- Tests Added: [Yes/No and what tests]
- Tests Status: [All passing / Some failing / Not run]
- PR Created: [Yes/No]
- PR URL: [URL if created]

Begin your investigation now!
""",
        skills=registry,
        policy=devops_policy,
    )

    console.print("\n[bold]Step 3:[/bold] Running autonomous investigation...")
    console.print("[dim]This may take several minutes...[/dim]\n")

    # Run agent
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Investigating issue...", total=None)

        try:
            response = await agent.run(
                f"Investigate and fix GitHub issue #{issue_number} in repository {repo}. "
                f"The issue title is: '{issue_data['title']}'. "
                f"Follow the workflow: reproduce bug, investigate, create fix, add tests, create PR."
            )

            progress.update(task, description="[green]✓ Investigation complete[/green]")

        except Exception as e:
            progress.update(task, description="[red]✗ Investigation failed[/red]")
            console.print(f"\n[red]❌ Error: {e}[/red]")
            await mcp_bridge.close()  # Clean up MCP bridge on error
            if debug:
                raise
            sys.exit(1)

    # Parse and display results
    summary = parse_investigation_summary(response.text)
    pr_url = extract_pr_url(response.text)

    display_results(response.text, summary, pr_url)

    # Display usage statistics if available
    if hasattr(response, 'usage') and response.usage:
        console.print("\n[bold]📈 Usage Statistics:[/bold]")
        console.print(f"  Input tokens: {response.usage.get('input_tokens', 'N/A')}")
        console.print(f"  Output tokens: {response.usage.get('output_tokens', 'N/A')}")

        # Estimate cost (approximate Claude pricing)
        input_tokens = response.usage.get('input_tokens', 0)
        output_tokens = response.usage.get('output_tokens', 0)

        # Rough pricing (will vary by model)
        # Sonnet: ~$3/M input, ~$15/M output
        # Haiku: ~$0.25/M input, ~$1.25/M output
        # Estimate assuming mix of both in planner-worker
        est_cost = (input_tokens * 1.5 / 1_000_000) + (output_tokens * 8 / 1_000_000)
        console.print(f"  Estimated cost: ${est_cost:.4f}")

    console.print()

    # Clean up MCP bridge
    await mcp_bridge.close()


async def monitor_repository(repo: str, debug: bool, dry_run: bool):
    """Monitor repository and automatically fix new issues.

    Args:
        repo: Repository in format "owner/repo"
        debug: Enable debug logging
        dry_run: Dry run mode (no actual changes)
    """
    # TODO: Days 11-14 - Implement daemon mode
    #
    # Steps:
    # 1. Poll GitHub for new issues (or use webhooks)
    # 2. Filter issues by labels (e.g., "bug", "auto-fix")
    # 3. For each qualifying issue:
    #    - Check if already being processed
    #    - Spawn investigate_issue task in background
    #    - Track active investigations
    # 4. Periodic status reporting
    # 5. Handle rate limits and errors

    console.print("\n⚠️  [yellow]Daemon mode implementation coming in Days 11-14![/yellow]")
    console.print("Use single issue mode for now:")
    console.print(f"  python main.py --repo {repo} --issue <number>")


if __name__ == "__main__":
    main()

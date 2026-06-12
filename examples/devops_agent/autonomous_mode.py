#!/usr/bin/env python3
"""Autonomous DevOps Agent - Continuous Repository Maintenance

This agent runs continuously to:
1. MISSIONS (Scheduled): Scan repo for bugs, create GitHub issues
2. TASKS (Immediate): Auto-fix issues and create PRs

Usage:
    python autonomous_mode.py --repo owner/repo
    python autonomous_mode.py --repo owner/repo --scan-interval 3600
    python autonomous_mode.py --repo owner/repo --dry-run
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from teotl.daemon import HeartbeatDaemon
from teotl.primitives.missions import Mission, MissionInterval
from teotl.primitives.tasks import Priority, Task

# Custom executor
from autonomous_executor import DevOpsExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

console = Console()


class AutonomousDevOpsAgent:
    """Autonomous agent that maintains a GitHub repository."""

    def __init__(self, repo: str, github_token: str, anthropic_key: str, scan_interval: int = 3600):
        """Initialize autonomous agent.

        Args:
            repo: Repository in format "owner/repo"
            github_token: GitHub token with repo scope
            anthropic_key: Anthropic API key
            scan_interval: Seconds between scans (default: 3600 = 1 hour)
        """
        self.repo = repo
        self.github_token = github_token
        self.anthropic_key = anthropic_key
        self.scan_interval = scan_interval
        self.executor = None
        self.daemon = None
        self.shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize MCP bridge and daemon."""
        console.print("\n[bold blue]🚀 Initializing Autonomous DevOps Agent[/bold blue]\n")

        # Create data directory
        data_dir = Path.home() / ".forge" / "devops-agent" / self.repo.replace("/", "-")
        data_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"   [green]✓[/green] Data directory: {data_dir}")

        # Create custom DevOps executor
        self.executor = DevOpsExecutor(anthropic_key=self.anthropic_key)
        console.print("   [green]✓[/green] DevOps executor created")

        # Create heartbeat daemon
        # Wrap executor to match expected interface
        class ExecutorWrapper:
            def __init__(self, devops_executor, autonomous_agent):
                self.devops_executor = devops_executor
                self.autonomous_agent = autonomous_agent

            async def __call__(self, description: str, context: dict | None = None) -> dict:
                """Called by daemon for both missions and tasks."""
                context = context or {}

                # Handle missions (custom methods)
                if "scan" in description.lower() and "bugs" in description.lower():
                    await self.autonomous_agent.scan_mission()
                    return {"success": True, "mission": "scan_bugs"}

                if "monitor" in description.lower() and "issues" in description.lower():
                    await self.autonomous_agent.monitor_new_issues()
                    return {"success": True, "mission": "monitor_issues"}

                # Handle tasks (fix specific issues)
                if context.get("issue_number"):
                    task = Task(
                        description=description,
                        priority=Priority.NORMAL,
                        context=context
                    )
                    return await self.devops_executor.execute_task(task)

                return {"success": False, "error": "Unknown mission/task type"}

            async def execute(self, description: str, context: dict | None = None) -> dict:
                return await self(description, context)

        self.daemon = HeartbeatDaemon(
            agent_id=f"devops-{self.repo.replace('/', '-')}",
            agent_executor=ExecutorWrapper(self.executor, self),
            data_dir=data_dir,
            poll_interval=10,  # Check every 10 seconds
        )

        console.print("   [green]✓[/green] Heartbeat daemon initialized\n")

    async def scan_for_bugs(self) -> list[dict]:
        """Scan repository for bugs using linters and tests.

        Returns:
            List of bugs found with descriptions
        """
        bugs = []

        console.print("[yellow]🔍 Scanning repository for bugs...[/yellow]")

        # Clone or update repository
        repo_dir = Path("/tmp") / f"devops-scan-{self.repo.replace('/', '-')}"

        if not repo_dir.exists():
            console.print(f"   Cloning {self.repo}...")
            subprocess.run(
                ["git", "clone", f"https://github.com/{self.repo}.git", str(repo_dir)],
                capture_output=True
            )
        else:
            console.print(f"   Updating {repo_dir}...")
            subprocess.run(
                ["git", "-C", str(repo_dir), "pull"],
                capture_output=True
            )

        # Scan Python files with pylint
        python_files = list(repo_dir.glob("**/*.py"))
        if python_files:
            console.print(f"   [cyan]Running pylint on {len(python_files)} Python files...[/cyan]")

            for py_file in python_files[:5]:  # Limit to first 5 files
                result = subprocess.run(
                    ["pylint", str(py_file), "--output-format=json"],
                    capture_output=True,
                    text=True
                )

                if result.stdout:
                    try:
                        issues = json.loads(result.stdout)
                        for issue in issues[:3]:  # Top 3 issues per file
                            if issue.get("type") in ["error", "warning"]:
                                bugs.append({
                                    "file": str(py_file.relative_to(repo_dir)),
                                    "line": issue.get("line"),
                                    "type": issue.get("type"),
                                    "message": issue.get("message"),
                                    "symbol": issue.get("symbol")
                                })
                    except json.JSONDecodeError:
                        pass

        # Run tests if they exist
        if (repo_dir / "pytest.ini").exists() or (repo_dir / "tests").exists():
            console.print("   [cyan]Running pytest...[/cyan]")
            result = subprocess.run(
                ["pytest", str(repo_dir), "-v", "--tb=short"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0 and "FAILED" in result.stdout:
                bugs.append({
                    "type": "test_failure",
                    "message": "Test suite has failures",
                    "details": result.stdout[:500]
                })

        console.print(f"   [green]✓[/green] Found {len(bugs)} potential issues\n")
        return bugs

    async def create_github_issue(self, bug: dict) -> int | None:
        """Create a GitHub issue for a bug.

        Args:
            bug: Bug dictionary with details

        Returns:
            Issue number if created, None if failed
        """
        title = f"Bug: {bug.get('message', 'Issue found')[:80]}"

        body_parts = ["**Automatically detected by DevOps Agent**\n"]

        if bug.get("file"):
            body_parts.append(f"**File:** `{bug['file']}`")
        if bug.get("line"):
            body_parts.append(f"**Line:** {bug['line']}")
        if bug.get("type"):
            body_parts.append(f"**Type:** {bug['type']}")
        if bug.get("message"):
            body_parts.append(f"\n**Description:**\n{bug['message']}")
        if bug.get("details"):
            body_parts.append(f"\n**Details:**\n```\n{bug['details'][:500]}\n```")

        body = "\n".join(body_parts)

        try:
            result = subprocess.run(
                ["gh", "issue", "create", "--repo", self.repo, "--title", title, "--body", body],
                capture_output=True,
                text=True,
                check=True
            )

            # Extract issue number from URL
            url = result.stdout.strip()
            issue_number = int(url.split("/")[-1])

            console.print(f"   [green]✓[/green] Created issue #{issue_number}: {title[:60]}...")
            return issue_number

        except subprocess.CalledProcessError as e:
            console.print(f"   [red]✗[/red] Failed to create issue: {e.stderr}")
            return None

    async def scan_mission(self):
        """Mission: Periodically scan repo for bugs and create issues."""
        logger.info(f"🔍 Starting bug scan mission for {self.repo}")

        bugs = await self.scan_for_bugs()

        if not bugs:
            console.print("[green]✨ No bugs found! Repository looks good.[/green]\n")
            return

        console.print(f"\n[yellow]📋 Creating GitHub issues for {len(bugs)} bugs...[/yellow]\n")

        for bug in bugs[:5]:  # Limit to 5 issues per scan
            issue_number = await self.create_github_issue(bug)

            if issue_number:
                # Create task to fix this issue with URGENT priority
                # URGENT tasks interrupt missions, allowing immediate execution
                task = Task(
                    description=f"Fix issue #{issue_number} in {self.repo}",
                    priority=Priority.URGENT,  # Always URGENT to interrupt missions
                    context={
                        "repo": self.repo,
                        "issue_number": issue_number,
                        "bug_type": bug.get("type")
                    },
                    expires_at=datetime.now() + timedelta(days=7)
                )

                await self.daemon.task_store.create(task)
                console.print(f"   [green]✓[/green] Created task to fix issue #{issue_number}\n")

    async def monitor_new_issues(self):
        """Check for new issues created by humans."""
        logger.info(f"👀 Monitoring {self.repo} for new issues")

        try:
            result = subprocess.run(
                ["gh", "issue", "list", "--repo", self.repo, "--state", "open",
                 "--json", "number,title,labels", "--limit", "10"],
                capture_output=True,
                text=True,
                check=True
            )

            issues = json.loads(result.stdout)

            # Filter for issues not created by bot
            for issue in issues:
                issue_number = issue["number"]

                # Check if we already have a task for this issue
                all_tasks = await self.daemon.task_store.list_all()
                exists = any(
                    t.context.get("issue_number") == issue_number
                    for t in all_tasks
                )

                if not exists:
                    # Create task to fix this issue with URGENT priority
                    # URGENT tasks interrupt missions, allowing immediate execution
                    task = Task(
                        description=f"Fix issue #{issue_number}: {issue['title'][:50]}",
                        priority=Priority.URGENT,  # Always URGENT to interrupt missions
                        context={
                            "repo": self.repo,
                            "issue_number": issue_number
                        },
                        expires_at=datetime.now() + timedelta(days=7)
                    )

                    await self.daemon.task_store.create(task)
                    console.print(f"[green]✓[/green] New issue detected: #{issue_number} - created fix task")

        except Exception as e:
            logger.error(f"Failed to monitor issues: {e}")

    async def start(self):
        """Start the autonomous agent."""
        await self.initialize()

        console.print(Panel.fit(
            f"[bold green]🤖 Autonomous DevOps Agent Running[/bold green]\n"
            f"Repository: {self.repo}\n"
            f"Scan interval: {self.scan_interval}s ({self.scan_interval // 3600}h)\n"
            f"Press Ctrl+C to stop gracefully (Ctrl+C twice to force quit)",
            border_style="green"
        ))

        # Create scanning mission
        # Map scan_interval to appropriate MissionInterval
        if self.scan_interval >= 3600:
            interval = MissionInterval.HOURLY
        elif self.scan_interval >= 1800:
            interval = MissionInterval.MINUTES_30
        elif self.scan_interval >= 600:
            interval = MissionInterval.MINUTES_10
        else:
            interval = MissionInterval.MINUTES_5

        scan_mission = Mission(
            description=f"Scan {self.repo} for bugs and create issues",
            interval=interval,
            next_execution_at=datetime.now() + timedelta(seconds=30),  # First scan in 30s
            can_be_interrupted=True,
            interrupt_threshold=Priority.URGENT,
        )

        await self.daemon.mission_store.create(scan_mission)
        logger.info(f"📅 Added scanning mission (every {self.scan_interval}s)")

        # Create issue monitoring mission
        monitor_mission = Mission(
            description=f"Monitor {self.repo} for new issues",
            interval=MissionInterval.MINUTES_10,  # Check every 10 minutes
            next_execution_at=datetime.now() + timedelta(seconds=5),  # First check in 5s
            can_be_interrupted=True,
            interrupt_threshold=Priority.URGENT,
        )

        await self.daemon.mission_store.create(monitor_mission)
        logger.info(f"👀 Added issue monitoring mission")

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        shutdown_count = 0

        def handle_shutdown():
            nonlocal shutdown_count
            shutdown_count += 1

            if shutdown_count == 1:
                console.print("\n[yellow]⚠️  Received shutdown signal, stopping gracefully...[/yellow]")
                console.print("[yellow]   (Press Ctrl+C again to force quit immediately)[/yellow]")
                self.shutdown_event.set()
            else:
                console.print("\n[red]⚠️  Force quit! Exiting immediately...[/red]")
                import sys
                sys.exit(0)

        loop.add_signal_handler(signal.SIGINT, handle_shutdown)
        loop.add_signal_handler(signal.SIGTERM, handle_shutdown)

        # Start daemon
        daemon_task = asyncio.create_task(self.daemon.start())

        try:
            # Run until shutdown signal received
            while not self.shutdown_event.is_set():
                try:
                    # Wait with shorter timeout for faster shutdown response
                    await asyncio.wait_for(
                        asyncio.sleep(10),
                        timeout=10
                    )
                except asyncio.TimeoutError:
                    pass

                if self.shutdown_event.is_set():
                    break

                # Show status
                try:
                    pending_tasks = await self.daemon.task_store.get_pending()
                    all_tasks = await self.daemon.task_store.list_all()
                    completed_tasks = [t for t in all_tasks if t.state.value == "completed"]
                except Exception:
                    # Database might be closed during shutdown
                    pending_tasks = []
                    completed_tasks = []

                table = Table(title="Agent Status", show_header=False)
                table.add_row("Pending tasks", str(len(pending_tasks)))
                table.add_row("Completed tasks", str(len(completed_tasks)))
                table.add_row("Current mission",
                            self.daemon.current_mission.description[:50] if self.daemon.current_mission else "Idle")

                console.print(table)
                console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Shutting down gracefully...[/yellow]")

        finally:
            console.print("[yellow]Stopping daemon...[/yellow]")

            # Stop daemon with timeout
            try:
                await asyncio.wait_for(self.daemon.stop(), timeout=3.0)
            except asyncio.TimeoutError:
                console.print("[yellow]⚠️  Daemon stop timed out, forcing shutdown...[/yellow]")

            # Cancel daemon task with timeout
            daemon_task.cancel()
            try:
                await asyncio.wait_for(daemon_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

            # Close executor with timeout
            try:
                await asyncio.wait_for(self.executor.close(), timeout=2.0)
            except asyncio.TimeoutError:
                console.print("[yellow]⚠️  Executor close timed out[/yellow]")

            # Show final stats
            try:
                all_tasks = await self.daemon.task_store.list_all()
                completed = sum(1 for t in all_tasks if t.state.value == "completed")
                failed = sum(1 for t in all_tasks if t.state.value == "failed")

                console.print("\n[bold]📈 Final Statistics:[/bold]")
                console.print(f"   Tasks completed: {completed}")
                console.print(f"   Tasks failed: {failed}")
            except Exception:
                console.print("\n[yellow]Could not retrieve final statistics[/yellow]")

            console.print("\n[green]👋 Autonomous agent stopped[/green]\n")


@click.command()
@click.option("--repo", required=True, help="GitHub repository (owner/repo)")
@click.option("--scan-interval", default=3600, help="Seconds between scans (default: 3600 = 1 hour)")
@click.option("--dry-run", is_flag=True, help="Dry run mode (no changes)")
def main(repo: str, scan_interval: int, dry_run: bool):
    """Autonomous DevOps Agent - Continuous Repository Maintenance"""

    # Check environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not github_token:
        console.print("[red]❌ Error: GITHUB_TOKEN environment variable required[/red]")
        console.print("   Get token from: gh auth token")
        sys.exit(1)

    if not anthropic_key:
        console.print("[red]❌ Error: ANTHROPIC_API_KEY environment variable required[/red]")
        sys.exit(1)

    if dry_run:
        console.print("[yellow]🔍 DRY RUN MODE - No changes will be made[/yellow]\n")
        console.print("In full mode, the agent would:")
        console.print("  1. Scan repository for bugs every hour")
        console.print("  2. Create GitHub issues for problems found")
        console.print("  3. Automatically fix issues")
        console.print("  4. Create pull requests")
        console.print("  5. Run continuously 24/7")
        return

    # Create and start agent
    agent = AutonomousDevOpsAgent(
        repo=repo,
        github_token=github_token,
        anthropic_key=anthropic_key,
        scan_interval=scan_interval
    )

    asyncio.run(agent.start())


if __name__ == "__main__":
    main()

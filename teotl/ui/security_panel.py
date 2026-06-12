"""Rich terminal panels for security status display.

Provides formatted displays of security status, audit logs, and compliance
information that can be integrated into CLI tools and dashboards.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from teotl.core.security.audit import AuditLogger
from teotl.core.security.enforcement import create_enforcer
from teotl.core.security.policy import SecurityPolicy


class SecurityPanel:
    """Rich terminal display for security information."""

    def __init__(self, console: Console | None = None):
        """Initialize security panel.

        Args:
            console: Rich console (creates default if None)
        """
        self.console = console or Console()

    def show_status(self, workspace_dir: Path) -> None:
        """Show comprehensive security status.

        Args:
            workspace_dir: Agent workspace directory
        """
        # Load enforcer
        enforcer = create_enforcer(workspace_dir)
        if not enforcer:
            self.console.print(
                Panel(
                    "[yellow]Security not enabled for this agent.[/yellow]\n"
                    "Run the wizard to configure security: forge onboard",
                    title="[bold red]Security Status[/bold red]",
                    border_style="red",
                )
            )
            return

        status = enforcer.get_security_status()

        # Create panels
        policy_panel = self._create_policy_panel(status)
        cost_panel = self._create_cost_panel(status)
        rate_panel = self._create_rate_panel(status)
        compliance_panel = self._create_compliance_panel(status)

        # Combine into group
        group = Group(
            policy_panel,
            cost_panel,
            rate_panel,
            compliance_panel,
        )

        # Show in main panel
        self.console.print(
            Panel(
                group,
                title=f"[bold cyan]Security Status: {status['agent_id']}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    def _create_policy_panel(self, status: dict) -> Panel:
        """Create policy information panel."""
        content = Text()
        content.append("Version: ", style="bold")
        content.append(f"{status['policy_version']}\n")
        content.append("Log Level: ", style="bold")
        content.append(f"{status['log_level']}\n")

        return Panel(
            content,
            title="[bold]Policy[/bold]",
            border_style="blue",
            padding=(0, 1),
        )

    def _create_cost_panel(self, status: dict) -> Panel:
        """Create cost limits panel with progress bars."""
        costs = status["costs"]

        # Create progress bars
        hourly_pct = (costs["current"]["hourly"] / costs["limits"]["hourly"]) * 100
        daily_pct = (costs["current"]["daily"] / costs["limits"]["daily"]) * 100
        monthly_pct = (costs["current"]["monthly"] / costs["limits"]["monthly"]) * 100

        # Determine colors based on usage
        def get_color(pct: float) -> str:
            if pct >= 90:
                return "red"
            elif pct >= 75:
                return "yellow"
            else:
                return "green"

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", width=8)
        table.add_column(width=40)
        table.add_column(style="dim", width=20)

        # Hourly
        hourly_bar = self._create_bar(hourly_pct, get_color(hourly_pct))
        table.add_row(
            "Hourly:",
            hourly_bar,
            f"${costs['current']['hourly']:.2f} / ${costs['limits']['hourly']:.2f}",
        )

        # Daily
        daily_bar = self._create_bar(daily_pct, get_color(daily_pct))
        table.add_row(
            "Daily:",
            daily_bar,
            f"${costs['current']['daily']:.2f} / ${costs['limits']['daily']:.2f}",
        )

        # Monthly
        monthly_bar = self._create_bar(monthly_pct, get_color(monthly_pct))
        table.add_row(
            "Monthly:",
            monthly_bar,
            f"${costs['current']['monthly']:.2f} / ${costs['limits']['monthly']:.2f}",
        )

        return Panel(
            table,
            title="[bold]Cost Limits[/bold]",
            border_style="blue",
            padding=(0, 1),
        )

    def _create_rate_panel(self, status: dict) -> Panel:
        """Create rate limits panel."""
        rate = status["rate"]

        current = rate["current_per_minute"]
        limit = rate["limit_per_minute"]
        pct = (current / limit) * 100 if limit > 0 else 0

        # Color based on usage
        if pct >= 90:
            color = "red"
        elif pct >= 75:
            color = "yellow"
        else:
            color = "green"

        bar = self._create_bar(pct, color)

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", width=15)
        table.add_column(width=40)
        table.add_column(style="dim", width=20)

        table.add_row(
            "Calls/Minute:",
            bar,
            f"{current} / {limit}",
        )

        return Panel(
            table,
            title="[bold]Rate Limits[/bold]",
            border_style="blue",
            padding=(0, 1),
        )

    def _create_compliance_panel(self, status: dict) -> Panel:
        """Create compliance features panel."""
        comp = status["compliance"]

        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold", width=10)
        table.add_column(width=15)

        # GDPR
        gdpr_status = "[green]✅ Enabled[/green]" if comp["gdpr"] else "[dim]❌ Disabled[/dim]"
        table.add_row("GDPR:", gdpr_status)

        # SOC2
        soc2_status = "[green]✅ Enabled[/green]" if comp["soc2"] else "[dim]❌ Disabled[/dim]"
        table.add_row("SOC2:", soc2_status)

        # HIPAA
        hipaa_status = "[green]✅ Enabled[/green]" if comp["hipaa"] else "[dim]❌ Disabled[/dim]"
        table.add_row("HIPAA:", hipaa_status)

        return Panel(
            table,
            title="[bold]Compliance[/bold]",
            border_style="blue",
            padding=(0, 1),
        )

    def _create_bar(self, percentage: float, color: str) -> str:
        """Create a visual progress bar.

        Args:
            percentage: Percentage complete (0-100)
            color: Color for the bar

        Returns:
            Formatted progress bar string
        """
        width = 30
        filled = int((percentage / 100) * width)
        empty = width - filled

        bar = "█" * filled + "░" * empty
        return f"[{color}]{bar}[/{color}] {percentage:.1f}%"

    def show_recent_logs(
        self,
        workspace_dir: Path,
        limit: int = 10,
        violations_only: bool = False,
    ) -> None:
        """Show recent audit log entries.

        Args:
            workspace_dir: Agent workspace directory
            limit: Maximum number of entries to show
            violations_only: Only show violations
        """
        # Load policy and audit logger
        policy_path = workspace_dir / "security.yaml"
        if not policy_path.exists():
            self.console.print("[yellow]Security not enabled for this agent.[/yellow]")
            return

        try:
            policy = SecurityPolicy.from_file(policy_path)
        except Exception as e:
            self.console.print(f"[red]Failed to load policy: {e}[/red]")
            return

        audit = AuditLogger(policy, workspace_dir)

        # Read recent logs (last 24 hours)
        start_date = datetime.now() - timedelta(days=1)
        try:
            entries = audit.read_logs(
                start_date=start_date,
                violations_only=violations_only,
            )
        except Exception as e:
            self.console.print(f"[red]Failed to read logs: {e}[/red]")
            return

        if not entries:
            self.console.print("[dim]No recent log entries.[/dim]")
            return

        # Create table
        table = Table(
            title=f"Recent Audit Logs (last {limit})",
            show_header=True,
            header_style="bold cyan",
            border_style="blue",
        )

        table.add_column("Time", style="dim", width=16)
        table.add_column("Event", width=20)
        table.add_column("Tool", width=20)
        table.add_column("Status", width=10)
        table.add_column("Cost", justify="right", width=10)

        # Add recent entries
        for entry in entries[-limit:]:
            # Format timestamp
            try:
                ts = datetime.fromisoformat(entry.timestamp)
                time_str = ts.strftime("%m-%d %H:%M:%S")
            except Exception:
                time_str = entry.timestamp[:16]

            # Status
            status = "[green]✓[/green]" if entry.allowed else "[red]✗[/red]"

            # Cost
            cost_str = f"${entry.cost:.4f}" if entry.cost else "-"

            # Tool name
            tool = entry.tool or "-"

            table.add_row(
                time_str,
                entry.event_type,
                tool,
                status,
                cost_str,
            )

        self.console.print(table)

    def show_summary(self, workspace_dir: Path, days: int = 7) -> None:
        """Show security summary for recent period.

        Args:
            workspace_dir: Agent workspace directory
            days: Number of days to summarize
        """
        # Load policy and audit logger
        policy_path = workspace_dir / "security.yaml"
        if not policy_path.exists():
            self.console.print("[yellow]Security not enabled for this agent.[/yellow]")
            return

        try:
            policy = SecurityPolicy.from_file(policy_path)
        except Exception as e:
            self.console.print(f"[red]Failed to load policy: {e}[/red]")
            return

        audit = AuditLogger(policy, workspace_dir)

        # Read logs for period
        start_date = datetime.now() - timedelta(days=days)
        try:
            entries = audit.read_logs(start_date=start_date)
        except Exception as e:
            self.console.print(f"[red]Failed to read logs: {e}[/red]")
            return

        # Calculate stats
        total_events = len(entries)
        violations = sum(1 for e in entries if not e.allowed)
        total_cost = sum(e.cost for e in entries if e.cost)

        # Event counts by type
        event_counts: dict[str, int] = {}
        for entry in entries:
            event_counts[entry.event_type] = event_counts.get(entry.event_type, 0) + 1

        # Create summary panel
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", width=20)
        table.add_column(width=30)

        table.add_row("Period:", f"Last {days} days")
        table.add_row("Total Events:", str(total_events))

        if violations > 0:
            table.add_row("Violations:", f"[red]{violations}[/red]")
        else:
            table.add_row("Violations:", "[green]0[/green]")

        table.add_row("Total Cost:", f"${total_cost:.2f}")

        # Top events
        if event_counts:
            top_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            events_str = ", ".join(f"{evt}: {cnt}" for evt, cnt in top_events)
            table.add_row("Top Events:", events_str)

        self.console.print(
            Panel(
                table,
                title=f"[bold cyan]Security Summary: {policy.agent_id}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )


def show_security_status(workspace_dir: Path | str) -> None:
    """Show security status for an agent workspace.

    Args:
        workspace_dir: Path to agent workspace
    """
    workspace = Path(workspace_dir).expanduser().resolve()
    panel = SecurityPanel()
    panel.show_status(workspace)


def show_security_logs(
    workspace_dir: Path | str,
    limit: int = 10,
    violations_only: bool = False,
) -> None:
    """Show recent security logs.

    Args:
        workspace_dir: Path to agent workspace
        limit: Maximum entries to show
        violations_only: Only show violations
    """
    workspace = Path(workspace_dir).expanduser().resolve()
    panel = SecurityPanel()
    panel.show_recent_logs(workspace, limit, violations_only)


def show_security_summary(workspace_dir: Path | str, days: int = 7) -> None:
    """Show security summary.

    Args:
        workspace_dir: Path to agent workspace
        days: Number of days to summarize
    """
    workspace = Path(workspace_dir).expanduser().resolve()
    panel = SecurityPanel()
    panel.show_summary(workspace, days)

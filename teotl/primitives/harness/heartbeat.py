"""Heartbeat monitoring for autonomous agents.

Provides autonomous oversight through:
1. Health checks (stuck detection, error thresholds, progress monitoring)
2. Escalation (notify user on actionable issues)
3. Auto cleanup (archive old logs, rotate files)

The heartbeat runs periodically and ensures the agent is making progress,
catches issues early, and maintains a clean workspace.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from teotl.primitives.harness.state import StateManager

if TYPE_CHECKING:
    from teotl.primitives.harness.progress import ProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status result from a check."""

    healthy: bool
    check_name: str
    message: str
    severity: str  # "info", "warning", "critical"
    data: dict | None = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class EscalationEvent:
    """Event that requires user attention."""

    title: str
    message: str
    severity: str  # "warning", "critical"
    context: dict
    suggested_actions: list[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_markdown(self) -> str:
        """Format as markdown for notification."""
        md = f"# ⚠️ {self.title}\n\n"
        md += f"**Severity:** {self.severity.upper()}\n\n"
        md += f"**Time:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += f"## Issue\n\n{self.message}\n\n"

        if self.context:
            md += "## Context\n\n"
            for key, value in self.context.items():
                md += f"- **{key}:** {value}\n"
            md += "\n"

        if self.suggested_actions:
            md += "## Suggested Actions\n\n"
            for i, action in enumerate(self.suggested_actions, 1):
                md += f"{i}. {action}\n"
            md += "\n"

        return md


class HealthCheck:
    """Base class for health checks."""

    def __init__(self, name: str, enabled: bool = True):
        """Initialize health check.

        Args:
            name: Name of the health check
            enabled: Whether check is enabled
        """
        self.name = name
        self.enabled = enabled

    def check(self, **context) -> HealthStatus:
        """Run health check.

        Args:
            **context: Context data for check

        Returns:
            HealthStatus
        """
        raise NotImplementedError


class StuckDetectionCheck(HealthCheck):
    """Detects if agent is stuck (no progress for N turns)."""

    def __init__(
        self,
        max_turns_without_progress: int = 10,
        enabled: bool = True,
    ):
        """Initialize stuck detection.

        Args:
            max_turns_without_progress: Max turns without progress before flagging
            enabled: Whether check is enabled
        """
        super().__init__(name="stuck_detection", enabled=enabled)
        self.max_turns_without_progress = max_turns_without_progress

    def check(self, **context) -> HealthStatus:
        """Check if agent is stuck."""
        state: StateManager = context.get("state")
        progress: ProgressTracker = context.get("progress")

        if not state or not progress:
            return HealthStatus(
                healthy=True,
                check_name=self.name,
                message="Skipped (no state or progress available)",
                severity="info",
            )

        # Check turns without progress
        last_progress_turn = state.get("last_progress_turn", 0)
        current_turn = state.get("current_turn", 0)
        turns_stuck = current_turn - last_progress_turn

        if turns_stuck > self.max_turns_without_progress:
            return HealthStatus(
                healthy=False,
                check_name=self.name,
                message=f"Agent stuck: {turns_stuck} turns without progress",
                severity="critical",
                data={
                    "turns_stuck": turns_stuck,
                    "max_allowed": self.max_turns_without_progress,
                    "last_progress_turn": last_progress_turn,
                    "current_turn": current_turn,
                },
            )

        return HealthStatus(
            healthy=True,
            check_name=self.name,
            message=f"Agent making progress ({turns_stuck}/{self.max_turns_without_progress} turns)",
            severity="info",
            data={"turns_stuck": turns_stuck},
        )


class ErrorThresholdCheck(HealthCheck):
    """Detects excessive consecutive errors."""

    def __init__(
        self,
        max_consecutive_errors: int = 5,
        enabled: bool = True,
    ):
        """Initialize error threshold check.

        Args:
            max_consecutive_errors: Max consecutive errors before flagging
            enabled: Whether check is enabled
        """
        super().__init__(name="error_threshold", enabled=enabled)
        self.max_consecutive_errors = max_consecutive_errors

    def check(self, **context) -> HealthStatus:
        """Check error threshold."""
        state: StateManager = context.get("state")

        if not state:
            return HealthStatus(
                healthy=True,
                check_name=self.name,
                message="Skipped (no state available)",
                severity="info",
            )

        # Check consecutive errors
        consecutive_errors = state.get("consecutive_errors", 0)

        if consecutive_errors >= self.max_consecutive_errors:
            return HealthStatus(
                healthy=False,
                check_name=self.name,
                message=f"Too many consecutive errors: {consecutive_errors}",
                severity="critical",
                data={
                    "consecutive_errors": consecutive_errors,
                    "max_allowed": self.max_consecutive_errors,
                    "last_error": state.get("last_error"),
                },
            )

        return HealthStatus(
            healthy=True,
            check_name=self.name,
            message=f"Error count acceptable ({consecutive_errors}/{self.max_consecutive_errors})",
            severity="info",
            data={"consecutive_errors": consecutive_errors},
        )


class ProgressRateCheck(HealthCheck):
    """Monitors rate of progress over time."""

    def __init__(
        self,
        min_completion_per_hour: float = 5.0,
        enabled: bool = True,
    ):
        """Initialize progress rate check.

        Args:
            min_completion_per_hour: Minimum completion rate (% per hour)
            enabled: Whether check is enabled
        """
        super().__init__(name="progress_rate", enabled=enabled)
        self.min_completion_per_hour = min_completion_per_hour

    def check(self, **context) -> HealthStatus:
        """Check progress rate."""
        progress: ProgressTracker = context.get("progress")
        state: StateManager = context.get("state")

        if not progress or not state:
            return HealthStatus(
                healthy=True,
                check_name=self.name,
                message="Skipped (no progress or state available)",
                severity="info",
            )

        # Get start time and current progress
        start_time = state.get("execution_start_time")
        if not start_time:
            return HealthStatus(
                healthy=True,
                check_name=self.name,
                message="Skipped (no start time recorded)",
                severity="info",
            )

        start_dt = datetime.fromisoformat(start_time)
        elapsed = (datetime.now() - start_dt).total_seconds() / 3600  # hours

        if elapsed < 0.1:  # Less than 6 minutes
            return HealthStatus(
                healthy=True,
                check_name=self.name,
                message="Skipped (execution just started)",
                severity="info",
            )

        # Calculate progress rate
        if progress.exists():
            state_data = progress.read()
            completion_pct = state_data.completion_percentage
            rate = completion_pct / elapsed  # % per hour
        else:
            rate = 0.0

        if rate < self.min_completion_per_hour:
            return HealthStatus(
                healthy=False,
                check_name=self.name,
                message=f"Progress rate too low: {rate:.1f}%/hour (min: {self.min_completion_per_hour}%/hour)",
                severity="warning",
                data={
                    "rate": rate,
                    "min_rate": self.min_completion_per_hour,
                    "elapsed_hours": elapsed,
                },
            )

        return HealthStatus(
            healthy=True,
            check_name=self.name,
            message=f"Progress rate healthy: {rate:.1f}%/hour",
            severity="info",
            data={"rate": rate},
        )


class EscalationPolicy:
    """Defines when and how to escalate issues."""

    def __init__(
        self,
        notify_on_critical: bool = True,
        notify_on_warning: bool = False,
        handlers: list[Callable[[EscalationEvent], None]] | None = None,
    ):
        """Initialize escalation policy.

        Args:
            notify_on_critical: Escalate critical issues
            notify_on_warning: Escalate warnings
            handlers: Callables to handle escalation events
        """
        self.notify_on_critical = notify_on_critical
        self.notify_on_warning = notify_on_warning
        self.handlers = handlers or []

    def should_escalate(self, status: HealthStatus) -> bool:
        """Check if status should be escalated.

        Args:
            status: Health status to check

        Returns:
            True if should escalate
        """
        if not status.healthy:
            if status.severity == "critical" and self.notify_on_critical:
                return True
            if status.severity == "warning" and self.notify_on_warning:
                return True
        return False

    def escalate(self, event: EscalationEvent) -> None:
        """Escalate an event.

        Args:
            event: Event to escalate
        """
        logger.warning(f"ESCALATION: {event.title}")

        # Call handlers
        for handler in self.handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Escalation handler failed: {e}")


class CleanupPolicy:
    """Defines cleanup rules for workspace artifacts."""

    def __init__(
        self,
        archive_logs_older_than_days: int = 7,
        max_archived_plans: int = 10,
        enabled: bool = True,
    ):
        """Initialize cleanup policy.

        Args:
            archive_logs_older_than_days: Archive logs older than N days
            max_archived_plans: Keep max N archived plans
            enabled: Whether cleanup is enabled
        """
        self.archive_logs_older_than_days = archive_logs_older_than_days
        self.max_archived_plans = max_archived_plans
        self.enabled = enabled

    def cleanup(self, workspace_dir: Path) -> dict:
        """Run cleanup on workspace.

        Args:
            workspace_dir: Workspace directory

        Returns:
            Cleanup metrics
        """
        if not self.enabled:
            return {"skipped": True}

        metrics = {
            "archived_plans_removed": 0,
            "old_logs_archived": 0,
        }

        # Cleanup old archived plans
        archived_plans = list(workspace_dir.glob("PLAN_*.md"))
        if len(archived_plans) > self.max_archived_plans:
            # Sort by modification time, oldest first
            archived_plans.sort(key=lambda p: p.stat().st_mtime)

            # Remove oldest
            to_remove = len(archived_plans) - self.max_archived_plans
            for plan in archived_plans[:to_remove]:
                logger.info(f"Removing old archived plan: {plan.name}")
                plan.unlink()
                metrics["archived_plans_removed"] += 1

        # Archive old logs (example: DECISION_LOG.md)
        cutoff_date = datetime.now() - timedelta(days=self.archive_logs_older_than_days)
        decision_log = workspace_dir / "DECISION_LOG.md"

        if decision_log.exists():
            mtime = datetime.fromtimestamp(decision_log.stat().st_mtime)
            if mtime < cutoff_date:
                # Archive it
                archive_name = f"DECISION_LOG_{mtime.strftime('%Y%m%d')}.md"
                archive_path = workspace_dir / "archive" / archive_name

                archive_path.parent.mkdir(exist_ok=True)
                decision_log.rename(archive_path)

                logger.info(f"Archived old decision log to: {archive_name}")
                metrics["old_logs_archived"] += 1

        return metrics


class HeartbeatMonitor:
    """Monitors agent health and performs periodic oversight.

    Usage:
        monitor = HeartbeatMonitor(
            agent_id="coding-assistant",
            workspace_dir=workspace,
            checks=[
                StuckDetectionCheck(max_turns_without_progress=10),
                ErrorThresholdCheck(max_consecutive_errors=5),
                ProgressRateCheck(min_completion_per_hour=5.0),
            ],
            escalation_policy=EscalationPolicy(
                notify_on_critical=True,
                handlers=[log_handler, email_handler],
            ),
            cleanup_policy=CleanupPolicy(
                archive_logs_older_than_days=7,
                max_archived_plans=10,
            ),
        )

        # Run heartbeat check
        result = monitor.heartbeat(state=state, progress=progress)

        if result["escalations"]:
            print("Issues detected!")
    """

    def __init__(
        self,
        agent_id: str,
        workspace_dir: Path,
        checks: list[HealthCheck] | None = None,
        escalation_policy: EscalationPolicy | None = None,
        cleanup_policy: CleanupPolicy | None = None,
        check_interval_turns: int = 5,
    ):
        """Initialize heartbeat monitor.

        Args:
            agent_id: Agent identifier
            workspace_dir: Workspace directory
            checks: Health checks to run
            escalation_policy: Escalation policy
            cleanup_policy: Cleanup policy
            check_interval_turns: Run heartbeat every N turns
        """
        self.agent_id = agent_id
        self.workspace_dir = Path(workspace_dir)
        self.checks = checks or self._default_checks()
        self.escalation_policy = escalation_policy or EscalationPolicy()
        self.cleanup_policy = cleanup_policy or CleanupPolicy()
        self.check_interval_turns = check_interval_turns

        self.last_heartbeat_turn = 0
        self.heartbeat_count = 0

    def _default_checks(self) -> list[HealthCheck]:
        """Create default health checks.

        Returns:
            List of default checks
        """
        return [
            StuckDetectionCheck(max_turns_without_progress=10),
            ErrorThresholdCheck(max_consecutive_errors=5),
            ProgressRateCheck(min_completion_per_hour=5.0),
        ]

    def should_run_heartbeat(self, current_turn: int) -> bool:
        """Check if heartbeat should run.

        Args:
            current_turn: Current turn number

        Returns:
            True if should run
        """
        turns_since_last = current_turn - self.last_heartbeat_turn
        return turns_since_last >= self.check_interval_turns

    def heartbeat(self, **context) -> dict:
        """Run heartbeat check.

        Args:
            **context: Context for health checks (state, progress, etc.)

        Returns:
            Heartbeat result with status and metrics
        """
        self.heartbeat_count += 1
        current_turn = context.get("state", StateManager(self.agent_id)).get("current_turn", 0)
        self.last_heartbeat_turn = current_turn

        logger.info(f"Running heartbeat check #{self.heartbeat_count} at turn {current_turn}")

        # Run health checks
        statuses = []
        for check in self.checks:
            if check.enabled:
                try:
                    status = check.check(**context)
                    statuses.append(status)
                    logger.debug(f"  {check.name}: {status.message}")
                except Exception as e:
                    logger.error(f"Health check {check.name} failed: {e}")

        # Check for escalations
        escalations = []
        for status in statuses:
            if self.escalation_policy.should_escalate(status):
                event = self._create_escalation_event(status)
                escalations.append(event)
                self.escalation_policy.escalate(event)

        # Run cleanup
        cleanup_metrics = {}
        if self.cleanup_policy.enabled:
            try:
                cleanup_metrics = self.cleanup_policy.cleanup(self.workspace_dir)
                logger.debug(f"  Cleanup: {cleanup_metrics}")
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")

        # Overall health
        all_healthy = all(s.healthy for s in statuses)

        result = {
            "healthy": all_healthy,
            "heartbeat_count": self.heartbeat_count,
            "turn": current_turn,
            "checks_run": len(statuses),
            "checks_passed": sum(1 for s in statuses if s.healthy),
            "checks_failed": sum(1 for s in statuses if not s.healthy),
            "escalations": escalations,
            "cleanup_metrics": cleanup_metrics,
            "timestamp": datetime.now().isoformat(),
        }

        if not all_healthy:
            logger.warning(f"Heartbeat detected issues: {result['checks_failed']} checks failed")
        else:
            logger.info("Heartbeat: All checks passed ✅")

        return result

    def _create_escalation_event(self, status: HealthStatus) -> EscalationEvent:
        """Create escalation event from health status.

        Args:
            status: Health status

        Returns:
            EscalationEvent
        """
        # Determine suggested actions based on check type
        suggested_actions = []

        if status.check_name == "stuck_detection":
            suggested_actions = [
                "Review PROGRESS.md to see what task the agent is stuck on",
                "Check DECISION_LOG.md for repeated patterns",
                "Consider providing additional context or breaking down the task",
                "Reset agent and start with clearer goals",
            ]
        elif status.check_name == "error_threshold":
            suggested_actions = [
                "Review STATE.json for last_error details",
                "Check if agent lacks necessary permissions or access",
                "Verify workspace environment and dependencies",
                "Consider adjusting worker skills or policy",
            ]
        elif status.check_name == "progress_rate":
            suggested_actions = [
                "Review PLAN.md to see if steps are too complex",
                "Check if agent is blocked on external dependencies",
                "Consider breaking down plan into smaller steps",
                "Verify worker model has sufficient capability",
            ]

        return EscalationEvent(
            title=f"Agent Health Issue: {status.check_name}",
            message=status.message,
            severity=status.severity,
            context={
                "agent_id": self.agent_id,
                "check_name": status.check_name,
                **(status.data or {}),
            },
            suggested_actions=suggested_actions,
        )

    def get_status_summary(self) -> str:
        """Get human-readable status summary.

        Returns:
            Summary string
        """
        return (
            f"Heartbeat Monitor Status:\n"
            f"  Agent: {self.agent_id}\n"
            f"  Heartbeats: {self.heartbeat_count}\n"
            f"  Last check: Turn {self.last_heartbeat_turn}\n"
            f"  Checks: {len([c for c in self.checks if c.enabled])} enabled\n"
            f"  Escalation: {'enabled' if self.escalation_policy.notify_on_critical else 'disabled'}\n"
            f"  Cleanup: {'enabled' if self.cleanup_policy.enabled else 'disabled'}"
        )

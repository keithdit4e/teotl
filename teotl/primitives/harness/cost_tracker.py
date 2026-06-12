"""Cost tracking and budget enforcement for autonomous agents.

Tracks costs across operations and enforces CostLimits to prevent
runaway spending in autonomous execution loops.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from teotl.core.security.policy import CostLimits
from teotl.primitives.harness.exceptions import BudgetExceededError

logger = logging.getLogger(__name__)


class CostTracker:
    """Tracks costs and enforces budget limits.

    Monitors spending across hourly, daily, and monthly windows and
    prevents operations that would exceed configured budget limits.

    Usage:
        tracker = CostTracker(
            limits=CostLimits(
                max_per_hour=5.0,
                max_per_day=50.0,
                max_per_month=500.0,
            ),
            workspace_dir=workspace,
        )

        # Check before spending
        if tracker.can_spend(estimated_cost=15.0):
            # Perform operation
            actual_cost = do_expensive_operation()
            tracker.record(actual_cost, "planning")

        # Get summary
        summary = tracker.get_summary()
        print(f"Spent: ${summary['total_spent']:.2f}")
    """

    def __init__(
        self,
        limits: CostLimits,
        workspace_dir: Path,
        log_file_name: str = "COST_LOG.jsonl",
    ):
        """Initialize cost tracker.

        Args:
            limits: Cost limits configuration
            workspace_dir: Workspace directory for cost log
            log_file_name: Name of cost log file (default: COST_LOG.jsonl)
        """
        self.limits = limits
        self.workspace_dir = Path(workspace_dir)
        self.log_file = self.workspace_dir / log_file_name

        # Current spending
        self.total_spent = 0.0
        self.hourly_spent = 0.0
        self.daily_spent = 0.0
        self.monthly_spent = 0.0

        # Time windows
        self.hour_start = datetime.now()
        self.day_start = datetime.now()
        self.month_start = datetime.now()

        # Load previous costs
        self._load_previous_costs()

    def _load_previous_costs(self) -> None:
        """Load previous costs from log file."""
        if not self.log_file.exists():
            logger.debug(f"No previous cost log found at {self.log_file}")
            return

        try:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            month_ago = now - timedelta(days=30)

            with open(self.log_file) as f:
                for line in f:
                    entry = json.loads(line.strip())
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    cost = entry["cost"]

                    # Accumulate total
                    self.total_spent += cost

                    # Accumulate within time windows
                    if timestamp >= hour_ago:
                        self.hourly_spent += cost
                        self.hour_start = min(self.hour_start, timestamp)

                    if timestamp >= day_ago:
                        self.daily_spent += cost
                        self.day_start = min(self.day_start, timestamp)

                    if timestamp >= month_ago:
                        self.monthly_spent += cost
                        self.month_start = min(self.month_start, timestamp)

            logger.info(
                f"Loaded previous costs: "
                f"${self.hourly_spent:.2f}/hour, "
                f"${self.daily_spent:.2f}/day, "
                f"${self.monthly_spent:.2f}/month"
            )

        except Exception as e:
            logger.error(f"Failed to load previous costs: {e}")

    def _reset_windows_if_needed(self) -> None:
        """Reset time windows that have elapsed."""
        now = datetime.now()

        # Reset hourly window
        if now - self.hour_start >= timedelta(hours=1):
            self.hourly_spent = 0.0
            self.hour_start = now
            logger.debug("Hourly cost window reset")

        # Reset daily window
        if now - self.day_start >= timedelta(days=1):
            self.daily_spent = 0.0
            self.day_start = now
            logger.debug("Daily cost window reset")

        # Reset monthly window
        if now - self.month_start >= timedelta(days=30):
            self.monthly_spent = 0.0
            self.month_start = now
            logger.debug("Monthly cost window reset")

    def can_spend(self, estimated_cost: float) -> bool:
        """Check if estimated cost fits within budget limits.

        Args:
            estimated_cost: Estimated cost of operation

        Returns:
            True if operation can proceed within budget

        Raises:
            BudgetExceededError: If operation would exceed budget
        """
        self._reset_windows_if_needed()

        # Check hourly limit
        if self.hourly_spent + estimated_cost > self.limits.max_per_hour:
            raise BudgetExceededError(
                spent=self.hourly_spent,
                limit=self.limits.max_per_hour,
                limit_type="hourly",
                operation=f"${estimated_cost:.2f} operation",
            )

        # Check daily limit
        if self.daily_spent + estimated_cost > self.limits.max_per_day:
            raise BudgetExceededError(
                spent=self.daily_spent,
                limit=self.limits.max_per_day,
                limit_type="daily",
                operation=f"${estimated_cost:.2f} operation",
            )

        # Check monthly limit if configured
        if (
            self.limits.max_per_month
            and self.monthly_spent + estimated_cost > self.limits.max_per_month
        ):
            raise BudgetExceededError(
                spent=self.monthly_spent,
                limit=self.limits.max_per_month,
                limit_type="monthly",
                operation=f"${estimated_cost:.2f} operation",
            )

        return True

    def record(self, cost: float, operation: str, metadata: dict | None = None) -> None:
        """Record actual cost of operation.

        Args:
            cost: Actual cost incurred
            operation: Operation type (e.g., "planning", "execution", "evaluation")
            metadata: Optional metadata about operation
        """
        self._reset_windows_if_needed()

        # Update totals
        self.total_spent += cost
        self.hourly_spent += cost
        self.daily_spent += cost
        self.monthly_spent += cost

        # Log to file
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "cost": cost,
            "total_spent": self.total_spent,
            "hourly_spent": self.hourly_spent,
            "daily_spent": self.daily_spent,
            "monthly_spent": self.monthly_spent,
            "currency": self.limits.currency,
        }

        if metadata:
            entry["metadata"] = metadata

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Append to JSONL
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        logger.info(f"Recorded cost: ${cost:.2f} for {operation} (total: ${self.total_spent:.2f})")

    def get_summary(self) -> dict:
        """Get current cost summary.

        Returns:
            Dictionary with spending totals and remaining budget
        """
        self._reset_windows_if_needed()

        return {
            "total_spent": self.total_spent,
            "hourly_spent": self.hourly_spent,
            "daily_spent": self.daily_spent,
            "monthly_spent": self.monthly_spent,
            "hourly_remaining": max(0, self.limits.max_per_hour - self.hourly_spent),
            "daily_remaining": max(0, self.limits.max_per_day - self.daily_spent),
            "monthly_remaining": max(0, self.limits.max_per_month - self.monthly_spent)
            if self.limits.max_per_month
            else None,
            "currency": self.limits.currency,
            "limits": {
                "max_per_hour": self.limits.max_per_hour,
                "max_per_day": self.limits.max_per_day,
                "max_per_month": self.limits.max_per_month,
            },
        }

    def estimate_operation_cost(
        self,
        operation_type: str,
        num_steps: int | None = None,
    ) -> float:
        """Estimate cost of operation.

        Args:
            operation_type: Type of operation (planning, execution, evaluation)
            num_steps: Number of steps (for execution)

        Returns:
            Estimated cost in USD

        Note:
            These are rough estimates based on typical usage:
            - Planning (Sonnet): ~$15
            - Execution (Haiku): ~$0.25 per step
            - Evaluation (Sonnet): ~$10
        """
        if operation_type == "planning":
            return 15.0
        elif operation_type == "execution":
            if num_steps is None:
                num_steps = 10  # Default estimate
            return num_steps * 0.25
        elif operation_type == "evaluation":
            return 10.0
        else:
            logger.warning(f"Unknown operation type: {operation_type}")
            return 5.0  # Conservative estimate

    def get_status_message(self) -> str:
        """Get human-readable status message.

        Returns:
            Status message with budget usage
        """
        summary = self.get_summary()

        hourly_pct = (summary["hourly_spent"] / self.limits.max_per_hour) * 100
        daily_pct = (summary["daily_spent"] / self.limits.max_per_day) * 100

        message = f"""Cost Tracker Status:
  Total Spent: ${summary["total_spent"]:.2f}

  Hourly:  ${summary["hourly_spent"]:.2f} / ${self.limits.max_per_hour:.2f} ({hourly_pct:.0f}%)
  Daily:   ${summary["daily_spent"]:.2f} / ${self.limits.max_per_day:.2f} ({daily_pct:.0f}%)
  Monthly: ${summary["monthly_spent"]:.2f} / ${self.limits.max_per_month:.2f}

  Remaining (hourly): ${summary["hourly_remaining"]:.2f}
  Remaining (daily):  ${summary["daily_remaining"]:.2f}
"""

        return message

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"CostTracker("
            f"spent=${self.total_spent:.2f}, "
            f"hourly=${self.hourly_spent:.2f}/{self.limits.max_per_hour:.2f}, "
            f"daily=${self.daily_spent:.2f}/{self.limits.max_per_day:.2f})"
        )

"""Cost and rate tracking for agent execution.

Tracks API costs and enforces limits to prevent runaway spending.
Tracks rate limits to prevent API abuse.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from teotl.core.security.policy import CostLimits, RateLimits


@dataclass
class CostRecord:
    """Cost tracking record."""

    timestamp: datetime
    tool: str
    cost: float
    tokens_used: int | None = None

    def to_dict(self) -> dict:
        """Convert to dict for JSON storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "tool": self.tool,
            "cost": self.cost,
            "tokens_used": self.tokens_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CostRecord:
        """Create from dict."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tool=data["tool"],
            cost=data["cost"],
            tokens_used=data.get("tokens_used"),
        )


class CostTracker:
    """Tracks API costs and enforces limits.

    Persists cost data to JSON file for tracking across restarts.
    Automatically resets hourly/daily/monthly totals.
    """

    def __init__(self, limits: CostLimits, storage_path: Path):
        """Initialize cost tracker.

        Args:
            limits: Cost limits configuration
            storage_path: Path to cost tracking JSON file
        """
        self.limits = limits
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data
        self.records: list[CostRecord] = []
        self._load()

        # Current totals (computed from records)
        self._update_totals()

    def _load(self) -> None:
        """Load cost records from storage."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path) as f:
                data = json.load(f)
                self.records = [CostRecord.from_dict(record) for record in data.get("records", [])]
        except Exception:
            # If file is corrupted, start fresh
            self.records = []

    def _save(self) -> None:
        """Save cost records to storage."""
        data = {"records": [record.to_dict() for record in self.records]}

        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _update_totals(self) -> None:
        """Update current totals from records."""
        now = datetime.now()

        # Calculate cutoff times
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Sum costs
        self.current_hour = sum(r.cost for r in self.records if r.timestamp >= hour_ago)

        self.current_day = sum(r.cost for r in self.records if r.timestamp >= day_ago)

        self.current_month = sum(r.cost for r in self.records if r.timestamp >= month_start)

    def _cleanup_old_records(self) -> None:
        """Remove records older than 1 month."""
        month_ago = datetime.now() - timedelta(days=30)
        self.records = [r for r in self.records if r.timestamp >= month_ago]

    def would_allow(self, estimated_cost: float) -> bool:
        """Check if cost would exceed limits.

        Args:
            estimated_cost: Estimated cost of operation

        Returns:
            True if within limits, False if would exceed
        """
        self._update_totals()

        if self.current_hour + estimated_cost > self.limits.max_per_hour:
            return False

        if self.current_day + estimated_cost > self.limits.max_per_day:
            return False

        return not self.current_month + estimated_cost > self.limits.max_per_month

    def record_cost(
        self,
        tool: str,
        actual_cost: float,
        tokens_used: int | None = None,
    ) -> None:
        """Record actual cost after execution.

        Args:
            tool: Tool that incurred cost
            actual_cost: Actual cost in USD
            tokens_used: Tokens used (if applicable)
        """
        record = CostRecord(
            timestamp=datetime.now(),
            tool=tool,
            cost=actual_cost,
            tokens_used=tokens_used,
        )

        self.records.append(record)
        self._update_totals()

        # Cleanup old records periodically
        if len(self.records) % 100 == 0:
            self._cleanup_old_records()

        # Persist
        self._save()

    def get_remaining(self) -> dict[str, float]:
        """Get remaining budget for each limit.

        Returns:
            Dict with remaining amounts
        """
        self._update_totals()

        return {
            "hourly": self.limits.max_per_hour - self.current_hour,
            "daily": self.limits.max_per_day - self.current_day,
            "monthly": self.limits.max_per_month - self.current_month,
        }

    def get_current(self) -> dict[str, float]:
        """Get current spending for each period.

        Returns:
            Dict with current amounts
        """
        self._update_totals()

        return {
            "hourly": self.current_hour,
            "daily": self.current_day,
            "monthly": self.current_month,
        }


@dataclass
class RateRecord:
    """Rate limit tracking record."""

    timestamp: datetime
    tool: str


class RateLimiter:
    """Tracks API call rates and enforces limits.

    Prevents API abuse by limiting calls per minute.
    """

    def __init__(self, limits: RateLimits):
        """Initialize rate limiter.

        Args:
            limits: Rate limits configuration
        """
        self.limits = limits
        self.records: list[RateRecord] = []

    def _cleanup_old_records(self) -> None:
        """Remove records older than 1 hour."""
        hour_ago = datetime.now() - timedelta(hours=1)
        self.records = [r for r in self.records if r.timestamp >= hour_ago]

    def would_allow(self) -> bool:
        """Check if rate limit allows another call.

        Returns:
            True if within limits, False if would exceed
        """
        self._cleanup_old_records()

        minute_ago = datetime.now() - timedelta(minutes=1)
        calls_last_minute = sum(1 for r in self.records if r.timestamp >= minute_ago)

        return calls_last_minute < self.limits.max_api_calls_per_minute

    def record_call(self, tool: str) -> None:
        """Record an API call.

        Args:
            tool: Tool that made the call
        """
        self.records.append(RateRecord(timestamp=datetime.now(), tool=tool))

        # Cleanup periodically
        if len(self.records) % 50 == 0:
            self._cleanup_old_records()

    def get_current_rate(self) -> int:
        """Get current calls per minute.

        Returns:
            Number of calls in last minute
        """
        self._cleanup_old_records()
        minute_ago = datetime.now() - timedelta(minutes=1)
        return sum(1 for r in self.records if r.timestamp >= minute_ago)

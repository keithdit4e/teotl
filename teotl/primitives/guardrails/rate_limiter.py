"""Rate limiting and cost tracking for LLM API calls.

Prevents:
- Cost explosions from runaway loops
- DoS attacks via excessive requests
- Quota exhaustion
- Multi-tenant abuse

Strategy:
- Request-per-minute (RPM) limits
- Cost-per-hour and cost-per-day budgets
- Token-based limits
- Per-user/per-agent isolation (optional)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    pass


class RateLimiter:
    """
    Token bucket-based rate limiter with cost tracking.

    Tracks requests and costs across multiple time windows:
    - Requests per minute (RPM)
    - Cost per hour
    - Cost per day

    Thread-safe for async usage (single event loop).
    """

    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_cost_per_hour: float = 5.0,
        max_cost_per_day: float = 25.0,
        max_tokens_per_request: int = 200_000,  # Total tokens (input + output)
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            max_requests_per_minute: Maximum requests per minute (default: 60)
            max_cost_per_hour: Maximum cost in USD per hour (default: $5)
            max_cost_per_day: Maximum cost in USD per day (default: $25)
            max_tokens_per_request: Maximum tokens per request (default: 8192)
        """
        self.max_rpm = max_requests_per_minute
        self.max_cost_hour = max_cost_per_hour
        self.max_cost_day = max_cost_per_day
        self.max_tokens = max_tokens_per_request

        # Track requests and costs with timestamps
        self.requests: list[datetime] = []
        self.costs: list[tuple[datetime, float]] = []

        # Statistics
        self.total_requests = 0
        self.total_cost = 0.0
        self.total_tokens = 0

        logger.info(
            f"RateLimiter initialized: {max_requests_per_minute} RPM, "
            f"${max_cost_per_hour}/hr, ${max_cost_per_day}/day"
        )

    def check_rate_limit(self) -> tuple[bool, str]:
        """
        Check if request is allowed under rate limits.

        Returns:
            (allowed, reason): True if allowed, False with reason if denied
        """
        now = datetime.now()

        # RPM check
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [r for r in self.requests if r > minute_ago]

        if len(recent_requests) >= self.max_rpm:
            # Calculate wait time if there are recent requests
            if recent_requests:
                wait_seconds = (recent_requests[0] - minute_ago).total_seconds()
                return False, (
                    f"Rate limit exceeded: {len(recent_requests)}/{self.max_rpm} requests per minute. "
                    f"Retry in {wait_seconds:.0f}s"
                )
            else:
                return False, (
                    f"Rate limit exceeded: {len(recent_requests)}/{self.max_rpm} requests per minute"
                )

        # Hourly cost check
        hour_ago = now - timedelta(hours=1)
        hourly_cost = sum(cost for ts, cost in self.costs if ts > hour_ago)

        if hourly_cost >= self.max_cost_hour:
            return False, (
                f"Hourly cost limit exceeded: ${hourly_cost:.4f}/${self.max_cost_hour:.2f}"
            )

        # Daily cost check
        day_ago = now - timedelta(days=1)
        daily_cost = sum(cost for ts, cost in self.costs if ts > day_ago)

        if daily_cost >= self.max_cost_day:
            return False, (f"Daily cost limit exceeded: ${daily_cost:.4f}/${self.max_cost_day:.2f}")

        return True, ""

    def check_token_limit(self, tokens: int) -> tuple[bool, str]:
        """
        Check if token count is within limits.

        Args:
            tokens: Number of tokens in request

        Returns:
            (allowed, reason): True if allowed, False with reason if denied
        """
        if tokens > self.max_tokens:
            return False, (f"Token limit exceeded: {tokens}/{self.max_tokens} tokens")
        return True, ""

    def record_request(self, cost: float = 0.0, tokens: int = 0) -> None:
        """
        Record a successful request.

        Args:
            cost: Estimated cost in USD
            tokens: Number of tokens used
        """
        now = datetime.now()

        self.requests.append(now)
        if cost > 0:
            self.costs.append((now, cost))

        # Update statistics
        self.total_requests += 1
        self.total_cost += cost
        self.total_tokens += tokens

        # Cleanup old entries (keep last 24 hours)
        cutoff = now - timedelta(days=1)
        self.requests = [r for r in self.requests if r > cutoff]
        self.costs = [(ts, c) for ts, c in self.costs if ts > cutoff]

        logger.debug(
            f"Request recorded: cost=${cost:.6f}, tokens={tokens}, "
            f"total_cost=${self.total_cost:.4f}"
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Get current usage statistics.

        Returns:
            Dict with usage metrics
        """
        now = datetime.now()

        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        rpm = len([r for r in self.requests if r > minute_ago])
        hourly_cost = sum(cost for ts, cost in self.costs if ts > hour_ago)
        daily_cost = sum(cost for ts, cost in self.costs if ts > day_ago)

        return {
            "requests_per_minute": rpm,
            "requests_per_minute_limit": self.max_rpm,
            "cost_per_hour": hourly_cost,
            "cost_per_hour_limit": self.max_cost_hour,
            "cost_per_day": daily_cost,
            "cost_per_day_limit": self.max_cost_day,
            "total_requests": self.total_requests,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
        }

    def reset_stats(self) -> None:
        """Reset all statistics and history."""
        self.requests.clear()
        self.costs.clear()
        self.total_requests = 0
        self.total_cost = 0.0
        self.total_tokens = 0
        logger.info("RateLimiter statistics reset")


class MultiUserRateLimiter:
    """
    Rate limiter with per-user isolation.

    Maintains separate rate limits for each user/agent.
    Useful for multi-tenant deployments.
    """

    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_cost_per_hour: float = 5.0,
        max_cost_per_day: float = 25.0,
        max_tokens_per_request: int = 200_000,  # Total tokens (input + output)
    ) -> None:
        """
        Initialize multi-user rate limiter.

        Each user gets their own rate limits.
        """
        self.default_limits = {
            "max_requests_per_minute": max_requests_per_minute,
            "max_cost_per_hour": max_cost_per_hour,
            "max_cost_per_day": max_cost_per_day,
            "max_tokens_per_request": max_tokens_per_request,
        }

        # Per-user rate limiters
        self.limiters: dict[str, RateLimiter] = defaultdict(
            lambda: RateLimiter(**self.default_limits)
        )

        logger.info(f"MultiUserRateLimiter initialized with defaults: {self.default_limits}")

    def get_limiter(self, user_id: str) -> RateLimiter:
        """Get rate limiter for a specific user."""
        return self.limiters[user_id]

    def check_rate_limit(self, user_id: str) -> tuple[bool, str]:
        """Check rate limit for a specific user."""
        return self.limiters[user_id].check_rate_limit()

    def check_token_limit(self, user_id: str, tokens: int) -> tuple[bool, str]:
        """Check token limit for a specific user."""
        return self.limiters[user_id].check_token_limit(tokens)

    def record_request(self, user_id: str, cost: float = 0.0, tokens: int = 0) -> None:
        """Record request for a specific user."""
        self.limiters[user_id].record_request(cost, tokens)

    def get_stats(self, user_id: str) -> dict[str, Any]:
        """Get statistics for a specific user."""
        return self.limiters[user_id].get_stats()

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all users."""
        return {user_id: limiter.get_stats() for user_id, limiter in self.limiters.items()}


def estimate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Estimate API cost based on usage.

    Args:
        provider: Provider name ("anthropic", "openai", etc.)
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in USD
    """
    # Pricing as of March 2026 (update as needed)
    pricing = {
        "anthropic": {
            "claude-opus-4-20250514": (0.015, 0.075),  # per 1K tokens
            "claude-sonnet-4-20250514": (0.003, 0.015),
            "claude-haiku-4-20250514": (0.00025, 0.00125),
        },
        "openai": {
            "gpt-4o": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4-turbo": (0.01, 0.03),
        },
    }

    # Get pricing for provider/model
    if provider.lower() in pricing:
        model_pricing = pricing[provider.lower()].get(model)
        if model_pricing:
            input_cost_per_1k, output_cost_per_1k = model_pricing
            cost = (input_tokens / 1000) * input_cost_per_1k + (
                output_tokens / 1000
            ) * output_cost_per_1k
            return cost

    # Unknown provider/model - return 0 (no cost tracking)
    logger.warning(
        f"Unknown pricing for {provider}/{model}. Cost tracking disabled for this model."
    )
    return 0.0

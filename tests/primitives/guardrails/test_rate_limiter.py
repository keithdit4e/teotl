"""Tests for rate limiter and cost tracking."""

from datetime import datetime, timedelta

from teotl.primitives.guardrails.rate_limiter import (
    MultiUserRateLimiter,
    RateLimiter,
    estimate_cost,
)


class TestRateLimiter:
    """Test basic rate limiter functionality."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(
            max_requests_per_minute=60,
            max_cost_per_hour=5.0,
            max_cost_per_day=25.0,
        )

        assert limiter.max_rpm == 60
        assert limiter.max_cost_hour == 5.0
        assert limiter.max_cost_day == 25.0

    def test_requests_per_minute_limit(self):
        """Test RPM limit enforcement."""
        limiter = RateLimiter(max_requests_per_minute=3)

        # First 3 requests should succeed
        for _i in range(3):
            allowed, reason = limiter.check_rate_limit()
            assert allowed is True
            limiter.record_request()

        # 4th request should fail
        allowed, reason = limiter.check_rate_limit()
        assert allowed is False
        assert "Rate limit exceeded" in reason
        assert "3/3 requests per minute" in reason

    def test_cost_per_hour_limit(self):
        """Test hourly cost limit enforcement."""
        limiter = RateLimiter(max_cost_per_hour=1.0)

        # Record requests up to limit
        limiter.record_request(cost=0.4)
        limiter.record_request(cost=0.4)

        # Still under limit
        allowed, reason = limiter.check_rate_limit()
        assert allowed is True

        # This would exceed limit
        limiter.record_request(cost=0.3)
        allowed, reason = limiter.check_rate_limit()
        assert allowed is False
        assert "Hourly cost limit exceeded" in reason

    def test_cost_per_day_limit(self):
        """Test daily cost limit enforcement."""
        # Set high hourly limit so daily limit is hit first
        limiter = RateLimiter(max_cost_per_hour=100.0, max_cost_per_day=5.0)

        # Record requests up to limit
        for _ in range(4):
            limiter.record_request(cost=1.2)

        # Still under limit (4 * 1.2 = 4.8)
        allowed, reason = limiter.check_rate_limit()
        assert allowed is True

        # This would exceed daily limit
        limiter.record_request(cost=1.0)
        allowed, reason = limiter.check_rate_limit()
        assert allowed is False
        assert "Daily cost limit exceeded" in reason

    def test_token_limit(self):
        """Test token limit enforcement."""
        limiter = RateLimiter(max_tokens_per_request=1000)

        # Within limit
        allowed, reason = limiter.check_token_limit(500)
        assert allowed is True

        # Exceeds limit
        allowed, reason = limiter.check_token_limit(1500)
        assert allowed is False
        assert "Token limit exceeded" in reason

    def test_cleanup_old_entries(self):
        """Test that old entries are cleaned up."""
        limiter = RateLimiter()

        # Record a request
        limiter.record_request(cost=1.0)
        assert len(limiter.requests) == 1
        assert len(limiter.costs) == 1

        # Manually set old timestamp
        old_time = datetime.now() - timedelta(days=2)
        limiter.requests[0] = old_time
        limiter.costs[0] = (old_time, 1.0)

        # Record new request (triggers cleanup)
        limiter.record_request(cost=0.5)

        # Old entries should be removed
        assert len(limiter.requests) == 1
        assert len(limiter.costs) == 1

    def test_get_stats(self):
        """Test statistics retrieval."""
        limiter = RateLimiter(
            max_requests_per_minute=60,
            max_cost_per_hour=5.0,
            max_cost_per_day=25.0,
        )

        limiter.record_request(cost=0.5, tokens=100)
        limiter.record_request(cost=0.3, tokens=75)

        stats = limiter.get_stats()

        assert stats["requests_per_minute"] == 2
        assert stats["requests_per_minute_limit"] == 60
        assert stats["cost_per_hour"] == 0.8
        assert stats["cost_per_day"] == 0.8
        assert stats["total_requests"] == 2
        assert stats["total_cost"] == 0.8
        assert stats["total_tokens"] == 175

    def test_reset_stats(self):
        """Test statistics reset."""
        limiter = RateLimiter()

        limiter.record_request(cost=1.0, tokens=100)
        limiter.record_request(cost=0.5, tokens=50)

        assert limiter.total_requests == 2
        assert limiter.total_cost == 1.5
        assert limiter.total_tokens == 150

        limiter.reset_stats()

        assert limiter.total_requests == 0
        assert limiter.total_cost == 0.0
        assert limiter.total_tokens == 0
        assert len(limiter.requests) == 0
        assert len(limiter.costs) == 0

    def test_no_cost_tracking(self):
        """Test that requests without cost still count toward RPM."""
        limiter = RateLimiter(max_requests_per_minute=2)

        limiter.record_request()  # No cost
        limiter.record_request()  # No cost

        # Should still hit RPM limit
        allowed, reason = limiter.check_rate_limit()
        assert allowed is False


class TestMultiUserRateLimiter:
    """Test multi-user rate limiter."""

    def test_per_user_isolation(self):
        """Test that users have separate rate limits."""
        limiter = MultiUserRateLimiter(max_requests_per_minute=2)

        # User A makes 2 requests
        limiter.record_request("user_a")
        limiter.record_request("user_a")

        # User A should be limited
        allowed, reason = limiter.check_rate_limit("user_a")
        assert allowed is False

        # User B should not be limited
        allowed, reason = limiter.check_rate_limit("user_b")
        assert allowed is True

    def test_per_user_cost_tracking(self):
        """Test that costs are tracked separately per user."""
        limiter = MultiUserRateLimiter(max_cost_per_hour=1.0)

        limiter.record_request("user_a", cost=0.8)
        limiter.record_request("user_b", cost=0.3)

        # User A should be near limit
        allowed, _ = limiter.check_rate_limit("user_a")
        assert allowed is True

        limiter.record_request("user_a", cost=0.3)
        allowed, _ = limiter.check_rate_limit("user_a")
        assert allowed is False

        # User B should still be fine
        allowed, _ = limiter.check_rate_limit("user_b")
        assert allowed is True

    def test_get_all_stats(self):
        """Test getting statistics for all users."""
        limiter = MultiUserRateLimiter()

        limiter.record_request("user_a", cost=0.5, tokens=100)
        limiter.record_request("user_b", cost=0.3, tokens=75)

        all_stats = limiter.get_all_stats()

        assert "user_a" in all_stats
        assert "user_b" in all_stats
        assert all_stats["user_a"]["total_cost"] == 0.5
        assert all_stats["user_b"]["total_cost"] == 0.3


class TestCostEstimation:
    """Test cost estimation for different providers."""

    def test_anthropic_claude_opus(self):
        """Test cost estimation for Claude Opus."""
        cost = estimate_cost(
            provider="anthropic",
            model="claude-opus-4-20250514",
            input_tokens=1000,
            output_tokens=500,
        )

        # (1000/1000) * 0.015 + (500/1000) * 0.075 = 0.015 + 0.0375 = 0.0525
        assert abs(cost - 0.0525) < 0.0001

    def test_anthropic_claude_sonnet(self):
        """Test cost estimation for Claude Sonnet."""
        cost = estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=1000,
        )

        # (1000/1000) * 0.003 + (1000/1000) * 0.015 = 0.003 + 0.015 = 0.018
        assert abs(cost - 0.018) < 0.0001

    def test_anthropic_claude_haiku(self):
        """Test cost estimation for Claude Haiku."""
        cost = estimate_cost(
            provider="anthropic",
            model="claude-haiku-4-20250514",
            input_tokens=10000,
            output_tokens=5000,
        )

        # (10000/1000) * 0.00025 + (5000/1000) * 0.00125 = 0.0025 + 0.00625 = 0.00875
        assert abs(cost - 0.00875) < 0.0001

    def test_openai_gpt4o(self):
        """Test cost estimation for GPT-4o."""
        cost = estimate_cost(
            provider="openai",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=1000,
        )

        # (1000/1000) * 0.005 + (1000/1000) * 0.015 = 0.005 + 0.015 = 0.020
        assert abs(cost - 0.020) < 0.0001

    def test_unknown_provider(self):
        """Test that unknown providers return 0 cost."""
        cost = estimate_cost(
            provider="unknown",
            model="unknown-model",
            input_tokens=1000,
            output_tokens=1000,
        )

        assert cost == 0.0

    def test_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        cost = estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=0,
            output_tokens=0,
        )

        assert cost == 0.0


class TestRateLimiterEdgeCases:
    """Test edge cases and error conditions."""

    def test_negative_cost(self):
        """Test that negative costs are handled."""
        limiter = RateLimiter()

        # Should not raise error
        limiter.record_request(cost=-0.5)

        stats = limiter.get_stats()
        assert stats["total_cost"] == -0.5

    def test_zero_limits(self):
        """Test rate limiter with zero limits."""
        limiter = RateLimiter(
            max_requests_per_minute=0,
            max_cost_per_hour=0.0,
        )

        # Should immediately fail
        allowed, _ = limiter.check_rate_limit()
        assert allowed is False

    def test_very_high_limits(self):
        """Test rate limiter with very high limits."""
        limiter = RateLimiter(
            max_requests_per_minute=1_000_000,
            max_cost_per_hour=1_000_000.0,
            max_cost_per_day=10_000_000.0,  # Also set high daily limit
        )

        # Should allow many requests
        for _ in range(100):
            allowed, _ = limiter.check_rate_limit()
            assert allowed is True
            limiter.record_request(cost=100.0)

    def test_concurrent_requests_simulation(self):
        """Simulate concurrent requests (within same event loop)."""
        limiter = RateLimiter(max_requests_per_minute=10)

        # Simulate 15 requests happening "concurrently"
        results = []
        for i in range(15):
            allowed, reason = limiter.check_rate_limit()
            results.append((i, allowed, reason))
            if allowed:
                limiter.record_request()

        # First 10 should succeed, last 5 should fail
        successful = sum(1 for _, allowed, _ in results if allowed)
        failed = sum(1 for _, allowed, _ in results if not allowed)

        assert successful == 10
        assert failed == 5

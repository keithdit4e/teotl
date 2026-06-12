"""Tests for rate-limited provider wrapper."""

from unittest.mock import AsyncMock

import pytest

from teotl.core.provider import Provider
from teotl.core.rate_limited_provider import RateLimitedProvider
from teotl.core.types import CompletionResult
from teotl.primitives.guardrails.rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
)


class MockProvider(Provider):
    """Mock provider for testing."""

    def __init__(self, model="test-model"):
        self._model = model
        self.complete_called = 0

    async def complete(self, **kwargs):
        self.complete_called += 1
        return CompletionResult(
            content="Test response",
            tool_calls=[],
            done=True,
            usage={
                "input_tokens": 100,
                "output_tokens": 50,
            },
            raw={},
        )

    @property
    def context_window(self) -> int:
        return 8192

    @property
    def model_name(self) -> str:
        return self._model

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class TestRateLimitedProvider:
    """Test rate-limited provider wrapper."""

    @pytest.mark.asyncio
    async def test_successful_completion(self):
        """Test that successful completions work normally."""
        base_provider = MockProvider()
        limiter = RateLimiter(max_requests_per_minute=10)
        provider = RateLimitedProvider(base_provider, limiter)

        result = await provider.complete(
            system="Test system",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert result.content == "Test response"
        assert base_provider.complete_called == 1

        # Check that usage was recorded
        stats = limiter.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_tokens"] == 150  # 100 + 50

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """Test that rate limits are enforced."""
        base_provider = MockProvider()
        limiter = RateLimiter(max_requests_per_minute=2)
        provider = RateLimitedProvider(base_provider, limiter)

        # First two requests should succeed
        await provider.complete(messages=[{"role": "user", "content": "1"}])
        await provider.complete(messages=[{"role": "user", "content": "2"}])

        # Third request should fail
        with pytest.raises(RateLimitExceeded, match="Rate limit exceeded"):
            await provider.complete(messages=[{"role": "user", "content": "3"}])

        # Base provider should only be called twice
        assert base_provider.complete_called == 2

    @pytest.mark.asyncio
    async def test_cost_tracking(self):
        """Test that costs are tracked correctly."""
        base_provider = MockProvider(model="claude-sonnet-4-20250514")
        limiter = RateLimiter()
        provider = RateLimitedProvider(base_provider, limiter)

        await provider.complete(messages=[{"role": "user", "content": "Test"}])

        stats = limiter.get_stats()

        # Cost should be calculated: (100/1000)*0.003 + (50/1000)*0.015
        # = 0.0003 + 0.00075 = 0.00105
        assert stats["total_cost"] > 0
        assert abs(stats["total_cost"] - 0.00105) < 0.00001

    @pytest.mark.asyncio
    async def test_cost_limit_enforcement(self):
        """Test that cost limits are enforced."""
        base_provider = MockProvider(model="claude-sonnet-4-20250514")
        limiter = RateLimiter(max_cost_per_hour=0.002)
        provider = RateLimitedProvider(base_provider, limiter)

        # First request: ~$0.00105
        await provider.complete(messages=[{"role": "user", "content": "1"}])

        # Second request: ~$0.00105 (total ~$0.0021, exceeds $0.002)
        await provider.complete(messages=[{"role": "user", "content": "2"}])

        # Third request: should exceed $0.002 limit
        with pytest.raises(RateLimitExceeded, match="Hourly cost limit exceeded"):
            await provider.complete(messages=[{"role": "user", "content": "3"}])

    @pytest.mark.asyncio
    async def test_token_limit_enforcement(self):
        """Test that token limits are enforced."""
        base_provider = MockProvider()
        limiter = RateLimiter(max_tokens_per_request=100)
        provider = RateLimitedProvider(base_provider, limiter)

        # This should fail due to max_tokens parameter
        with pytest.raises(RateLimitExceeded, match="Token limit exceeded"):
            await provider.complete(
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=200,  # Exceeds limit
            )

    @pytest.mark.asyncio
    async def test_failed_request_counts_toward_limit(self):
        """Test that failed requests still count toward rate limit."""
        # Create a provider that always fails
        failing_provider = MockProvider()
        failing_provider.complete = AsyncMock(side_effect=Exception("API error"))

        limiter = RateLimiter(max_requests_per_minute=2)
        provider = RateLimitedProvider(failing_provider, limiter)

        # First failed request
        with pytest.raises(Exception, match="API error"):
            await provider.complete(messages=[{"role": "user", "content": "1"}])

        # Second failed request
        with pytest.raises(Exception, match="API error"):
            await provider.complete(messages=[{"role": "user", "content": "2"}])

        # Third request should hit rate limit (not the API error)
        with pytest.raises(RateLimitExceeded):
            await provider.complete(messages=[{"role": "user", "content": "3"}])

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting statistics from the wrapper."""
        base_provider = MockProvider()
        limiter = RateLimiter()
        provider = RateLimitedProvider(base_provider, limiter)

        await provider.complete(messages=[{"role": "user", "content": "Test"}])

        stats = provider.get_stats()

        assert stats["total_requests"] == 1
        assert stats["total_tokens"] == 150
        assert "requests_per_minute" in stats

    @pytest.mark.asyncio
    async def test_provider_delegation(self):
        """Test that provider methods are properly delegated."""
        base_provider = MockProvider(model="test-model-123")
        limiter = RateLimiter()
        provider = RateLimitedProvider(base_provider, limiter)

        # Test model_name delegation
        assert provider.model_name == "test-model-123"

        # Test context_window delegation
        assert provider.context_window == 8192

        # Test estimate_tokens delegation
        tokens = provider.estimate_tokens("Hello world")
        assert tokens == len("Hello world") // 4

    @pytest.mark.asyncio
    async def test_user_id_tracking(self):
        """Test that user ID is tracked."""
        base_provider = MockProvider()
        limiter = RateLimiter()
        provider = RateLimitedProvider(base_provider, limiter, user_id="user_123")

        assert provider.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_openai_cost_estimation(self):
        """Test cost estimation for OpenAI models."""
        base_provider = MockProvider(model="gpt-4o")
        limiter = RateLimiter()
        provider = RateLimitedProvider(base_provider, limiter)

        await provider.complete(messages=[{"role": "user", "content": "Test"}])

        stats = limiter.get_stats()

        # Cost should be: (100/1000)*0.005 + (50/1000)*0.015
        # = 0.0005 + 0.00075 = 0.00125
        assert abs(stats["total_cost"] - 0.00125) < 0.00001

    @pytest.mark.asyncio
    async def test_unknown_model_no_cost_tracking(self):
        """Test that unknown models don't track costs."""
        base_provider = MockProvider(model="unknown-model-xyz")
        limiter = RateLimiter()
        provider = RateLimitedProvider(base_provider, limiter)

        await provider.complete(messages=[{"role": "user", "content": "Test"}])

        stats = limiter.get_stats()

        # Cost should be 0 for unknown models
        assert stats["total_cost"] == 0.0
        # But tokens should still be tracked
        assert stats["total_tokens"] == 150


class TestRateLimitedProviderEdgeCases:
    """Test edge cases for rate-limited provider."""

    @pytest.mark.asyncio
    async def test_empty_messages(self):
        """Test with empty messages."""
        base_provider = MockProvider()
        limiter = RateLimiter()
        provider = RateLimitedProvider(base_provider, limiter)

        result = await provider.complete(messages=[])

        assert result.content == "Test response"

    @pytest.mark.asyncio
    async def test_very_long_input(self):
        """Test with very long input."""
        base_provider = MockProvider()
        limiter = RateLimiter(max_tokens_per_request=50)  # Low limit
        provider = RateLimitedProvider(base_provider, limiter)

        # Long input should trigger token limit
        long_content = "x" * 1000  # ~250 tokens estimated

        with pytest.raises(RateLimitExceeded, match="Token limit exceeded"):
            await provider.complete(
                messages=[{"role": "user", "content": long_content}],
                max_tokens=100,
            )

    @pytest.mark.asyncio
    async def test_no_usage_in_response(self):
        """Test handling when provider doesn't return usage."""
        base_provider = MockProvider()

        # Override complete to return no usage
        async def complete_no_usage(**kwargs):
            return CompletionResult(
                content="Test",
                tool_calls=[],
                done=True,
                usage={},  # Empty usage
                raw={},
            )

        base_provider.complete = complete_no_usage

        limiter = RateLimiter()
        provider = RateLimitedProvider(base_provider, limiter)

        result = await provider.complete(messages=[{"role": "user", "content": "Test"}])

        # Should handle gracefully
        assert result.content == "Test"

        stats = limiter.get_stats()
        # Cost should be 0 (no tokens in usage)
        assert stats["total_cost"] == 0.0
        assert stats["total_tokens"] == 0

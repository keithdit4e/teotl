"""Rate-limited provider wrapper.

Wraps any Provider with rate limiting and cost tracking.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from teotl.core.provider import Provider
from teotl.primitives.guardrails.rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
    estimate_cost,
)

if TYPE_CHECKING:
    from teotl.core.types import CompletionResult, ToolDefinition

logger = logging.getLogger(__name__)


class RateLimitedProvider(Provider):
    """
    Provider wrapper that adds rate limiting and cost tracking.

    Wraps any provider and enforces:
    - Requests per minute limits
    - Cost per hour/day budgets
    - Token limits per request

    Usage:
        base_provider = AnthropicProvider()
        rate_limiter = RateLimiter(
            max_requests_per_minute=60,
            max_cost_per_hour=5.0,
            max_cost_per_day=25.0
        )
        provider = RateLimitedProvider(base_provider, rate_limiter)

        agent = Agent(provider=provider)
    """

    def __init__(
        self,
        provider: Provider,
        rate_limiter: RateLimiter,
        user_id: str = "default",
    ) -> None:
        """
        Initialize rate-limited provider.

        Args:
            provider: Base provider to wrap
            rate_limiter: Rate limiter instance
            user_id: Optional user ID for multi-tenant tracking
        """
        self.provider = provider
        self.limiter = rate_limiter
        self.user_id = user_id

        logger.info(f"RateLimitedProvider initialized for {provider.model_name} (user: {user_id})")

    async def complete(
        self,
        *,
        system: str = "",
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 8192,
    ) -> CompletionResult:
        """
        Execute completion with rate limiting.

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        # Pre-flight checks
        allowed, reason = self.limiter.check_rate_limit()
        if not allowed:
            logger.warning(f"Rate limit exceeded: {reason}")
            raise RateLimitExceeded(reason)

        # Estimate input tokens (rough approximation)
        total_text = system + " ".join(
            msg.get("content", "") for msg in messages if isinstance(msg.get("content"), str)
        )
        estimated_tokens = self.provider.estimate_tokens(total_text)

        # Check token limit
        allowed, reason = self.limiter.check_token_limit(estimated_tokens + max_tokens)
        if not allowed:
            logger.warning(f"Token limit exceeded: {reason}")
            raise RateLimitExceeded(reason)

        # Execute the actual completion
        try:
            result = await self.provider.complete(
                system=system,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
            )

            # Record usage
            cost = self._estimate_cost(result.usage)
            total_tokens = result.usage.get("input_tokens", 0) + result.usage.get(
                "output_tokens", 0
            )

            self.limiter.record_request(cost=cost, tokens=total_tokens)

            logger.debug(f"Completion successful: cost=${cost:.6f}, tokens={total_tokens}")

            return result

        except Exception:
            # Still record the request attempt (failed requests count toward rate limit)
            self.limiter.record_request(cost=0.0, tokens=0)
            raise

    def _estimate_cost(self, usage: dict[str, Any]) -> float:
        """
        Estimate cost based on token usage.

        Args:
            usage: Usage dict with input_tokens and output_tokens

        Returns:
            Estimated cost in USD
        """
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Determine provider from model name
        model_name = self.provider.model_name
        if "claude" in model_name.lower():
            provider = "anthropic"
        elif "gpt" in model_name.lower():
            provider = "openai"
        else:
            provider = "unknown"

        cost = estimate_cost(
            provider=provider,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        return cost

    @property
    def context_window(self) -> int:
        """Delegate to wrapped provider."""
        return self.provider.context_window

    @property
    def model_name(self) -> str:
        """Delegate to wrapped provider."""
        return self.provider.model_name

    def estimate_tokens(self, text: str) -> int:
        """Delegate to wrapped provider."""
        return self.provider.estimate_tokens(text)

    def get_stats(self) -> dict[str, Any]:
        """
        Get current rate limiter statistics.

        Returns:
            Dict with usage metrics
        """
        return self.limiter.get_stats()

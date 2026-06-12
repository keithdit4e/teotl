"""LLM provider abstraction. Model-agnostic interface."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from teotl.core.types import CompletionResult, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class Provider(ABC):
    """
    Abstract LLM provider. All providers implement this interface.

    Swap providers without changing agent code:
        agent = Agent(provider=AnthropicProvider())
        agent = Agent(provider=OpenAIProvider())
        agent = Agent(provider=OllamaProvider(model="llama3"))
    """

    @abstractmethod
    async def complete(
        self,
        *,
        system: str = "",
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        """
        Send a completion request to the LLM.

        Args:
            system: System prompt.
            messages: Conversation history as list of role/content dicts.
            tools: Available tools the LLM can call.
            max_tokens: Maximum tokens in response.

        Returns:
            CompletionResult with content, tool calls, and usage info.
        """
        ...

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text. Override for provider-specific counting."""
        return len(text) // 4

    @property
    @abstractmethod
    def context_window(self) -> int:
        """Maximum context window size in tokens."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model name."""
        ...


class AnthropicProvider(Provider):
    """Claude via Anthropic API."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_tokens: int = 8192,
    ) -> None:
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install forge-agent[anthropic]"
            )

        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        *,
        system: str = "",
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]

        response = await self.client.messages.create(**kwargs)

        # Parse response
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        args=block.input,
                    )
                )

        return CompletionResult(
            content=content,
            tool_calls=tool_calls,
            done=len(tool_calls) == 0,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            raw=response,
        )

    @property
    def context_window(self) -> int:
        windows = {
            "claude-opus-4-20250514": 200_000,
            "claude-sonnet-4-20250514": 200_000,
            "claude-haiku-4-20250514": 200_000,
        }
        return windows.get(self.model, 200_000)

    @property
    def model_name(self) -> str:
        return self.model


class OpenAIProvider(Provider):
    """GPT via OpenAI API."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package required. Install with: pip install forge-agent[openai]"
            )

        self.model = model
        self.max_tokens = max_tokens
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        *,
        system: str = "",
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
    ) -> CompletionResult:
        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.extend(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        content = choice.message.content or ""
        tool_calls = []

        if choice.message.tool_calls:
            import json

            for tc in choice.message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        args=json.loads(tc.function.arguments),
                    )
                )

        return CompletionResult(
            content=content,
            tool_calls=tool_calls,
            done=len(tool_calls) == 0,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            raw=response,
        )

    @property
    def context_window(self) -> int:
        windows = {
            "gpt-4o": 128_000,
            "gpt-4o-mini": 128_000,
            "gpt-4-turbo": 128_000,
        }
        return windows.get(self.model, 128_000)

    @property
    def model_name(self) -> str:
        return self.model


class OllamaProvider(Provider):
    """Local models via Ollama."""

    def __init__(self, model: str = "llama3", host: str = "http://localhost:11434") -> None:
        self.model = model
        self.host = host

    async def complete(
        self,
        *,
        system: str = "",
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
    ) -> CompletionResult:
        try:
            import ollama
        except ImportError:
            raise ImportError(
                "ollama package required. Install with: pip install forge-agent[ollama]"
            )

        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.extend(messages)

        client = ollama.AsyncClient(host=self.host)
        response = await client.chat(
            model=self.model,
            messages=api_messages,
        )

        return CompletionResult(
            content=response["message"]["content"],
            tool_calls=[],
            done=True,
            usage={},
            raw=response,
        )

    @property
    def context_window(self) -> int:
        return 8_192  # Conservative default; varies by model

    @property
    def model_name(self) -> str:
        return f"ollama/{self.model}"

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
        model: str = "claude-sonnet-4-6-20260301",
        api_key: str | None = None,
        max_tokens: int = 8192,
    ) -> None:
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install teotl[anthropic]"
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
            # Claude 4.x series (2026) - 1M context
            "claude-opus-4-8-20260528": 1_000_000,
            "claude-opus-4-7-20260416": 1_000_000,
            "claude-sonnet-4-6-20260301": 1_000_000,
            "claude-haiku-4-5-20260115": 1_000_000,
            # Legacy models
            "claude-opus-4-20250514": 200_000,
            "claude-sonnet-4-20250514": 200_000,
        }
        return windows.get(self.model, 1_000_000)

    @property
    def model_name(self) -> str:
        return self.model


class OpenAIProvider(Provider):
    """GPT via OpenAI API."""

    def __init__(
        self,
        model: str = "gpt-5.4",
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 8192,
    ) -> None:
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package required. Install with: pip install teotl[openai]"
            )

        self.model = model
        self.max_tokens = max_tokens
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

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
            # GPT-5.x series - 1M context
            "gpt-5.5": 1_000_000,
            "gpt-5.5-pro": 1_000_000,
            "gpt-5.4": 1_000_000,
            # GPT-4.x series
            "gpt-4.1": 1_000_000,
            "gpt-4.1-nano": 128_000,
            "gpt-4o": 128_000,
            "gpt-4o-mini": 128_000,
            # O-series reasoning models
            "o3": 200_000,
            "o3-pro": 200_000,
            "o4-mini": 200_000,
        }
        return windows.get(self.model, 1_000_000)

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
                "ollama package required. Install with: pip install teotl[ollama]"
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


class GeminiProvider(Provider):
    """Google Gemini via Google Generative AI API."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        max_tokens: int = 8192,
    ) -> None:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai package required. Install with: pip install teotl[google]"
            )

        self.model = model
        self.max_tokens = max_tokens
        self._genai = genai

        # Configure the API key
        if api_key:
            genai.configure(api_key=api_key)

        # Create the model client
        self.client = genai.GenerativeModel(model)

    async def complete(
        self,
        *,
        system: str = "",
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        import asyncio

        # Convert messages to Gemini format
        # Gemini uses "user" and "model" roles (not "assistant")
        gemini_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                role = "model"

            content = msg.get("content", "")

            # Handle tool results - Gemini expects function responses
            if role == "user" and "tool_result" in msg:
                # This is a tool result message
                from google.generativeai.types import content_types

                gemini_messages.append(
                    content_types.ContentDict(
                        role="user",
                        parts=[
                            {
                                "function_response": {
                                    "name": msg.get("tool_name", "unknown"),
                                    "response": {"result": msg["tool_result"]},
                                }
                            }
                        ],
                    )
                )
            elif content:
                gemini_messages.append({"role": role, "parts": [content]})

        # Build generation config
        generation_config = {
            "max_output_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }

        # Build tool config if tools provided
        gemini_tools = None
        if tools:
            gemini_tools = self._convert_tools(tools)

        # Create model with system instruction if provided
        model = self.client
        if system:
            model = self._genai.GenerativeModel(
                self.model,
                system_instruction=system,
            )

        # Run sync API in thread pool (Gemini SDK is synchronous)
        def _sync_generate():
            kwargs: dict[str, Any] = {
                "contents": gemini_messages,
                "generation_config": generation_config,
            }
            if gemini_tools:
                kwargs["tools"] = gemini_tools

            return model.generate_content(**kwargs)

        response = await asyncio.to_thread(_sync_generate)

        # Parse response
        content = ""
        tool_calls = []

        # Handle response parts
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    content += part.text
                elif hasattr(part, "function_call"):
                    fc = part.function_call
                    tool_calls.append(
                        ToolCall(
                            id=f"call_{fc.name}_{len(tool_calls)}",
                            name=fc.name,
                            args=dict(fc.args) if fc.args else {},
                        )
                    )

        # Extract usage metadata
        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count or 0,
                "output_tokens": response.usage_metadata.candidates_token_count or 0,
            }

        return CompletionResult(
            content=content,
            tool_calls=tool_calls,
            done=len(tool_calls) == 0,
            usage=usage,
            raw=response,
        )

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[Any]:
        """Convert ToolDefinition to Gemini function declarations."""
        from google.generativeai.types import content_types

        declarations = []
        for tool in tools:
            # Convert JSON schema to Gemini format
            declarations.append(
                content_types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.parameters,
                )
            )

        return [content_types.Tool(function_declarations=declarations)]

    @property
    def context_window(self) -> int:
        windows = {
            # Gemini 3.x series
            "gemini-3.5-flash": 1_000_000,
            "gemini-3.1-flash-lite": 1_000_000,
            "gemini-3.1-pro-preview": 2_000_000,
            "gemini-3-flash-preview": 1_000_000,
            # Gemini 2.5 series
            "gemini-2.5-pro": 2_000_000,
            "gemini-2.5-flash": 1_000_000,
            "gemini-2.5-flash-lite": 1_000_000,
        }
        return windows.get(self.model, 1_000_000)

    @property
    def model_name(self) -> str:
        return self.model

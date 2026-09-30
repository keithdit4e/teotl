"""LLM provider abstraction. Model-agnostic interface."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from teotl.core.models import (
    CLAUDE_MODELS,
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_MODEL,
    DEFAULT_OPENAI_MODEL,
    GEMINI_MODELS,
    OPENAI_CHAT_TOOLS_UNSUPPORTED,
    OPENAI_MODELS,
)
from teotl.core.types import CompletionResult, ToolCall, ToolDefinition

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message conversion
#
# The agent keeps conversation history in Anthropic's format: content is a
# string, or a list of blocks ("text", "tool_use", "tool_result", and
# provider-native blocks such as "thinking"). Other providers convert it.
# ---------------------------------------------------------------------------


def _blocks(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}] if content else []
    return [b for b in content or [] if isinstance(b, dict)]


def _text(blocks: list[dict[str, Any]]) -> str:
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def _result_text(block: dict[str, Any]) -> str:
    content = block.get("content", "")
    if isinstance(content, list):
        content = _text(_blocks(content))
    return str(content)


def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anthropic-format history -> OpenAI chat messages (tool_calls / role "tool")."""
    out: list[dict[str, Any]] = []
    for msg in messages:
        blocks = _blocks(msg.get("content"))
        if msg["role"] == "assistant":
            calls = [b for b in blocks if b.get("type") == "tool_use"]
            entry: dict[str, Any] = {"role": "assistant", "content": _text(blocks) or None}
            if calls:
                entry["tool_calls"] = [
                    {
                        "id": b["id"],
                        "type": "function",
                        "function": {
                            "name": b["name"],
                            "arguments": json.dumps(b.get("input", {})),
                        },
                    }
                    for b in calls
                ]
            out.append(entry)
        else:
            for b in blocks:
                if b.get("type") == "tool_result":
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": b["tool_use_id"],
                            "content": _result_text(b),
                        }
                    )
            text = _text(blocks)
            if text:
                out.append({"role": "user", "content": text})
    return out


def _to_ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anthropic-format history -> Ollama chat messages."""
    out: list[dict[str, Any]] = []
    names: dict[str, str] = {}
    for msg in messages:
        blocks = _blocks(msg.get("content"))
        if msg["role"] == "assistant":
            calls = [b for b in blocks if b.get("type") == "tool_use"]
            entry: dict[str, Any] = {"role": "assistant", "content": _text(blocks)}
            if calls:
                entry["tool_calls"] = [
                    {"function": {"name": b["name"], "arguments": b.get("input", {})}}
                    for b in calls
                ]
                names.update({b["id"]: b["name"] for b in calls})
            out.append(entry)
        else:
            for b in blocks:
                if b.get("type") == "tool_result":
                    out.append(
                        {
                            "role": "tool",
                            "content": _result_text(b),
                            "tool_name": names.get(b["tool_use_id"], ""),
                        }
                    )
            text = _text(blocks)
            if text:
                out.append({"role": "user", "content": text})
    return out


def _to_gemini_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anthropic-format history -> Gemini contents (function_call / function_response)."""
    out: list[dict[str, Any]] = []
    names: dict[str, str] = {}
    for msg in messages:
        blocks = _blocks(msg.get("content"))
        parts: list[Any] = []
        if msg["role"] == "assistant":
            text = _text(blocks)
            if text:
                parts.append({"text": text})
            for b in blocks:
                if b.get("type") == "tool_use":
                    names[b["id"]] = b["name"]
                    parts.append({"function_call": {"name": b["name"], "args": b.get("input", {})}})
            if parts:
                out.append({"role": "model", "parts": parts})
        else:
            for b in blocks:
                if b.get("type") == "tool_result":
                    parts.append(
                        {
                            "function_response": {
                                "name": names.get(b["tool_use_id"], "unknown"),
                                "response": {"result": _result_text(b)},
                            }
                        }
                    )
            text = _text(blocks)
            if text:
                parts.append({"text": text})
            if parts:
                out.append({"role": "user", "parts": parts})
    return out


def _openai_style_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
        }
        for t in tools
    ]


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
        model: str = DEFAULT_MODEL,
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
            # Echo blocks back unchanged: thinking blocks must not be dropped or edited
            assistant_content=[block.to_dict() for block in response.content],
        )

    @property
    def context_window(self) -> int:
        info = CLAUDE_MODELS.get(self.model)
        return info.context_window if info else DEFAULT_CONTEXT_WINDOW

    @property
    def model_name(self) -> str:
        return self.model


class OpenAIProvider(Provider):
    """GPT via OpenAI API."""

    def __init__(
        self,
        model: str = DEFAULT_OPENAI_MODEL,
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
        self._warned_tools = False

    async def complete(
        self,
        *,
        system: str = "",
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.extend(_to_openai_messages(messages))

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            # Current OpenAI models reject `max_tokens`
            "max_completion_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }

        if tools:
            kwargs["tools"] = _openai_style_tools(tools)
            if self.model.startswith(OPENAI_CHAT_TOOLS_UNSUPPORTED) and not self._warned_tools:
                logger.warning(
                    f"{self.model} doesn't fully support tool calling in the Chat Completions "
                    "API that OpenAIProvider uses (OpenAI requires the Responses API). "
                    "Use gpt-5.6-terra, gpt-5.6-sol or gpt-5.6-luna for agents with tools."
                )
                self._warned_tools = True

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        content = choice.message.content or ""
        tool_calls = []

        if choice.message.tool_calls:
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
        info = OPENAI_MODELS.get(self.model)
        return info.context_window if info else DEFAULT_CONTEXT_WINDOW

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
        max_tokens: int | None = None,
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
        api_messages.extend(_to_ollama_messages(messages))

        kwargs: dict[str, Any] = {"model": self.model, "messages": api_messages}
        if tools:
            kwargs["tools"] = _openai_style_tools(tools)
        if max_tokens is not None:
            kwargs["options"] = {"num_predict": max_tokens}

        client = ollama.AsyncClient(host=self.host)
        response = await client.chat(**kwargs)

        message = response["message"]
        tool_calls = [
            ToolCall(
                id=f"call_{i}_{tc['function']['name']}",
                name=tc["function"]["name"],
                args=dict(tc["function"].get("arguments") or {}),
            )
            for i, tc in enumerate(message.get("tool_calls") or [])
        ]

        return CompletionResult(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            done=len(tool_calls) == 0,
            usage={
                "input_tokens": response.get("prompt_eval_count") or 0,
                "output_tokens": response.get("eval_count") or 0,
            },
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
        model: str = DEFAULT_GEMINI_MODEL,
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

        # Convert Anthropic-format history (incl. tool calls/results) to Gemini contents
        gemini_messages = _to_gemini_contents(messages)

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
                elif getattr(part, "function_call", None) and part.function_call.name:
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
        info = GEMINI_MODELS.get(self.model)
        return info.context_window if info else DEFAULT_CONTEXT_WINDOW

    @property
    def model_name(self) -> str:
        return self.model

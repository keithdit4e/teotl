"""LLM provider abstraction. Model-agnostic interface."""

from __future__ import annotations

import base64
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
    """Anthropic-format history -> Gemini contents (function_call / function_response).

    Blocks produced by GeminiProvider carry `gemini_id` (the function call's id) and
    `gemini_thought_signature` (base64). Both are sent back unchanged: newer Gemini
    models reject function-calling turns whose thought signatures were dropped.
    """
    out: list[dict[str, Any]] = []
    names: dict[str, str] = {}
    gemini_ids: dict[str, str] = {}
    for msg in messages:
        blocks = _blocks(msg.get("content"))
        parts: list[dict[str, Any]] = []
        if msg["role"] == "assistant":
            for b in blocks:
                part: dict[str, Any]
                if b.get("type") == "text":
                    if not b.get("text") and not b.get("gemini_thought_signature"):
                        continue
                    part = {"text": b.get("text", "")}
                elif b.get("type") == "tool_use":
                    names[b["id"]] = b["name"]
                    call: dict[str, Any] = {"name": b["name"], "args": b.get("input", {})}
                    if b.get("gemini_id"):
                        call["id"] = b["gemini_id"]
                        gemini_ids[b["id"]] = b["gemini_id"]
                    part = {"function_call": call}
                else:
                    continue  # other providers' native blocks (e.g. Claude thinking)
                if b.get("gemini_thought_signature"):
                    part["thought_signature"] = base64.b64decode(b["gemini_thought_signature"])
                parts.append(part)
            if parts:
                out.append({"role": "model", "parts": parts})
        else:
            for b in blocks:
                if b.get("type") == "tool_result":
                    response: dict[str, Any] = {
                        "name": names.get(b["tool_use_id"], "unknown"),
                        "response": {"result": _result_text(b)},
                    }
                    if b["tool_use_id"] in gemini_ids:
                        response["id"] = gemini_ids[b["tool_use_id"]]
                    parts.append({"function_response": response})
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
    """Google Gemini via the Google Gen AI SDK (`google-genai`)."""

    def __init__(
        self,
        model: str = DEFAULT_GEMINI_MODEL,
        api_key: str | None = None,
        max_tokens: int = 8192,
    ) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-genai package required. Install with: pip install teotl[google]"
            )

        self.model = model
        self.max_tokens = max_tokens
        self._types = types
        # Without api_key, the SDK reads GOOGLE_API_KEY or GEMINI_API_KEY
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    async def complete(
        self,
        *,
        system: str = "",
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        types = self._types
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            max_output_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            tools=self._convert_tools(tools) if tools else None,
            # Teotl runs tools itself (through guardrails); never let the SDK call them
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        contents = [types.Content.model_validate(c) for c in _to_gemini_contents(messages)]

        response = await self.client.aio.models.generate_content(
            model=self.model, contents=contents, config=config
        )

        content = ""
        tool_calls: list[ToolCall] = []
        assistant_content: list[dict[str, Any]] = []
        candidate = response.candidates[0] if response.candidates else None
        for part in (candidate.content.parts if candidate and candidate.content else None) or []:
            signature = (
                base64.b64encode(part.thought_signature).decode()
                if part.thought_signature
                else None
            )
            if part.function_call and part.function_call.name:
                fc = part.function_call
                call_id = fc.id or f"call_{fc.name}_{len(tool_calls)}"
                args = dict(fc.args or {})
                tool_calls.append(ToolCall(id=call_id, name=fc.name, args=args))
                block: dict[str, Any] = {
                    "type": "tool_use",
                    "id": call_id,
                    "name": fc.name,
                    "input": args,
                }
                if fc.id:
                    block["gemini_id"] = fc.id
            elif part.text is not None and not part.thought:
                content += part.text
                block = {"type": "text", "text": part.text}
            elif signature:
                block = {"type": "text", "text": ""}  # signature-only part
            else:
                continue
            if signature:
                block["gemini_thought_signature"] = signature
            assistant_content.append(block)

        usage: dict[str, int] = {}
        meta = response.usage_metadata
        if meta:
            usage = {
                "input_tokens": meta.prompt_token_count or 0,
                # Thinking tokens are billed as output
                "output_tokens": (meta.candidates_token_count or 0)
                + (meta.thoughts_token_count or 0),
            }

        return CompletionResult(
            content=content,
            tool_calls=tool_calls,
            done=len(tool_calls) == 0,
            usage=usage,
            raw=response,
            # Sent back verbatim so call ids and thought signatures survive tool loops
            assistant_content=assistant_content,
        )

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[Any]:
        """ToolDefinitions -> one Gemini Tool, passing each JSON Schema through as-is."""
        types = self._types
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=t.name,
                        description=t.description,
                        parameters_json_schema=t.parameters,
                    )
                    for t in tools
                ]
            )
        ]

    @property
    def context_window(self) -> int:
        info = GEMINI_MODELS.get(self.model)
        return info.context_window if info else DEFAULT_CONTEXT_WINDOW

    @property
    def model_name(self) -> str:
        return self.model

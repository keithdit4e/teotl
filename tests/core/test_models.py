"""Tests for the Claude model catalog and thinking-block round-tripping."""

from types import SimpleNamespace

import pytest

from teotl.core.agent import Agent
from teotl.core.models import (
    CLAUDE_MODELS,
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_MODEL,
    DEFAULT_PLANNER_MODEL,
    DEFAULT_WORKER_MODEL,
)
from teotl.core.types import CompletionResult, ToolCall
from teotl.primitives.guardrails.rate_limiter import estimate_cost

anthropic = pytest.importorskip("anthropic")
from anthropic.types import TextBlock, ThinkingBlock, ToolUseBlock  # noqa: E402

from teotl.core.provider import AnthropicProvider  # noqa: E402


class TestCatalog:
    def test_defaults_are_in_catalog(self):
        for model in (DEFAULT_MODEL, DEFAULT_PLANNER_MODEL, DEFAULT_WORKER_MODEL):
            assert model in CLAUDE_MODELS

    def test_every_catalog_model_has_pricing(self):
        for model in CLAUDE_MODELS:
            assert estimate_cost("anthropic", model, 1000, 1000) > 0

    def test_context_window_from_catalog(self):
        assert AnthropicProvider(model="claude-sonnet-5-5", api_key="x").context_window == 1_000_000
        assert AnthropicProvider(model="claude-haiku-4-5", api_key="x").context_window == 200_000

    def test_unknown_model_uses_conservative_window(self):
        provider = AnthropicProvider(model="claude-unknown-9", api_key="x")
        assert provider.context_window == DEFAULT_CONTEXT_WINDOW

    def test_provider_default_model(self):
        assert AnthropicProvider(api_key="x").model == DEFAULT_MODEL


class TestThinkingBlocks:
    @pytest.mark.asyncio
    async def test_provider_returns_native_blocks(self):
        """Thinking blocks are passed through verbatim, including empty text and signature."""
        provider = AnthropicProvider(model="claude-sonnet-5-5", api_key="x")
        response = SimpleNamespace(
            content=[
                ThinkingBlock(type="thinking", thinking="", signature="sig-123"),
                TextBlock(type="text", text="Checking files."),
                ToolUseBlock(type="tool_use", id="tu_1", name="bash", input={"command": "ls"}),
            ],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )

        async def fake_create(**kwargs):
            return response

        provider.client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
        result = await provider.complete(messages=[{"role": "user", "content": "hi"}])

        assert result.assistant_content == [
            {"type": "thinking", "thinking": "", "signature": "sig-123"},
            {"type": "text", "text": "Checking files."},
            {"type": "tool_use", "id": "tu_1", "name": "bash", "input": {"command": "ls"}},
        ]
        assert result.tool_calls[0].id == "tu_1"

    @pytest.mark.asyncio
    async def test_agent_echoes_native_blocks_in_tool_loop(self):
        """The assistant turn sent back to the model keeps the thinking block unchanged."""
        blocks = [
            {"type": "thinking", "thinking": "", "signature": "sig-123"},
            {"type": "tool_use", "id": "tu_1", "name": "bash", "input": {"command": "ls -la"}},
        ]

        class Provider:
            model = "claude-sonnet-5-5"
            context_window = 1_000_000
            model_name = "claude-sonnet-5-5"

            def __init__(self):
                self.calls = []

            def estimate_tokens(self, text):
                return len(text) // 4

            async def complete(self, **kwargs):
                self.calls.append(kwargs)
                if len(self.calls) == 1:
                    return CompletionResult(
                        tool_calls=[ToolCall(id="tu_1", name="bash", args={"command": "ls -la"})],
                        done=False,
                        assistant_content=blocks,
                    )
                return CompletionResult(content="done", done=True)

        class UI:
            async def confirm(self, message, *, title=""):
                return True

            async def display(self, message):
                pass

            async def input(self, prompt=""):
                return ""

            async def error(self, message):
                pass

        provider = Provider()
        agent = Agent(provider=provider, policy="standard")

        async def bash_handler(command: str) -> str:
            return "file.txt"

        agent.register_tool(
            name="bash",
            description="Run bash command",
            handler=bash_handler,
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        )

        await agent.run("List files", ui=UI())

        second_request = provider.calls[1]["messages"]
        assistant_turn = next(m for m in second_request if m["role"] == "assistant")
        assert assistant_turn["content"] == blocks

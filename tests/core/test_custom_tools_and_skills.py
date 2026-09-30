"""End-to-end tests for user-defined tools and skills, and cross-provider tool history."""

import pytest

from teotl.core.agent import Agent
from teotl.core.provider import (
    _to_gemini_contents,
    _to_ollama_messages,
    _to_openai_messages,
)
from teotl.core.types import CompletionResult, ToolCall

# A conversation in the agent's (Anthropic) format after one tool call
HISTORY = [
    {"role": "user", "content": "What's the weather in Paris?"},
    {
        "role": "assistant",
        "content": [
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "text", "text": "Checking."},
            {"type": "tool_use", "id": "call_1", "name": "get_weather", "input": {"city": "Paris"}},
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call_1",
                "content": "18C, sunny",
                "is_error": False,
            }
        ],
    },
]


class ScriptedProvider:
    """Returns queued CompletionResults and records every request."""

    model = "scripted"
    model_name = "scripted"
    context_window = 200_000

    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    async def complete(self, **kwargs):
        self.calls.append(kwargs)
        return self.results.pop(0) if self.results else CompletionResult(content="done")


class RecordingUI:
    def __init__(self, approve=True):
        self.approve = approve
        self.confirmations = []

    async def confirm(self, message, *, title=""):
        self.confirmations.append(message)
        return self.approve

    async def display(self, message):
        pass

    async def input(self, prompt=""):
        return ""

    async def error(self, message):
        pass


def call(tool, /, **args):
    return CompletionResult(
        tool_calls=[ToolCall(id=f"id_{tool}", name=tool, args=args)], done=False
    )


def tool_results(provider, turn):
    """tool_result blocks sent to the model on a given request."""
    last = provider.calls[turn]["messages"][-1]["content"]
    return [b for b in last if isinstance(b, dict) and b.get("type") == "tool_result"]


# ---------------------------------------------------------------------------
# Custom tools
# ---------------------------------------------------------------------------


class TestCustomTools:
    @pytest.mark.asyncio
    async def test_sync_handler_called_with_args(self):
        provider = ScriptedProvider(call("add", a=2, b=3))
        agent = Agent(provider=provider, skills=[])
        agent.register_tool(
            "add",
            "Add two numbers",
            lambda a, b: a + b,
            {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
        )

        response = await agent.run("add 2 and 3")

        assert response.text == "done"
        assert [t.name for t in provider.calls[0]["tools"]].count("add") == 1
        assert tool_results(provider, 1)[0]["content"] == "5"

    @pytest.mark.asyncio
    async def test_async_handler(self):
        async def fetch(url: str) -> str:
            return f"fetched {url}"

        provider = ScriptedProvider(call("fetch", url="https://example.com"))
        agent = Agent(provider=provider, skills=[])
        agent.register_tool("fetch", "Fetch a URL", fetch)
        await agent.run("fetch it")
        assert tool_results(provider, 1)[0]["content"] == "fetched https://example.com"

    @pytest.mark.asyncio
    async def test_handler_error_is_reported_not_raised(self):
        def boom():
            raise RuntimeError("service down")

        provider = ScriptedProvider(call("boom"))
        agent = Agent(provider=provider, skills=[])
        agent.register_tool("boom", "Fails", boom)
        await agent.run("try it")
        result = tool_results(provider, 1)[0]
        assert result["is_error"] is True
        assert "service down" in result["content"]

    def test_reregistering_replaces_tool(self):
        agent = Agent(provider=ScriptedProvider())  # bash is registered automatically
        agent.register_tool("bash", "My own bash", lambda command: "ok")
        assert [t.name for t in agent._tools].count("bash") == 1
        assert agent._tools[-1].description == "My own bash"

    @pytest.mark.parametrize("name", ["has space", "", "x" * 65, "dots.not.allowed"])
    def test_invalid_tool_name_rejected(self, name):
        with pytest.raises(ValueError, match="Invalid tool name"):
            Agent(provider=ScriptedProvider(), skills=[]).register_tool(name, "d", lambda: "")

    def test_invalid_risk_rejected(self):
        with pytest.raises(ValueError, match="Invalid risk"):
            Agent(provider=ScriptedProvider(), skills=[]).register_tool(
                "t", "d", lambda: "", risk="spicy"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "risk,confirmations,ran",
        [("low", 0, True), ("medium", 1, True), ("high", 1, True), ("critical", 0, False)],
    )
    async def test_risk_levels_under_standard_policy(self, risk, confirmations, ran):
        calls = []
        provider = ScriptedProvider(call("send_email", to="a@b.c"))
        agent = Agent(provider=provider, policy="standard", skills=[])
        agent.register_tool(
            "send_email", "Send email", lambda to: calls.append(to) or "sent", risk=risk
        )
        ui = RecordingUI(approve=True)

        await agent.run("email them", ui=ui)

        assert len(ui.confirmations) == confirmations
        assert bool(calls) == ran

    @pytest.mark.asyncio
    async def test_denied_confirmation_skips_tool(self):
        calls = []
        provider = ScriptedProvider(call("delete_record", record_id=7))
        agent = Agent(provider=provider, policy="standard", skills=[])
        agent.register_tool(
            "delete_record", "Delete", lambda record_id: calls.append(record_id), risk="medium"
        )
        await agent.run("delete it", ui=RecordingUI(approve=False))
        assert calls == []


# ---------------------------------------------------------------------------
# Custom skills
# ---------------------------------------------------------------------------


@pytest.fixture
def user_skill(tmp_path, monkeypatch):
    skill = tmp_path / "skills" / "invoice-report"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: invoice-report\n"
        "description: Summarize unpaid invoices\n"
        "triggers:\n  - unpaid invoices\n"
        "---\n"
        "Run `python scripts/report.py` from the skill directory and summarize the output.\n"
    )
    (skill / "scripts" / "report.py").write_text("print('3 unpaid invoices')\n")
    monkeypatch.setenv("TEOTL_SKILLS_PATH", str(tmp_path / "skills"))
    return skill


class TestCustomSkills:
    def test_custom_skill_discovered_and_described(self, user_skill):
        agent = Agent(provider=ScriptedProvider(), skills=["invoice-report"])
        assert "invoice-report" in agent.skills.skills
        assert "load_skill" in [t.name for t in agent._tools]

    @pytest.mark.asyncio
    async def test_trigger_in_user_message_loads_instructions_up_front(self, user_skill):
        provider = ScriptedProvider()
        agent = Agent(provider=provider, skills=["invoice-report"])

        await agent.run("Give me a summary of unpaid invoices")

        system = provider.calls[0]["system"]
        assert "Run `python scripts/report.py`" in system
        assert f"Skill directory: {user_skill}" in system

    @pytest.mark.asyncio
    async def test_model_can_load_skill_mid_run(self, user_skill):
        provider = ScriptedProvider(call("load_skill", name="invoice-report"))
        agent = Agent(provider=provider, skills=["invoice-report"])

        await agent.run("How much money are customers owing us?")  # no trigger words

        assert "scripts/report.py" not in provider.calls[0]["system"]
        loaded = tool_results(provider, 1)[0]["content"]
        assert "Run `python scripts/report.py`" in loaded
        assert str(user_skill) in loaded
        assert agent.skills.is_active("invoice-report")

    @pytest.mark.asyncio
    async def test_unknown_skill_lists_available(self, user_skill):
        provider = ScriptedProvider(call("load_skill", name="nope"))
        agent = Agent(provider=provider, skills=["invoice-report"])
        await agent.run("hi")
        assert "Available skills: invoice-report" in tool_results(provider, 1)[0]["content"]

    @pytest.mark.asyncio
    async def test_skill_script_runs_via_bash(self, user_skill):
        provider = ScriptedProvider(
            call("bash", command=f"cd {user_skill} && python3 scripts/report.py")
        )
        agent = Agent(provider=provider, skills=["invoice-report"], policy="minimal")
        await agent.run("unpaid invoices please", ui=RecordingUI(approve=True))
        assert "3 unpaid invoices" in tool_results(provider, 1)[0]["content"]


# ---------------------------------------------------------------------------
# Provider history conversion
# ---------------------------------------------------------------------------


class TestProviderConversion:
    def test_openai_messages(self):
        msgs = _to_openai_messages(HISTORY)
        assert msgs[0] == {"role": "user", "content": "What's the weather in Paris?"}
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == "Checking."
        tc = msgs[1]["tool_calls"][0]
        assert tc["id"] == "call_1" and tc["function"]["name"] == "get_weather"
        assert tc["function"]["arguments"] == '{"city": "Paris"}'
        assert msgs[2] == {"role": "tool", "tool_call_id": "call_1", "content": "18C, sunny"}

    def test_openai_messages_match_sdk_types(self):
        openai = pytest.importorskip("openai")  # noqa: F841
        from openai.types.chat import ChatCompletionMessageParam
        from pydantic import TypeAdapter

        adapter = TypeAdapter(list[ChatCompletionMessageParam])
        adapter.validate_python(_to_openai_messages(HISTORY))

    def test_ollama_messages(self):
        msgs = _to_ollama_messages(HISTORY)
        assert msgs[1]["tool_calls"] == [
            {"function": {"name": "get_weather", "arguments": {"city": "Paris"}}}
        ]
        assert msgs[2] == {"role": "tool", "content": "18C, sunny", "tool_name": "get_weather"}

    def test_gemini_contents(self):
        contents = _to_gemini_contents(HISTORY)
        assert [c["role"] for c in contents] == ["user", "model", "user"]
        assert contents[1]["parts"][1] == {
            "function_call": {"name": "get_weather", "args": {"city": "Paris"}}
        }
        assert contents[2]["parts"][0]["function_response"]["name"] == "get_weather"

    def test_gemini_contents_match_sdk_types(self):
        pytest.importorskip("google.generativeai")
        from google.generativeai.types import content_types

        content_types.to_contents(_to_gemini_contents(HISTORY))


@pytest.mark.asyncio
async def test_openai_provider_request_and_tool_parsing(monkeypatch):
    pytest.importorskip("openai")
    from openai.types.chat import ChatCompletion

    from teotl.core.provider import OpenAIProvider
    from teotl.core.types import ToolDefinition

    provider = OpenAIProvider(api_key="x", max_tokens=1234)
    sent = {}

    async def create(**kwargs):
        sent.update(kwargs)
        return ChatCompletion.model_validate(
            {
                "id": "c",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-5.4",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_9",
                                    "type": "function",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city": "Rome"}',
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
        )

    monkeypatch.setattr(provider.client.chat.completions, "create", create)
    result = await provider.complete(
        system="sys",
        messages=HISTORY,
        tools=[ToolDefinition(name="get_weather", description="w", parameters={"type": "object"})],
    )

    assert sent["max_completion_tokens"] == 1234
    assert "max_tokens" not in sent
    assert sent["messages"][0] == {"role": "system", "content": "sys"}
    assert sent["messages"][-1]["role"] == "tool"
    assert result.tool_calls[0].name == "get_weather"
    assert result.tool_calls[0].args == {"city": "Rome"}


@pytest.mark.asyncio
async def test_ollama_provider_sends_tools_and_parses_calls(monkeypatch):
    import sys
    import types

    from teotl.core.provider import OllamaProvider
    from teotl.core.types import ToolDefinition

    sent = {}

    class FakeClient:
        def __init__(self, host):
            pass

        async def chat(self, **kwargs):
            sent.update(kwargs)
            return {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "get_weather", "arguments": {"city": "Oslo"}}}
                    ],
                },
                "prompt_eval_count": 3,
                "eval_count": 2,
            }

    monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(AsyncClient=FakeClient))
    result = await OllamaProvider().complete(
        messages=HISTORY,
        tools=[ToolDefinition(name="get_weather", description="w", parameters={"type": "object"})],
    )

    assert sent["tools"][0]["function"]["name"] == "get_weather"
    assert sent["messages"][-1]["role"] == "tool"
    assert result.tool_calls[0].args == {"city": "Oslo"}
    assert result.done is False

"""Tool handlers that fail without raising, and output filters that fail."""

import pytest

from teotl.core.agent import Agent
from teotl.core.types import CompletionResult, RiskLevel, ToolCall, ToolErrorOutput


class Scripted:
    model = model_name = "scripted"
    context_window = 200_000

    def __init__(self, *calls):
        self.results = [
            CompletionResult(tool_calls=[ToolCall(id=f"c{i}", name=n, args=a)], done=False)
            for i, (n, a) in enumerate(calls)
        ]

    async def complete(self, **kwargs):
        return self.results.pop(0) if self.results else CompletionResult(content="done")


def make_agent(*calls):
    agent = Agent(provider=Scripted(*calls), skills=[], rules={"tools": {"lookup": "allow"}})
    agent.register_tool(
        "lookup",
        "Look something up",
        lambda key: ToolErrorOutput("Error: not found") if key == "missing" else f"value of {key}",
        {"type": "object", "properties": {"key": {"type": "string"}}},
        risk=RiskLevel.LOW,
    )
    return agent


@pytest.mark.asyncio
async def test_tool_error_output_is_recorded_as_an_error():
    async with make_agent(("lookup", {"key": "missing"}), ("lookup", {"key": "a"})) as agent:
        response = await agent.run("go")
    missing, found = response.tool_results
    assert missing.is_error is True and missing.error == "Error: not found"
    assert found.is_error is False and found.output == "value of a"


@pytest.mark.asyncio
async def test_crashing_output_filter_withholds_output():
    async with make_agent(("lookup", {"key": "secret"})) as agent:

        async def redactor(event, **kwargs):
            raise RuntimeError("redaction service down")

        agent.events.on("tool_result", redactor)
        response = await agent.run("go")
    result = response.tool_results[0]
    assert result.is_error is True and result.error.startswith("Output withheld:")
    assert "value of secret" not in (result.output or "") + (result.error or "")


@pytest.mark.asyncio
async def test_crashing_guardrail_blocks_the_call():
    calls = []
    async with make_agent(("lookup", {"key": "a"})) as agent:
        agent._tool_handlers["lookup"] = lambda key: calls.append(key) or "ran"

        async def broken_guardrail(event, **kwargs):
            raise RuntimeError("policy engine unavailable")

        agent.events.on("tool_call", broken_guardrail, priority=-200)
        response = await agent.run("go")
    assert calls == []
    assert response.tool_results[0].is_error is True
    assert "blocked to be safe" in response.tool_results[0].error

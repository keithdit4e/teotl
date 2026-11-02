"""GeminiProvider on google-genai: requests, parsing, and thought-signature round trips."""

from types import SimpleNamespace

import pytest

genai_types = pytest.importorskip("google.genai.types")

from teotl.core.agent import Agent  # noqa: E402
from teotl.core.provider import GeminiProvider  # noqa: E402
from teotl.core.types import ToolDefinition  # noqa: E402

SIGNATURE = b"\x01\x02opaque-signature"
SCHEMA = {
    "type": "object",
    "properties": {"city": {"type": "string", "description": "City name"}},
    "required": ["city"],
}


def response(*parts, prompt=100, output=20, thoughts=30):
    return genai_types.GenerateContentResponse.model_validate(
        {
            "candidates": [{"content": {"role": "model", "parts": list(parts)}}],
            "usage_metadata": {
                "prompt_token_count": prompt,
                "candidates_token_count": output,
                "thoughts_token_count": thoughts,
            },
        }
    )


def function_call_part(name="get_weather", args=None, call_id="fc-1", signature=SIGNATURE):
    part = {"function_call": {"name": name, "args": args or {"city": "Paris"}, "id": call_id}}
    if signature:
        part["thought_signature"] = signature
    return part


class FakeModels:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    async def generate_content(self, *, model, contents, config):
        self.requests.append({"model": model, "contents": contents, "config": config})
        return self.responses.pop(0)


def provider_with(*responses):
    provider = GeminiProvider(api_key="test-key")
    models = FakeModels(*responses)
    provider.client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return provider, models


@pytest.mark.asyncio
async def test_request_config_and_function_call_parsing():
    provider, models = provider_with(response(function_call_part()))
    tools = [ToolDefinition(name="get_weather", description="Weather", parameters=SCHEMA)]

    result = await provider.complete(
        system="Be brief.", messages=[{"role": "user", "content": "Weather?"}], tools=tools
    )

    config = models.requests[0]["config"]
    assert config.system_instruction == "Be brief."
    assert config.automatic_function_calling.disable is True
    declaration = config.tools[0].function_declarations[0]
    assert declaration.name == "get_weather"
    assert declaration.parameters_json_schema == SCHEMA  # passed through unchanged

    assert result.done is False
    assert result.tool_calls[0].id == "fc-1"
    assert result.tool_calls[0].args == {"city": "Paris"}
    block = result.assistant_content[0]
    assert block["gemini_id"] == "fc-1"
    assert block["gemini_thought_signature"]  # kept for the next request


@pytest.mark.asyncio
async def test_usage_counts_thinking_as_output():
    provider, _ = provider_with(response({"text": "hi"}, prompt=100, output=20, thoughts=30))
    result = await provider.complete(messages=[{"role": "user", "content": "hi"}])
    assert result.usage == {"input_tokens": 100, "output_tokens": 50}


@pytest.mark.asyncio
async def test_thought_summaries_are_not_part_of_the_answer():
    provider, _ = provider_with(
        response({"text": "reasoning summary", "thought": True}, {"text": "Final answer."})
    )
    result = await provider.complete(messages=[{"role": "user", "content": "q"}])
    assert result.content == "Final answer."


@pytest.mark.asyncio
async def test_agent_tool_loop_sends_signature_and_ids_back():
    provider, models = provider_with(
        response(function_call_part()),
        response({"text": "It's 18C in Paris."}),
    )
    agent = Agent(provider=provider, skills=[])
    agent.register_tool("get_weather", "Weather", lambda city: "18C sunny", SCHEMA)

    result = await agent.run("What's the weather in Paris?")

    assert result.text == "It's 18C in Paris."
    second = models.requests[1]["contents"]
    model_turn = next(c for c in second if c.role == "model")
    call_part = model_turn.parts[0]
    assert call_part.function_call.id == "fc-1"
    assert call_part.thought_signature == SIGNATURE  # byte-for-byte
    result_turn = second[-1]
    fr = result_turn.parts[0].function_response
    assert (fr.id, fr.name) == ("fc-1", "get_weather")
    assert fr.response == {"result": "18C sunny"}


@pytest.mark.asyncio
async def test_calls_without_ids_or_signatures_still_work():
    provider, models = provider_with(
        response(function_call_part(call_id=None, signature=None)),
        response({"text": "done"}),
    )
    agent = Agent(provider=provider, skills=[])
    agent.register_tool("get_weather", "Weather", lambda city: "sunny", SCHEMA)

    await agent.run("Weather?")

    call_part = next(c for c in models.requests[1]["contents"] if c.role == "model").parts[0]
    assert call_part.function_call.id is None
    assert call_part.thought_signature is None

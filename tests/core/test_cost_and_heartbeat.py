"""Response cost/token totals, real-cost budget tracking, and the agent heartbeat."""

import logging

import pytest

from teotl.core.agent import Agent
from teotl.core.security.policy import CostLimits
from teotl.core.types import CompletionResult, ToolCall
from teotl.primitives.harness.cost_tracker import CostTracker
from teotl.primitives.harness.heartbeat import (
    ErrorThresholdCheck,
    HeartbeatMonitor,
    StuckDetectionCheck,
)


class Scripted:
    """Returns queued results, each with the given usage; then a final answer."""

    context_window = 200_000
    max_tokens = 4096

    def __init__(self, *results, model="claude-haiku-4-5", usage=(1000, 100)):
        self.model = self.model_name = model
        self.results = list(results)
        self.usage = {"input_tokens": usage[0], "output_tokens": usage[1]}
        self.calls = 0

    async def complete(self, **kwargs):
        self.calls += 1
        result = self.results.pop(0) if self.results else CompletionResult(content="done")
        result.usage = dict(self.usage)
        return result


def call(tool, **args):
    return CompletionResult(
        tool_calls=[ToolCall(id=f"id_{tool}", name=tool, args=args)], done=False
    )


# Haiku 4.5: $1 / $5 per million tokens -> 1000 in + 100 out = $0.0015 per call
PER_CALL = 1000 * 1e-6 + 100 * 5e-6


class TestResponseTotals:
    @pytest.mark.asyncio
    async def test_cost_and_tokens_cover_every_call(self):
        provider = Scripted(call("echo", text="hi"))
        agent = Agent(provider=provider, skills=[])
        agent.register_tool("echo", "Echo", lambda text: text)

        response = await agent.run("say hi")

        assert provider.calls == 2
        assert response.input_tokens == 2000
        assert response.output_tokens == 200
        assert response.tokens_used == 2200
        assert response.cost == pytest.approx(2 * PER_CALL)

    @pytest.mark.asyncio
    async def test_cost_reported_without_a_cost_tracker(self):
        response = await Agent(provider=Scripted(), skills=[]).run("hi")
        assert response.cost == pytest.approx(PER_CALL)

    @pytest.mark.asyncio
    async def test_unknown_model_costs_zero_and_warns_once(self, caplog):
        agent = Agent(provider=Scripted(model="my-local-model"), skills=[])
        with caplog.at_level(logging.WARNING, logger="teotl.core.agent"):
            first = await agent.run("hi")
            await agent.run("hi again")
        assert first.cost == 0.0
        assert caplog.text.count("No pricing for model 'my-local-model'") == 1

    @pytest.mark.asyncio
    async def test_cost_tracker_records_real_cost(self, tmp_path):
        tracker = CostTracker(CostLimits(), tmp_path)
        provider = Scripted(call("echo", text="hi"), model="claude-sonnet-5-5")
        agent = Agent(provider=provider, skills=[], cost_tracker=tracker)
        agent.register_tool("echo", "Echo", lambda text: text)

        response = await agent.run("say hi")

        # Sonnet 5.5: $2 / $10 per million tokens
        assert response.cost == pytest.approx(2 * (1000 * 2e-6 + 100 * 10e-6))
        assert tracker.total_spent == pytest.approx(response.cost)


def monitor(tmp_path, *checks):
    return HeartbeatMonitor(
        agent_id="t", workspace_dir=tmp_path, checks=list(checks), check_interval_turns=1
    )


class TestAgentHeartbeat:
    @pytest.mark.asyncio
    async def test_repeated_tool_errors_stop_the_run(self, tmp_path):
        def broken():
            raise RuntimeError("service down")

        provider = Scripted(*[call("broken") for _ in range(20)])
        agent = Agent(
            provider=provider,
            skills=[],
            max_turns=20,
            heartbeat_monitor=monitor(tmp_path, ErrorThresholdCheck(max_consecutive_errors=3)),
        )
        agent.register_tool("broken", "Always fails", broken)

        response = await agent.run("try it")

        assert response.text.startswith("Stopped by heartbeat monitor")
        assert "consecutive errors" in response.text
        assert provider.calls == 3  # stopped after the third failure, not at max_turns

    @pytest.mark.asyncio
    async def test_no_progress_stops_the_run(self, tmp_path):
        provider = Scripted(*[call("missing_tool") for _ in range(20)])  # unknown tool -> error
        agent = Agent(
            provider=provider,
            skills=[],
            max_turns=20,
            heartbeat_monitor=monitor(tmp_path, StuckDetectionCheck(max_turns_without_progress=2)),
        )

        response = await agent.run("go")

        assert "Agent stuck" in response.text
        assert provider.calls == 3

    @pytest.mark.asyncio
    async def test_healthy_run_is_not_interrupted(self, tmp_path):
        escalations = []
        provider = Scripted(*[call("echo", text=str(i)) for i in range(4)])
        agent = Agent(
            provider=provider,
            skills=[],
            max_turns=10,
            heartbeat_monitor=monitor(
                tmp_path,
                ErrorThresholdCheck(max_consecutive_errors=2),
                StuckDetectionCheck(max_turns_without_progress=2),
            ),
        )
        agent.register_tool("echo", "Echo", lambda text: text)
        agent.events.on("heartbeat_escalation", lambda e, **kw: escalations.append(e))

        response = await agent.run("count")

        assert response.text == "done"
        assert provider.calls == 5
        assert escalations == []


@pytest.mark.asyncio
async def test_harness_records_real_costs_once(tmp_path, monkeypatch):
    from teotl.primitives.harness import PlannerWorkerHarness

    monkeypatch.chdir(tmp_path)
    plan = "## Step 1: Write f1\n\n**File:** `f1.txt`\n**Change:** create it"
    planner = Scripted(CompletionResult(content=plan), model="claude-sonnet-5-5")
    worker = Scripted(
        call("bash", command="echo hi > f1.txt"), CompletionResult(content="STEP_STATUS: DONE")
    )
    harness = PlannerWorkerHarness(
        agent_id="t",
        planner_provider=planner,
        worker_provider=worker,
        workspace_dir=tmp_path / "ws",
        worker_skills=[],
        require_approval_for_continuation=False,
        enable_janitor=False,
    )
    assert harness.worker.agent.heartbeat is None  # the harness runs the heartbeat itself

    await harness.plan(goals="write f1")
    result = await harness.execute_next_step(max_retries=0)

    planning_cost = 1000 * 2e-6 + 100 * 10e-6  # one Sonnet 5.5 call
    assert result.success, result.error
    assert result.cost == pytest.approx(2 * PER_CALL)  # two Haiku 4.5 calls
    assert harness.cost_tracker.total_spent == pytest.approx(planning_cost + result.cost)


def test_every_harness_agent_shares_the_cost_tracker(tmp_path):
    from teotl.primitives.harness import PlannerWorkerHarness

    harness = PlannerWorkerHarness(
        agent_id="t",
        planner_provider=Scripted(model="claude-sonnet-5-5"),
        worker_provider=Scripted(),
        workspace_dir=tmp_path / "ws",
        worker_skills=[],
    )
    tracker = harness.cost_tracker
    assert tracker is not None
    assert harness.planner.agent.cost_tracker is tracker
    assert harness.worker.agent.cost_tracker is tracker
    assert harness.evaluator.agent.cost_tracker is tracker
    assert harness.janitor.extraction_agent.cost_tracker is tracker

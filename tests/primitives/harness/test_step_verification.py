"""Planner-worker: step limits, evidence-based success, and safety checks on retries."""

from types import SimpleNamespace

import pytest

from teotl.core.types import CompletionResult, ToolCall, ToolResult
from teotl.primitives.harness import PlannerWorkerHarness
from teotl.primitives.harness.plan import PlanStep
from teotl.primitives.harness.worker import _concrete_path, _status_line


class Scripted:
    """Provider returning queued results (then a plain reply)."""

    model = model_name = "scripted"
    context_window = 200_000
    max_tokens = 4096

    def __init__(self, *results):
        self.results = list(results)

    async def complete(self, **kwargs):
        return self.results.pop(0) if self.results else CompletionResult(content="ok")


def text(t):
    return CompletionResult(content=t)


def bash(command):
    return CompletionResult(
        tool_calls=[ToolCall(id=command[:20], name="bash", args={"command": command})], done=False
    )


def plan_text(n):
    return "\n\n".join(
        f"## Step {i}: Write file {i}\n\n**File:** `f{i}.txt`\n**Change:** create it\n**Verify:** `test -f f{i}.txt`"
        for i in range(1, n + 1)
    )


def harness(tmp_path, planner, worker, **kw):
    return PlannerWorkerHarness(
        agent_id="t",
        planner_provider=planner,
        worker_provider=worker,
        workspace_dir=tmp_path / "ws",
        worker_skills=[],
        require_approval_for_continuation=False,
        enable_janitor=False,
        enable_heartbeat=False,
        enable_cost_tracking=False,
        **kw,
    )


@pytest.fixture(autouse=True)
def in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


class TestHelpers:
    @pytest.mark.parametrize(
        "value",
        [None, "", "<proj>/calc.py", "N/A (environment check)", "`a.py` and `b.py`", "src/*.py"],
    )
    def test_concrete_path_rejects_placeholders(self, value):
        assert _concrete_path(value) is None

    def test_concrete_path_accepts_real_paths(self, tmp_path):
        assert _concrete_path("`calc.py`") == (tmp_path / "calc.py").resolve()
        assert _concrete_path("/etc/passwd") == __import__("pathlib").Path("/etc/passwd").resolve()

    def test_status_line_uses_last_marker(self):
        assert _status_line("STEP_STATUS: FAILED - x\n...\nSTEP_STATUS: DONE") == "DONE"
        assert _status_line("all good, step complete!") is None


class TestPlanner:
    @pytest.mark.asyncio
    async def test_plan_is_capped_at_max_steps(self, tmp_path):
        h = harness(tmp_path, Scripted(text(plan_text(12))), Scripted(), max_plan_steps=3)
        plan = await h.plan(goals="write files")
        assert plan.total_steps == 3

    @pytest.mark.asyncio
    async def test_prompt_states_the_limit(self, tmp_path):
        seen = []

        class Capture(Scripted):
            async def complete(self, **kwargs):
                seen.append(kwargs["messages"][-1]["content"])
                return text(plan_text(1))

        h = harness(tmp_path, Capture(), Scripted(), max_plan_steps=4)
        await h.plan(goals="write a file")
        prompt = seen[0] if isinstance(seen[0], str) else str(seen[0])
        assert "at most 4" in prompt


class TestStepVerification:
    @pytest.mark.asyncio
    async def test_real_work_with_done_succeeds(self, tmp_path):
        worker = Scripted(bash("echo hi > f1.txt"), text("Created f1.txt.\nSTEP_STATUS: DONE"))
        h = harness(tmp_path, Scripted(text(plan_text(1))), worker)
        await h.plan(goals="write f1")
        result = await h.execute_next_step(max_retries=0)
        assert result.success, result.error
        assert (tmp_path / "f1.txt").exists()
        assert h.is_complete()

    @pytest.mark.asyncio
    async def test_claiming_done_without_tools_fails(self, tmp_path):
        worker = Scripted(text("All done, step complete! ✅\nSTEP_STATUS: DONE"))
        h = harness(tmp_path, Scripted(text(plan_text(1))), worker)
        await h.plan(goals="write f1")
        result = await h.execute_next_step(max_retries=0)
        assert not result.success
        assert "without using any tools" in result.error
        plan = h.worker.plan_manager.load()
        assert plan.steps[0].skipped and not plan.steps[0].completed  # ⊘, not ✓
        assert h.is_complete()  # loops like `while not is_complete()` terminate

    @pytest.mark.asyncio
    async def test_missing_target_file_fails(self, tmp_path):
        worker = Scripted(bash("echo hi > other.txt"), text("STEP_STATUS: DONE"))
        h = harness(tmp_path, Scripted(text(plan_text(1))), worker)
        await h.plan(goals="write f1")
        result = await h.execute_next_step(max_retries=0)
        assert not result.success
        assert "does not exist" in result.error

    @pytest.mark.asyncio
    async def test_blocked_tool_call_fails_even_if_model_says_done(self, tmp_path):
        worker = Scripted(bash("rm -rf /"), text("Cleaned up.\nSTEP_STATUS: DONE"))
        h = harness(tmp_path, Scripted(text(plan_text(1))), worker)
        await h.plan(goals="write f1")
        result = await h.execute_next_step(max_retries=0)
        assert not result.success
        assert "blocked or failed" in result.error
        plan = h.worker.plan_manager.load()
        assert not plan.steps[0].completed  # not shown as ✓

    @pytest.mark.asyncio
    async def test_worker_reported_failure(self, tmp_path):
        worker = Scripted(bash("true"), text("STEP_STATUS: FAILED - tests fail"))
        h = harness(tmp_path, Scripted(text(plan_text(1))), worker)
        await h.plan(goals="write f1")
        result = await h.execute_next_step(max_retries=0)
        assert not result.success and "FAILED" in result.error

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_feedback(self, tmp_path):
        worker = Scripted(
            text("I think it's done.\nSTEP_STATUS: DONE"),  # attempt 1: no tools -> fail
            bash("echo hi > f1.txt"),
            text("STEP_STATUS: DONE"),  # retry: real work -> success
        )
        h = harness(tmp_path, Scripted(text(plan_text(1))), worker)
        await h.plan(goals="write f1")
        result = await h.execute_next_step(max_retries=1)
        assert result.success, result.error


class TestSafetyOnRetry:
    @pytest.mark.asyncio
    async def test_blocked_path_stays_blocked_on_retry(self, tmp_path):
        plan = "## Step 1: Edit passwd\n\n**File:** `/etc/passwd`\n**Change:** append a line"
        worker = Scripted(bash("true"), text("STEP_STATUS: DONE"))
        h = harness(tmp_path, Scripted(text(plan)), worker)
        h.worker.policy.filesystem.blocked_paths.append("/etc/**")
        await h.plan(goals="edit passwd")

        first = await h.worker.execute_current_step()
        retry = await h.worker.retry_step(1, feedback="try again")

        assert not first.success and "Security policy" in first.error
        assert not retry.success and "Security policy" in retry.error
        assert worker.results  # the worker model was never called

    @pytest.mark.asyncio
    async def test_placeholder_paths_are_not_blocked(self, tmp_path):
        step = PlanStep(number=1, description="check env", file_path="N/A (environment check)")
        h = harness(tmp_path, Scripted(), Scripted())
        assert h.worker._validate_step_safety(step) == (True, None)


def test_evaluate_reports_first_failed_tool():
    from teotl.primitives.harness.worker import Worker

    worker = Worker.__new__(Worker)
    response = SimpleNamespace(
        text="STEP_STATUS: DONE",
        tool_calls_made=[ToolCall(id="1", name="bash", args={})],
        tool_results=[ToolResult(call_id="1", error="Blocked: Destructive action", is_error=True)],
    )
    ok, reason = worker._evaluate_step(PlanStep(number=1, description="x"), response)
    assert not ok and "Blocked: Destructive action" in reason

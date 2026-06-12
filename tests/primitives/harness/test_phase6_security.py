"""Integration tests for Phase 6 security features.

Tests the following Phase 6 capabilities:
1. Cost tracking and budget enforcement
2. Human-in-the-loop approval gates
3. Halt on critical escalations
4. SecurityPolicy enforcement in Worker
"""

from unittest.mock import MagicMock

import pytest

from teotl.core.security.policy import CostLimits, SecurityPolicy
from teotl.primitives.harness.cost_tracker import CostTracker
from teotl.primitives.harness.evaluator import CycleApprovalRequest, Evaluation
from teotl.primitives.harness.exceptions import (
    BudgetExceededError,
    ExecutionHaltedError,
)
from teotl.primitives.harness.orchestrator import PlannerWorkerHarness
from teotl.primitives.harness.worker import Worker


class TestCostTracker:
    """Test CostTracker budget enforcement."""

    def test_can_spend_within_budget(self, tmp_path):
        """Test that operations within budget are allowed."""
        limits = CostLimits(
            max_per_hour=10.0,
            max_per_day=100.0,
            max_per_month=1000.0,
        )
        tracker = CostTracker(limits=limits, workspace_dir=tmp_path)

        # Should allow spending within budget
        assert tracker.can_spend(5.0) is True
        tracker.record(5.0, "test")

        # Should still have budget remaining
        assert tracker.can_spend(4.0) is True

    def test_budget_exceeded_raises_error(self, tmp_path):
        """Test that exceeding budget raises BudgetExceededError."""
        limits = CostLimits(
            max_per_hour=10.0,
            max_per_day=100.0,
        )
        tracker = CostTracker(limits=limits, workspace_dir=tmp_path)

        # Record spending up to limit
        tracker.record(9.0, "test")

        # Should raise error when exceeding hourly limit
        with pytest.raises(BudgetExceededError) as exc_info:
            tracker.can_spend(2.0)

        assert exc_info.value.limit_type == "hourly"
        assert exc_info.value.spent == 9.0
        assert exc_info.value.limit == 10.0

    def test_cost_summary(self, tmp_path):
        """Test cost summary includes all windows."""
        limits = CostLimits(
            max_per_hour=10.0,
            max_per_day=100.0,
            max_per_month=1000.0,
        )
        tracker = CostTracker(limits=limits, workspace_dir=tmp_path)

        tracker.record(5.0, "planning")
        tracker.record(2.5, "execution")

        summary = tracker.get_summary()

        assert summary["total_spent"] == 7.5
        assert summary["hourly_spent"] == 7.5
        assert summary["daily_spent"] == 7.5
        assert summary["monthly_spent"] == 7.5
        assert summary["hourly_remaining"] == 2.5
        assert summary["daily_remaining"] == 92.5

    def test_cost_persistence(self, tmp_path):
        """Test that costs persist across tracker instances."""
        limits = CostLimits(max_per_hour=10.0, max_per_day=100.0)

        # First tracker records costs
        tracker1 = CostTracker(limits=limits, workspace_dir=tmp_path)
        tracker1.record(5.0, "test")

        # Second tracker should load previous costs
        tracker2 = CostTracker(limits=limits, workspace_dir=tmp_path)
        assert tracker2.total_spent == 5.0


class TestWorkerSecurityPolicy:
    """Test Worker SecurityPolicy enforcement."""

    @pytest.mark.asyncio
    async def test_worker_validates_step_safety(self, tmp_path):
        """Test that Worker validates steps against security policy."""
        # Create restrictive policy that blocks /etc
        policy = SecurityPolicy.create_default("test-agent", preset="autonomous-dev")
        policy.filesystem.blocked_paths = ["/etc/*"]

        # Mock provider
        provider = MagicMock()
        provider.model = "test-model"

        worker = Worker(
            agent_id="test-agent",
            provider=provider,
            workspace_dir=tmp_path,
            policy=policy,
        )

        # Create a plan step that tries to access blocked path
        from teotl.primitives.harness.plan import PlanStep

        blocked_step = PlanStep(
            number=1,
            description="Access blocked path",
            file_path="/etc/passwd",
        )

        # Validate step safety
        is_safe, error = worker._validate_step_safety(blocked_step)
        assert is_safe is False
        assert "blocked by security policy" in error.lower()

    @pytest.mark.asyncio
    async def test_worker_allows_safe_steps(self, tmp_path):
        """Test that Worker allows steps within workspace."""
        policy = SecurityPolicy.create_default("test-agent", preset="autonomous-dev")
        # Add tmp_path to allowed paths so workspace files are accessible
        policy.filesystem.allowed_paths.append(f"{tmp_path}/**")

        provider = MagicMock()
        provider.model = "test-model"

        worker = Worker(
            agent_id="test-agent",
            provider=provider,
            workspace_dir=tmp_path,
            policy=policy,
        )

        from teotl.primitives.harness.plan import PlanStep

        safe_step = PlanStep(
            number=1,
            description="Access workspace file",
            file_path=str(tmp_path / "test.py"),
        )

        is_safe, error = worker._validate_step_safety(safe_step)
        assert is_safe is True
        assert error is None


class TestCycleApprovalRequest:
    """Test CycleApprovalRequest structure."""

    def test_approval_request_summary(self):
        """Test approval request generates readable summary."""
        evaluation = Evaluation(
            goals_achieved=False,
            confidence=0.8,
            what_was_done=["Task 1", "Task 2"],
            what_remains=["Task 3", "Task 4"],
            test_status="passing",
        )

        request = CycleApprovalRequest(
            cycle=1,
            evaluation=evaluation,
            estimated_next_cost=15.0,
            cost_summary={
                "total_spent": 25.0,
                "daily_remaining": 75.0,
            },
        )

        summary = request.to_summary_text()

        assert "Cycle 1 Complete" in summary
        assert "Confidence: 80%" in summary
        assert "Task 1" in summary
        assert "Task 3" in summary
        assert "$15.00" in summary


class TestExecutionHalt:
    """Test execution halt on critical escalations."""

    def test_execution_halted_error_structure(self):
        """Test ExecutionHaltedError includes escalation details."""
        from teotl.primitives.harness.heartbeat import EscalationEvent

        escalation = EscalationEvent(
            title="Agent Stuck",
            severity="critical",
            message="No progress for 10 turns",
            context={},
            suggested_actions=["Review agent state", "Check for errors"],
        )

        error = ExecutionHaltedError(
            message="Halted due to critical issues",
            escalations=[escalation],
            turn=25,
            recoverable=True,
        )

        assert error.turn == 25
        assert error.recoverable is True
        assert len(error.escalations) == 1
        assert error.escalations[0].severity == "critical"

        error_dict = error.to_dict()
        assert error_dict["type"] == "ExecutionHaltedError"
        assert error_dict["escalation_count"] == 1


class TestPlannerWorkerHarnessPhase6:
    """Integration tests for PlannerWorkerHarness Phase 6 features."""

    @pytest.mark.asyncio
    async def test_harness_initializes_with_cost_tracker(self, tmp_path):
        """Test that harness initializes cost tracker correctly."""
        from teotl.core.provider import Provider

        planner_provider = MagicMock(spec=Provider)
        planner_provider.model = "claude-sonnet-4"

        worker_provider = MagicMock(spec=Provider)
        worker_provider.model = "claude-3-haiku-20240307"

        # Create policy with cost limits
        policy = SecurityPolicy.create_default("test-agent", preset="autonomous-dev")

        harness = PlannerWorkerHarness(
            agent_id="test-agent",
            planner_provider=planner_provider,
            worker_provider=worker_provider,
            workspace_dir=tmp_path,
            worker_policy=policy,
            enable_cost_tracking=True,
        )

        # Should have cost tracker initialized
        assert harness.cost_tracker is not None
        assert harness.cost_tracker.limits == policy.cost_limits

    @pytest.mark.asyncio
    async def test_harness_requires_approval_by_default(self, tmp_path):
        """Test that harness requires approval by default."""
        from teotl.core.provider import Provider

        planner_provider = MagicMock(spec=Provider)
        planner_provider.model = "claude-sonnet-4"

        worker_provider = MagicMock(spec=Provider)
        worker_provider.model = "claude-3-haiku-20240307"

        harness = PlannerWorkerHarness(
            agent_id="test-agent",
            planner_provider=planner_provider,
            worker_provider=worker_provider,
            workspace_dir=tmp_path,
        )

        # Should require approval by default
        assert harness.require_approval is True

    @pytest.mark.asyncio
    async def test_harness_halts_on_critical_by_default(self, tmp_path):
        """Test that harness halts on critical escalations by default."""
        from teotl.core.provider import Provider

        planner_provider = MagicMock(spec=Provider)
        planner_provider.model = "claude-sonnet-4"

        worker_provider = MagicMock(spec=Provider)
        worker_provider.model = "claude-3-haiku-20240307"

        harness = PlannerWorkerHarness(
            agent_id="test-agent",
            planner_provider=planner_provider,
            worker_provider=worker_provider,
            workspace_dir=tmp_path,
        )

        # Should halt on critical by default
        assert harness.halt_on_critical is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

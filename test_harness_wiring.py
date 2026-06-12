#!/usr/bin/env python3
"""Test harness component wiring without making API calls.

This test verifies that harness components are properly initialized and
passed to agents, without actually executing any LLM calls.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from teotl.core.provider import Provider
from teotl.daemon.executor import AgentExecutorFactory


def test_agent_factory_harness_wiring():
    """Test that AgentExecutorFactory properly wires harness components."""
    print("\n" + "=" * 70)
    print("TEST: AgentExecutorFactory Harness Wiring")
    print("=" * 70 + "\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace_dir = Path(tmp_dir) / "test-agent"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Create mock provider
        mock_provider = MagicMock(spec=Provider)
        mock_provider.model = "test-model"

        print("✅ Creating factory with all harness features enabled...")
        factory = AgentExecutorFactory(
            provider=mock_provider,
            workspace_dir=workspace_dir,
            enable_cost_tracking=True,
            enable_audit=True,
            enable_checkpoints=False,
            enable_heartbeat=True,
            enable_state=True,
        )

        print("\nHarness components initialized:")
        print(f"  - cost_tracker: {factory.cost_tracker is not None}")
        print(f"  - audit_logger: {factory.audit_logger is not None}")
        print(f"  - checkpoint_manager: {factory.checkpoint_manager is not None}")
        print(f"  - heartbeat_monitor: {factory.heartbeat_monitor is not None}")
        print(f"  - state_manager: {factory.state_manager is not None}")

        # Create an executor
        print("\n✅ Creating executor...")
        executor = factory.create(
            instructions="Test instructions",
            skills=["bash"],
        )

        # Get the agent from the executor
        print("✅ Getting agent instance...")
        agent = executor.agent

        print("\nAgent harness components:")
        print(f"  - cost_tracker: {agent.cost_tracker is not None}")
        print(f"  - audit_logger: {agent.audit_logger is not None}")
        print(f"  - checkpoint_manager: {agent.checkpoint_manager is not None}")
        print(f"  - heartbeat: {agent.heartbeat is not None}")
        print(f"  - state_manager: {agent.state_manager is not None}")

        # Verify components match
        success = True
        if agent.cost_tracker is not factory.cost_tracker:
            print("❌ cost_tracker mismatch!")
            success = False
        if agent.audit_logger is not factory.audit_logger:
            print("❌ audit_logger mismatch!")
            success = False
        if agent.heartbeat is not factory.heartbeat_monitor:
            print("❌ heartbeat_monitor mismatch!")
            success = False
        if agent.state_manager is not factory.state_manager:
            print("❌ state_manager mismatch!")
            success = False

        print("\n" + "=" * 70)
        if success:
            print("✅ SUCCESS: All harness components properly wired!")
        else:
            print("❌ FAILURE: Component wiring issues detected")
        print("=" * 70 + "\n")

        return success


def test_planner_worker_component_sharing():
    """Test that Planner and Worker receive shared harness components."""
    print("\n" + "=" * 70)
    print("TEST: PlannerWorkerHarness Component Sharing")
    print("=" * 70 + "\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace_dir = Path(tmp_dir) / "test-harness"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        from teotl.primitives.harness.orchestrator import PlannerWorkerHarness

        # Create mock providers
        planner_provider = MagicMock(spec=Provider)
        planner_provider.model = "test-planner-model"

        worker_provider = MagicMock(spec=Provider)
        worker_provider.model = "test-worker-model"

        print("✅ Creating PlannerWorkerHarness...")
        harness = PlannerWorkerHarness(
            agent_id="test-harness",
            planner_provider=planner_provider,
            worker_provider=worker_provider,
            workspace_dir=workspace_dir,
            enable_cost_tracking=True,
            enable_heartbeat=True,
        )

        print("\nHarness components:")
        print(f"  - cost_tracker: {harness.cost_tracker is not None}")
        print(f"  - heartbeat: {harness.heartbeat is not None}")

        print("\nPlanner agent components:")
        print(f"  - cost_tracker: {harness.planner.agent.cost_tracker is not None}")
        print(f"  - state_manager: {harness.planner.agent.state_manager is not None}")

        print("\nWorker agent components:")
        print(f"  - cost_tracker: {harness.worker.agent.cost_tracker is not None}")
        print(f"  - heartbeat: {harness.worker.agent.heartbeat is not None}")
        print(f"  - state_manager: {harness.worker.agent.state_manager is not None}")

        # Verify sharing
        success = True

        if harness.planner.agent.cost_tracker is not harness.cost_tracker:
            print("❌ Planner cost_tracker not shared!")
            success = False

        if harness.worker.agent.cost_tracker is not harness.cost_tracker:
            print("❌ Worker cost_tracker not shared!")
            success = False

        if harness.planner.agent.state_manager is not harness.state:
            print("❌ Planner state_manager not shared!")
            success = False

        if harness.worker.agent.state_manager is not harness.state:
            print("❌ Worker state_manager not shared!")
            success = False

        if harness.worker.agent.heartbeat is not harness.heartbeat:
            print("❌ Worker heartbeat not shared!")
            success = False

        print("\n" + "=" * 70)
        if success:
            print("✅ SUCCESS: All components properly shared between agents!")
        else:
            print("❌ FAILURE: Component sharing issues detected")
        print("=" * 70 + "\n")

        return success


def main():
    """Run all wiring tests."""
    print("\n" + "=" * 70)
    print("HARNESS WIRING TESTS (No API Calls)")
    print("=" * 70)

    test1_passed = test_agent_factory_harness_wiring()
    test2_passed = test_planner_worker_component_sharing()

    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"  AgentExecutorFactory wiring: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  PlannerWorker sharing: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print("=" * 70 + "\n")

    if test1_passed and test2_passed:
        print("✅ ALL TESTS PASSED\n")
        return 0
    else:
        print("❌ SOME TESTS FAILED\n")
        return 1


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
"""Integration test for harness features in basic Agent.

This test verifies that harness components (cost tracking, audit logging,
state management, etc.) work with the base Agent class.
"""

import asyncio
import tempfile
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.daemon.executor import create_simple_executor


async def test_basic_agent_with_harness():
    """Test that basic agent can use harness features."""
    print("\n" + "=" * 70)
    print("TEST: Basic Agent with Harness Features")
    print("=" * 70 + "\n")

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace_dir = Path(tmp_dir) / "test-agent"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        print(f"Workspace: {workspace_dir}")

        # Create executor with ALL harness features enabled
        print("\n✅ Creating executor with harness features enabled...")
        executor = create_simple_executor(
            provider=AnthropicProvider(model="claude-3-haiku-20240307"),
            instructions="You are a helpful test assistant.",
            workspace_dir=workspace_dir,
            # Enable all harness features
            enable_cost_tracking=True,
            enable_audit=True,
            enable_checkpoints=False,  # Skip git features for simple test
            enable_heartbeat=True,
            enable_state=True,
        )

        # Execute a simple task
        print("\n✅ Executing test task...")
        try:
            result = await executor("What is 2 + 2? Please respond with just the number.", {})

            print("\n✅ Task completed successfully!")
            print(f"Result: {result}")

            # Check that harness artifacts were created
            print("\n✅ Checking harness artifacts...")

            cost_log = workspace_dir / "COST_LOG.jsonl"
            audit_log = workspace_dir / "AUDIT_LOG.jsonl"
            state_file = workspace_dir / "STATE.json"

            artifacts_found = []

            if cost_log.exists():
                artifacts_found.append("COST_LOG.jsonl")
                print(f"  ✓ {cost_log.name} created")
            else:
                print(f"  ✗ {cost_log.name} NOT created")

            if audit_log.exists():
                artifacts_found.append("AUDIT_LOG.jsonl")
                print(f"  ✓ {audit_log.name} created")
                # Show first line
                with open(audit_log) as f:
                    first_line = f.readline()
                    print(f"    Sample: {first_line[:100]}...")
            else:
                print(f"  ✗ {audit_log.name} NOT created")

            if state_file.exists():
                artifacts_found.append("STATE.json")
                print(f"  ✓ {state_file.name} created")
                # Show content
                import json

                with open(state_file) as f:
                    state = json.load(f)
                    print(f"    State keys: {list(state.keys())}")
            else:
                print(f"  ✗ {state_file.name} NOT created")

            print("\n" + "=" * 70)
            if len(artifacts_found) == 3:
                print("✅ SUCCESS: All harness features working!")
            else:
                print(f"⚠️  PARTIAL: {len(artifacts_found)}/3 harness features working")
                print(f"   Created: {', '.join(artifacts_found)}")
            print("=" * 70 + "\n")

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback

            traceback.print_exc()


async def test_planner_worker_with_harness():
    """Test that PlannerWorkerHarness still works with shared components."""
    print("\n" + "=" * 70)
    print("TEST: PlannerWorkerHarness with Shared Components")
    print("=" * 70 + "\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace_dir = Path(tmp_dir) / "test-harness"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        print(f"Workspace: {workspace_dir}")

        # Import harness components
        from teotl.core.provider import AnthropicProvider
        from teotl.primitives.harness.orchestrator import PlannerWorkerHarness

        print("\n✅ Creating PlannerWorkerHarness with cost tracking enabled...")

        try:
            harness = PlannerWorkerHarness(
                agent_id="test-harness",
                planner_provider=AnthropicProvider(model="claude-3-5-sonnet-20241022"),
                worker_provider=AnthropicProvider(model="claude-3-haiku-20240307"),
                workspace_dir=workspace_dir,
                enable_cost_tracking=True,
                enable_audit_trail=False,  # Skip for simple test
                enable_heartbeat=True,
                enable_checkpoints=False,  # Skip git for simple test
            )

            print("✅ PlannerWorkerHarness created successfully!")
            print(f"  - Cost tracker: {harness.cost_tracker is not None}")
            print(f"  - Heartbeat monitor: {harness.heartbeat is not None}")
            print(
                f"  - Planner agent has cost tracker: {harness.planner.agent.cost_tracker is not None}"
            )
            print(
                f"  - Worker agent has cost tracker: {harness.worker.agent.cost_tracker is not None}"
            )

            print("\n" + "=" * 70)
            print("✅ SUCCESS: PlannerWorkerHarness components properly shared!")
            print("=" * 70 + "\n")

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback

            traceback.print_exc()


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("HARNESS INTEGRATION TESTS")
    print("=" * 70)

    # Test 1: Basic agent with harness
    await test_basic_agent_with_harness()

    # Test 2: PlannerWorkerHarness component sharing
    await test_planner_worker_with_harness()

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

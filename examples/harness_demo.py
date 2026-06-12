"""Demo of Harness Engineering primitives.

Shows how to use ProgressTracker, StateManager, and ContextJanitor
independently for custom agent workflows.
"""

import asyncio
from pathlib import Path

from teotl.primitives.harness import ContextJanitor, ProgressTracker, StateManager


async def main():
    """Demo harness primitives."""
    print("🔧 Harness Engineering Primitives Demo")
    print("=" * 60)
    print()

    agent_id = "demo-agent"
    workspace = Path.home() / ".forge" / "agents" / agent_id

    # -------------------------------------------------------------------
    # 1. ProgressTracker Demo
    # -------------------------------------------------------------------
    print("1️⃣  ProgressTracker (PROGRESS.md)")
    print("-" * 60)

    progress = ProgressTracker(agent_id)

    # Simulate a multi-step task
    tasks = [
        "Add type hints to utils.py",
        "Fix bug in parser.py",
        "Write tests for validator.py",
        "Update documentation",
        "Refactor database.py",
    ]

    # Start with first task
    progress.update(
        current=tasks[0],
        completed=[],
        remaining=tasks[1:],
    )

    print(f"✅ PROGRESS.md created at: {progress.path}")

    # Simulate completing tasks
    for i in range(len(tasks)):
        current = tasks[i] if i < len(tasks) else None
        completed = tasks[:i]
        remaining = tasks[i + 1 :]

        progress.update(
            current=current,
            completed=completed,
            remaining=remaining,
        )

        if current:
            print(f"   Working on: {current}")

    # Read final state
    final_state = progress.read()
    print(f"   Progress: {final_state.completion_percentage:.1f}% complete")
    print(f"   Completed {len(final_state.completed)} tasks")
    print()

    # -------------------------------------------------------------------
    # 2. StateManager Demo
    # -------------------------------------------------------------------
    print("2️⃣  StateManager (STATE.json)")
    print("-" * 60)

    state = StateManager(agent_id)

    # Save various state types
    state.save(
        phase="testing",
        tests_passed=4,
        tests_failed=1,
        last_error="ImportError in test_utils.py",
        credentials_valid=True,
        sync_cursor="2024-03-27T10:30:00Z",
    )

    print(f"✅ STATE.json created at: {state.path}")
    print(f"   Variables saved: {len(state.load())}")

    # Update specific values
    state.update(tests_passed=5, last_error=None)
    print("   Updated: tests_passed=5, last_error=None")

    # Use counters
    state.increment("consecutive_successes")
    state.increment("records_processed", by=10)
    print("   Incremented counters")

    # Use flags
    state.set_flag("ready_for_deployment", True)
    print("   Set flag: ready_for_deployment=True")

    # Read state
    current_phase = state.get("phase")
    tests_passed = state.get("tests_passed")
    print(f"   Current phase: {current_phase}")
    print(f"   Tests passed: {tests_passed}")
    print()

    # -------------------------------------------------------------------
    # 3. ContextJanitor Demo
    # -------------------------------------------------------------------
    print("3️⃣  ContextJanitor (DECISION_LOG.md)")
    print("-" * 60)

    janitor = ContextJanitor(agent_id, compact_every=5)

    print(f"✅ DECISION_LOG.md created at: {janitor.decision_log_path}")
    print(f"   Compaction interval: every {janitor.compact_every} turns")

    # Simulate agent turns
    agent_responses = [
        "I decided to add type hints to improve code quality.",
        "Fixed the import error because it was blocking tests.",
        "The tests are now passing (5/6).",
        "I chose to refactor the database module for better maintainability.",
        "Updated documentation to reflect the API changes.",
        "Added validation because the input was not being sanitized.",
        "Committed changes after all tests passed.",
        "I removed the deprecated function that was causing warnings.",
        "Fixed the bug in the parser by updating the regex pattern.",
        "The build is now successful.",
    ]

    for i, response in enumerate(agent_responses, 1):
        janitor.after_turn(response)

        if janitor.should_reset_context():
            print(f"   ⚠️  Context compaction at turn {i}")

    print(f"   Total turns: {janitor.get_turn_count()}")
    print(f"   Pending decisions: {len(janitor.get_pending_decisions())}")
    print()

    # -------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------
    print("=" * 60)
    print("✅ Demo Complete!")
    print()
    print("Check these files in your workspace:")
    print(f"   📄 {workspace / 'PROGRESS.md'}")
    print(f"   📄 {workspace / 'STATE.json'}")
    print(f"   📄 {workspace / 'DECISION_LOG.md'}")
    print()
    print("These artifacts persist across agent executions,")
    print("enabling durable state management and context compaction.")
    print()


if __name__ == "__main__":
    asyncio.run(main())

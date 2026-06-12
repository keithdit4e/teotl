"""Demo of Heartbeat Monitoring (Phase 5).

Shows autonomous oversight capabilities:
1. Health checks (stuck detection, error thresholds, progress monitoring)
2. Escalation (notify user on actionable issues)
3. Auto cleanup (archive old logs, rotate files)

Demonstrates:
- Detecting when agent is stuck (no progress for N turns)
- Detecting excessive consecutive errors
- Monitoring progress rate over time
- Escalation events with suggested actions
- Automatic workspace cleanup
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from teotl.primitives.harness import (
    CleanupPolicy,
    ErrorThresholdCheck,
    EscalationEvent,
    EscalationPolicy,
    HeartbeatMonitor,
    ProgressRateCheck,
    ProgressTracker,
    StateManager,
    StuckDetectionCheck,
)


def log_escalation_handler(event: EscalationEvent) -> None:
    """Simple escalation handler that logs to console."""
    print()
    print("=" * 70)
    print("🚨 ESCALATION EVENT")
    print("=" * 70)
    print()
    print(event.to_markdown())
    print("=" * 70)
    print()


async def main():
    """Demo heartbeat monitoring."""
    print("🏥 Heartbeat Monitoring Demo")
    print("=" * 70)
    print()

    # Setup
    agent_id = "heartbeat-demo"
    workspace = Path.home() / ".forge" / "agents" / agent_id
    workspace.mkdir(parents=True, exist_ok=True)

    print(f"📂 Workspace: {workspace}")
    print()

    # -------------------------------------------------------------------
    # DEMO 1: Health Checks - Normal Operation
    # -------------------------------------------------------------------
    print("=" * 70)
    print("DEMO 1: Health Checks - Normal Operation")
    print("=" * 70)
    print()

    # Create monitor
    monitor = HeartbeatMonitor(
        agent_id=agent_id,
        workspace_dir=workspace,
        checks=[
            StuckDetectionCheck(max_turns_without_progress=5),
            ErrorThresholdCheck(max_consecutive_errors=3),
            ProgressRateCheck(min_completion_per_hour=5.0),
        ],
        escalation_policy=EscalationPolicy(
            notify_on_critical=True,
            notify_on_warning=False,
            handlers=[log_escalation_handler],
        ),
        cleanup_policy=CleanupPolicy(
            archive_logs_older_than_days=7,
            max_archived_plans=5,
        ),
        check_interval_turns=3,
    )

    print("✅ Monitor created")
    print(monitor.get_status_summary())
    print()

    # Setup state and progress
    state = StateManager(agent_id, workspace)
    progress = ProgressTracker(agent_id, workspace)

    # Initialize healthy state
    state.save(
        execution_start_time=datetime.now().isoformat(),
        current_turn=0,
        consecutive_errors=0,
        last_progress_turn=0,
    )

    progress.update(
        current="Working on feature implementation",
        completed=["Setup environment", "Write tests"],
        remaining=["Implement feature", "Deploy"],
    )

    print("📝 Simulating normal operation...")
    print()

    # Simulate 10 turns with progress
    for turn in range(1, 11):
        state.update(
            current_turn=turn,
            last_progress_turn=turn,  # Making progress each turn
            consecutive_errors=0,
        )

        # Run heartbeat every 3 turns
        if monitor.should_run_heartbeat(turn):
            print(f"Turn {turn}: Running heartbeat check...")
            result = monitor.heartbeat(state=state, progress=progress)

            if result["healthy"]:
                print("  ✅ All checks passed")
            else:
                print(f"  ❌ {result['checks_failed']} check(s) failed")

            print(f"  Checks: {result['checks_passed']}/{result['checks_run']} passed")
            print()

    # -------------------------------------------------------------------
    # DEMO 2: Stuck Detection
    # -------------------------------------------------------------------
    print("=" * 70)
    print("DEMO 2: Stuck Detection - Agent Not Making Progress")
    print("=" * 70)
    print()

    print("💡 Scenario: Agent stuck on same task for 8 turns (threshold: 5)")
    print()

    # Reset and simulate stuck agent
    state.save(
        execution_start_time=datetime.now().isoformat(),
        current_turn=0,
        consecutive_errors=0,
        last_progress_turn=0,  # No progress since start
    )

    # Simulate 10 turns WITHOUT progress
    for turn in range(1, 11):
        state.update(
            current_turn=turn,
            # Note: NOT updating last_progress_turn - agent is stuck!
        )

        if monitor.should_run_heartbeat(turn):
            print(f"Turn {turn}: Running heartbeat check...")
            result = monitor.heartbeat(state=state, progress=progress)

            if result["healthy"]:
                print("  ✅ All checks passed")
            else:
                print(f"  ❌ {result['checks_failed']} check(s) failed")
                print(f"  🚨 {len(result['escalations'])} escalation(s)")

            print()

    # -------------------------------------------------------------------
    # DEMO 3: Error Threshold Detection
    # -------------------------------------------------------------------
    print("=" * 70)
    print("DEMO 3: Error Threshold - Too Many Consecutive Errors")
    print("=" * 70)
    print()

    print("💡 Scenario: Agent encountering 5 consecutive errors (threshold: 3)")
    print()

    # Reset and simulate errors
    state.save(
        execution_start_time=datetime.now().isoformat(),
        current_turn=0,
        consecutive_errors=0,
        last_progress_turn=0,
    )

    # Simulate turns with increasing errors
    for turn in range(1, 11):
        # First 5 turns: accumulate errors
        if turn <= 5:
            consecutive_errors = turn
            last_error = f"Error {turn}: Failed to access resource"
        else:
            # After turn 5: errors resolved
            consecutive_errors = 0
            last_error = None

        state.update(
            current_turn=turn,
            consecutive_errors=consecutive_errors,
        )

        if last_error:
            state.update(last_error=last_error)

        if monitor.should_run_heartbeat(turn):
            print(f"Turn {turn}: Running heartbeat check (errors: {consecutive_errors})...")
            result = monitor.heartbeat(state=state, progress=progress)

            if result["healthy"]:
                print("  ✅ All checks passed")
            else:
                print(f"  ❌ {result['checks_failed']} check(s) failed")
                print(f"  🚨 {len(result['escalations'])} escalation(s)")

            print()

    # -------------------------------------------------------------------
    # DEMO 4: Progress Rate Monitoring
    # -------------------------------------------------------------------
    print("=" * 70)
    print("DEMO 4: Progress Rate - Slow Progress Detection")
    print("=" * 70)
    print()

    print("💡 Scenario: Agent making very slow progress (2%/hour, min: 5%/hour)")
    print()

    # Reset and simulate slow progress
    start_time = datetime.now() - timedelta(hours=5)  # 5 hours ago
    state.save(
        execution_start_time=start_time.isoformat(),
        current_turn=10,
        consecutive_errors=0,
        last_progress_turn=10,
    )

    # Update progress to show only 10% completion in 5 hours = 2%/hour
    progress.update(
        current="Still working on feature implementation",
        completed=["Setup environment"],  # Only 1 task done
        remaining=[
            "Write tests",
            "Implement feature",
            "Deploy",
            "Document",
            "Review",
        ],  # Many remain
    )

    print("Running heartbeat check...")
    result = monitor.heartbeat(state=state, progress=progress)

    if result["healthy"]:
        print("  ✅ All checks passed")
    else:
        print(f"  ⚠️  {result['checks_failed']} check(s) failed")
        print("  Progress rate issue detected")

    print()

    # -------------------------------------------------------------------
    # DEMO 5: Auto Cleanup
    # -------------------------------------------------------------------
    print("=" * 70)
    print("DEMO 5: Auto Cleanup - Workspace Maintenance")
    print("=" * 70)
    print()

    print("💡 Scenario: Creating old archived plans and running cleanup")
    print()

    # Create some archived plan files
    for i in range(12):
        plan_file = workspace / f"PLAN_cycle{i}.md"
        plan_file.write_text(f"# Plan for Cycle {i}\n\n- Step 1\n- Step 2\n")
        print(f"  Created: {plan_file.name}")

    print()
    print("Created 12 archived plans (max allowed: 5)")
    print()

    # Run cleanup
    print("Running cleanup...")
    cleanup_result = monitor.cleanup_policy.cleanup(workspace)

    print("  ✅ Cleanup complete")
    print(f"  Archived plans removed: {cleanup_result['archived_plans_removed']}")
    print(f"  Old logs archived: {cleanup_result['old_logs_archived']}")
    print()

    # Verify
    remaining_plans = list(workspace.glob("PLAN_*.md"))
    print(f"Remaining archived plans: {len(remaining_plans)}")
    print()

    # -------------------------------------------------------------------
    # DEMO 6: Integration with Supervisor
    # -------------------------------------------------------------------
    print("=" * 70)
    print("DEMO 6: Integration with Supervisor Pattern")
    print("=" * 70)
    print()

    print("💡 In production, heartbeat integrates with PlannerWorkerHarness:")
    print()
    print("```python")
    print("harness = PlannerWorkerHarness(")
    print('    agent_id="coding-assistant",')
    print("    planner_provider=sonnet_provider,")
    print("    worker_provider=haiku_provider,")
    print("    enable_heartbeat=True,           # Enable heartbeat monitoring")
    print("    heartbeat_check_every=5,         # Check every 5 turns")
    print("    heartbeat_stuck_threshold=10,    # Flag if stuck for 10 turns")
    print("    heartbeat_error_threshold=5,     # Flag if 5 consecutive errors")
    print(")")
    print()
    print("# Heartbeat runs automatically during execution")
    print("result = await harness.run_supervised_cycle(goals=goals)")
    print("```")
    print()

    print("📊 Benefits:")
    print("  • Detects stuck agents early (before wasting resources)")
    print("  • Catches error patterns (permissions, dependencies)")
    print("  • Monitors progress rate (ensures goals being achieved)")
    print("  • Escalates actionable issues (with suggested fixes)")
    print("  • Maintains clean workspace (archives old artifacts)")
    print()

    # -------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------
    print("=" * 70)
    print("HEARTBEAT MONITORING SUMMARY")
    print("=" * 70)
    print()

    print(f"Total heartbeats run: {monitor.heartbeat_count}")
    print(f"Last check at turn: {monitor.last_heartbeat_turn}")
    print()

    print("Health Checks:")
    for check in monitor.checks:
        status = "✅ enabled" if check.enabled else "❌ disabled"
        print(f"  • {check.name}: {status}")
    print()

    print("Escalation Policy:")
    print(f"  • Critical: {'yes' if monitor.escalation_policy.notify_on_critical else 'no'}")
    print(f"  • Warning: {'yes' if monitor.escalation_policy.notify_on_warning else 'no'}")
    print(f"  • Handlers: {len(monitor.escalation_policy.handlers)}")
    print()

    print("Cleanup Policy:")
    print(f"  • Enabled: {'yes' if monitor.cleanup_policy.enabled else 'no'}")
    print(f"  • Archive after: {monitor.cleanup_policy.archive_logs_older_than_days} days")
    print(f"  • Max plans: {monitor.cleanup_policy.max_archived_plans}")
    print()

    # -------------------------------------------------------------------
    # KEY INSIGHTS
    # -------------------------------------------------------------------
    print("=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)
    print()

    print("✅ Heartbeat Monitoring Provides:")
    print()
    print("1. **Autonomous Oversight**")
    print("   - Runs periodically without human intervention")
    print("   - Detects issues before they become critical")
    print("   - Escalates only when user action needed")
    print()
    print("2. **Health Checks**")
    print("   - Stuck detection: Agent not making progress")
    print("   - Error thresholds: Too many consecutive failures")
    print("   - Progress rate: Goals not being achieved fast enough")
    print()
    print("3. **Smart Escalation**")
    print("   - Only escalates actionable issues")
    print("   - Provides context and suggested actions")
    print("   - Configurable severity levels")
    print()
    print("4. **Auto Cleanup**")
    print("   - Archives old logs automatically")
    print("   - Limits archived plans to save space")
    print("   - Keeps workspace organized")
    print()
    print("5. **Integration Ready**")
    print("   - Works seamlessly with supervisor pattern")
    print("   - No manual intervention required")
    print("   - Configurable thresholds per agent type")
    print()

    print("=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())

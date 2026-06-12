"""Autonomous agent execution using Planner-Worker pattern.

Two-phase execution:
1. PLANNER (Sonnet): Creates execution plan from GOALS.md - runs ONCE
2. WORKER (Haiku): Executes each step from plan - runs MANY times

Benefits:
- 93-97% cost savings vs using Sonnet for everything
- More reliable (atomic steps, clear verification)
- Observable (PLAN.md, PROGRESS.md artifacts)
- Resumable (can stop/start, survives crashes)

Usage:
    # First run: Creates plan and starts execution
    python3 run_planner_worker.py

    # Subsequent runs: Resumes from PROGRESS.md
    python3 run_planner_worker.py

    # Force replanning:
    python3 run_planner_worker.py --replan
"""

import argparse
import asyncio
import os
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness


async def main():
    """Run planner-worker autonomous execution."""
    parser = argparse.ArgumentParser(description="Planner-Worker autonomous execution")
    parser.add_argument(
        "--agent-id",
        default="coding-assistant",
        help="Agent ID (default: coding-assistant)",
    )
    parser.add_argument(
        "--replan",
        action="store_true",
        help="Force replanning even if plan exists",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Execute N steps then stop (default: all steps)",
    )
    parser.add_argument(
        "--planner-model",
        default="claude-sonnet-4",
        help="Model for planner (default: claude-sonnet-4)",
    )
    parser.add_argument(
        "--worker-model",
        default="claude-3-haiku-20240307",
        help="Model for worker (default: claude-3-haiku-20240307)",
    )
    args = parser.parse_args()

    print("🤖 Planner-Worker Autonomous Execution")
    print("=" * 70)
    print()

    # Configuration
    agent_id = args.agent_id
    agent_dir = Path.home() / ".forge" / "agents" / agent_id

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set")
        return

    # Load GOALS.md
    goals_path = agent_dir / "GOALS.md"
    if not goals_path.exists():
        print(f"❌ Error: {goals_path} not found")
        print("   Run 'forge onboard' first to create agent workspace")
        return

    print(f"📂 Agent workspace: {agent_dir}")
    print()

    with open(goals_path) as f:
        goals = f.read()

    print("🎯 Goals loaded:")
    print(f"   {len(goals)} chars from GOALS.md")
    print()

    # Create harness
    print("⚙️  Initializing Planner-Worker Harness...")
    print(f"   Planner: {args.planner_model}")
    print(f"   Worker: {args.worker_model}")
    print()

    harness = PlannerWorkerHarness(
        agent_id=agent_id,
        planner_provider=AnthropicProvider(
            api_key=api_key,
            model=args.planner_model,
            max_tokens=4096,
        ),
        worker_provider=AnthropicProvider(
            api_key=api_key,
            model=args.worker_model,
            max_tokens=4096,
        ),
        workspace_dir=agent_dir,
        worker_skills=["filesystem", "git"],
        worker_policy=agent_dir / "security.yaml",
    )

    # -------------------------------------------------------------------
    # PHASE 1: PLANNING (if needed)
    # -------------------------------------------------------------------
    plan_exists = (agent_dir / "PLAN.md").exists()

    if not plan_exists or args.replan:
        print("=" * 70)
        print("PHASE 1: PLANNING")
        print("=" * 70)
        print()

        if args.replan:
            print("🔄 Forcing replan (--replan flag)")
        else:
            print("📝 No plan found, creating new plan...")

        print(f"🧠 Invoking {args.planner_model}...")
        print()

        try:
            plan = await harness.plan(goals=goals, force_replan=args.replan)

            print("✅ Plan created!")
            print(f"   Total steps: {plan.total_steps}")
            print(f"   File: {agent_dir / 'PLAN.md'}")
            print()

            # Show steps
            print("📋 Execution Plan:")
            print("-" * 70)
            for step in plan.steps:
                status = "✓" if step.completed else ("⊘" if step.skipped else " ")
                print(f"  [{status}] {step.number}. {step.description}")
                if step.file_path:
                    print(f"       File: {step.file_path}")
            print("-" * 70)
            print()

        except Exception as e:
            print(f"❌ Planning failed: {e}")
            return
    else:
        print("✅ Plan already exists (use --replan to force replanning)")
        print(f"   File: {agent_dir / 'PLAN.md'}")
        print()

        # Show progress
        progress = harness.get_progress()
        print("📊 Current Progress:")
        print("-" * 70)
        print(f"   Total steps: {progress['total_steps']}")
        print(f"   Completed: {progress['completed']}")
        print(f"   Remaining: {progress['remaining']}")
        print(f"   Progress: {progress['completion_percentage']:.1f}%")
        print("-" * 70)
        print()

    # -------------------------------------------------------------------
    # PHASE 2: EXECUTION
    # -------------------------------------------------------------------
    if harness.is_complete():
        print("🎉 All steps complete!")
        print()
        return

    print("=" * 70)
    print("PHASE 2: EXECUTION")
    print("=" * 70)
    print()

    progress = harness.get_progress()
    steps_to_execute = args.steps if args.steps else progress["remaining"]

    print(f"🏃 Executing {steps_to_execute} step(s) with {args.worker_model}...")
    print()

    executed = 0

    while not harness.is_complete() and (args.steps is None or executed < args.steps):
        progress = harness.get_progress()
        current = progress["current_step"]
        current_desc = progress["current_description"]

        print(f"▶️  Step {current}/{progress['total_steps']}: {current_desc}")
        print("-" * 70)

        try:
            result = await harness.execute_next_step(max_retries=3)

            if result.success:
                print(f"✅ Step {result.step.number} completed")
                print(f"   Tools used: {result.tools_used}")
                print()
                print("   Response:")
                # Show first 200 chars of response
                response_preview = result.response[:200]
                if len(result.response) > 200:
                    response_preview += "..."
                print(f"   {response_preview}")
            else:
                print(f"❌ Step {result.step.number} failed")
                print(f"   Error: {result.error}")

            executed += 1

        except Exception as e:
            print(f"❌ Execution error: {e}")
            break

        print("-" * 70)
        print()

    # Final progress
    progress = harness.get_progress()
    print("=" * 70)
    print("EXECUTION STATUS")
    print("=" * 70)
    print()
    print(f"   Total steps: {progress['total_steps']}")
    print(f"   Completed: {progress['completed']}")
    print(f"   Remaining: {progress['remaining']}")
    print(f"   Progress: {progress['completion_percentage']:.1f}%")
    print()

    if harness.is_complete():
        print("🎉 All steps complete!")
    elif args.steps:
        print(f"⏸️  Paused after {executed} steps (--steps {args.steps})")
        print("   Run again to continue execution")
    else:
        print("⏸️  Execution paused")
        print("   Run again to continue")

    print()
    print("📁 Artifacts:")
    print(f"   {agent_dir / 'PLAN.md'}")
    print(f"   {agent_dir / 'PROGRESS.md'}")
    print(f"   {agent_dir / 'STATE.json'}")
    print()


if __name__ == "__main__":
    asyncio.run(main())

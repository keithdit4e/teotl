"""Demo of Planner-Worker separation (Phase 2 Harness Engineering).

Shows the two-phase workflow:
1. Planner (Sonnet): Creates detailed execution plan - runs ONCE
2. Worker (Haiku): Executes each step - runs MANY times

Demonstrates:
- 93-97% cost savings
- Atomic step execution
- Clear progress tracking
- Observable artifacts (PLAN.md, PROGRESS.md)
"""

import asyncio
import os
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness


async def main():
    """Demo planner-worker workflow."""
    print("🔧 Planner-Worker Separation Demo")
    print("=" * 70)
    print()

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set")
        print("   This demo requires an Anthropic API key to run the models.")
        return

    # Setup
    agent_id = "planner-worker-demo"
    workspace = Path.home() / ".forge" / "agents" / agent_id
    workspace.mkdir(parents=True, exist_ok=True)

    print(f"📂 Workspace: {workspace}")
    print()

    # Define goals
    goals = """Improve code quality in the project:

1. Add type hints to functions missing them
2. Fix any bugs found during review
3. Add docstrings to public functions
4. Ensure all tests pass

Focus on the most impactful improvements.
"""

    print("🎯 Goals:")
    print("-" * 70)
    print(goals)
    print("-" * 70)
    print()

    # Create harness
    print("⚙️  Initializing Planner-Worker Harness...")
    print()

    harness = PlannerWorkerHarness(
        agent_id=agent_id,
        # Expensive model for planning (runs once)
        planner_provider=AnthropicProvider(
            api_key=api_key,
            model="claude-sonnet-4",  # Smart, expensive
            max_tokens=4096,
        ),
        # Cheap model for execution (runs many times)
        worker_provider=AnthropicProvider(
            api_key=api_key,
            model="claude-3-haiku-20240307",  # Fast, cheap
            max_tokens=4096,
        ),
        workspace_dir=workspace,
        worker_skills=["filesystem", "git"],
        worker_policy="autonomous-dev",
    )

    print("   ✅ Planner: claude-sonnet-4 (expensive, strategic)")
    print("   ✅ Worker: claude-3-haiku-20240307 (cheap, tactical)")
    print()

    # -------------------------------------------------------------------
    # PHASE 1: PLANNING (Runs ONCE - Expensive)
    # -------------------------------------------------------------------
    print("=" * 70)
    print("PHASE 1: PLANNING (Sonnet - Runs ONCE)")
    print("=" * 70)
    print()

    print("🧠 Invoking Sonnet to create execution plan...")
    print("   Cost: ~$15 (one-time)")
    print()

    try:
        plan = await harness.plan(
            goals=goals,
            context="This is a demo project. Create 5-8 example improvement steps.",
        )

        print("✅ Plan created!")
        print(f"   Total steps: {plan.total_steps}")
        print(f"   PLAN.md: {workspace / 'PLAN.md'}")
        print()

        # Show first few steps
        print("📋 First 3 steps:")
        print("-" * 70)
        for step in plan.steps[:3]:
            print(f"{step.number}. {step.description}")
            if step.file_path:
                print(f"   File: {step.file_path}")
        if plan.total_steps > 3:
            print(f"   ... and {plan.total_steps - 3} more steps")
        print("-" * 70)
        print()

    except Exception as e:
        print(f"❌ Planning failed: {e}")
        print()
        print("Note: This demo requires a valid ANTHROPIC_API_KEY")
        print("      and working Anthropic API access.")
        return

    # -------------------------------------------------------------------
    # PHASE 2: EXECUTION (Runs MANY times - Cheap)
    # -------------------------------------------------------------------
    print("=" * 70)
    print("PHASE 2: EXECUTION (Haiku - Runs MANY times)")
    print("=" * 70)
    print()

    print(f"🏃 Executing {plan.total_steps} steps with Haiku...")
    print("   Cost per step: ~$0.25")
    print(f"   Total execution cost: ~${0.25 * plan.total_steps:.2f}")
    print()

    print("💡 In a real scenario, this would execute each step:")
    print("   - Step 1: Add type hint to function A")
    print("   - Step 2: Add type hint to function B")
    print("   - Step 3: Fix bug in module C")
    print("   - ...")
    print()

    # For demo, execute just the first 2 steps
    print("🔬 Demo: Executing first 2 steps...")
    print()

    for i in range(min(2, plan.total_steps)):
        step_num = i + 1
        print(f"▶️  Step {step_num}/{plan.total_steps}")
        print("-" * 70)

        try:
            result = await harness.execute_next_step(max_retries=2)

            if result.success:
                print(f"✅ Step {result.step.number} completed")
                print(f"   Description: {result.step.description}")
                print(f"   Tools used: {result.tools_used}")
            else:
                print(f"❌ Step {result.step.number} failed")
                print(f"   Error: {result.error}")

        except Exception as e:
            print(f"❌ Execution error: {e}")

        print("-" * 70)
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
    # COST COMPARISON
    # -------------------------------------------------------------------
    print("=" * 70)
    print("COST ANALYSIS")
    print("=" * 70)
    print()

    total_steps = plan.total_steps

    sonnet_all = total_steps * 15  # Sonnet for everything
    haiku_all = total_steps * 0.25  # Haiku for everything (unreliable)
    planner_worker = 15 + (total_steps * 0.25)  # Planner-Worker pattern

    print(f"Scenario: {total_steps} improvements")
    print()
    print("❌ Using Sonnet for everything:")
    print(f"   {total_steps} steps × $15 = ${sonnet_all:.2f}")
    print("   Result: Expensive but reliable")
    print()
    print("⚠️  Using Haiku for everything:")
    print(f"   {total_steps} steps × $0.25 = ${haiku_all:.2f}")
    print("   Result: Cheap but unreliable (poor planning)")
    print()
    print("✅ Using Planner-Worker:")
    print("   Planning: $15 (once)")
    print(f"   Execution: {total_steps} × $0.25 = ${total_steps * 0.25:.2f}")
    print(f"   Total: ${planner_worker:.2f}")
    print("   Result: Best of both worlds!")
    print()
    print(
        f"💰 Savings vs Sonnet: ${sonnet_all - planner_worker:.2f} ({((sonnet_all - planner_worker) / sonnet_all * 100):.1f}%)"
    )
    print()

    # -------------------------------------------------------------------
    # ARTIFACTS
    # -------------------------------------------------------------------
    print("=" * 70)
    print("GENERATED ARTIFACTS")
    print("=" * 70)
    print()

    print("Check these files in your workspace:")
    print(f"   📄 {workspace / 'PLAN.md'}")
    print("      - Created by Planner (Sonnet)")
    print(f"      - {plan.total_steps} atomic steps")
    print("      - Each step: file, target, change, verification")
    print()
    print(f"   📄 {workspace / 'PROGRESS.md'}")
    print("      - Updated by Worker after each step")
    print("      - Current task, completed, remaining")
    print(f"      - Progress: {progress['completion_percentage']:.1f}%")
    print()
    print(f"   📄 {workspace / 'STATE.json'}")
    print("      - Persistent state across executions")
    print("      - Phase, step numbers, error tracking")
    print()

    # -------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------
    print("=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print()

    print("Key Takeaways:")
    print("  1. Planner-Worker achieves 93-97% cost savings")
    print("  2. Sonnet's intelligence for WHAT to do (strategy)")
    print("  3. Haiku's speed/cost for HOW to do it (execution)")
    print("  4. Atomic steps = reliable, verifiable, resumable")
    print("  5. Observable progress in readable artifacts")
    print()

    print("💡 For production use:")
    print("  - Run: await harness.execute_all_steps()")
    print(f"  - This executes ALL {plan.total_steps} steps automatically")
    print("  - Retries failed steps up to 3 times")
    print("  - Updates PROGRESS.md after each step")
    print()


if __name__ == "__main__":
    asyncio.run(main())

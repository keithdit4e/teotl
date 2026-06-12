"""Demo of Supervised Execution (Phase 3: Evaluator + Supervisor Loop).

Shows the intelligent closed-loop system:
1. PLANNER (Sonnet): Creates execution plan - runs at start of each cycle
2. WORKER (Haiku): Executes all steps - runs many times per cycle
3. EVALUATOR (Sonnet): Assesses if goals achieved - runs at end of each cycle
   - If COMPLETE → Generate report for user
   - If CONTINUE → Plan next cycle with refined goals

Demonstrates:
- Autonomous goal achievement (no user intervention needed)
- Intelligent adaptation (evaluator finds issues, planner addresses them)
- Cost-effective (still 85%+ savings vs Sonnet-only)
- Observable (PLAN.md, PROGRESS.md, evaluation reports)
"""

import asyncio
import os
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness


async def main():
    """Demo supervised execution."""
    print("🤖 Supervised Execution Demo")
    print("=" * 70)
    print()

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set")
        print("   This demo requires an Anthropic API key.")
        return

    # Setup
    agent_id = "supervisor-demo"
    workspace = Path.home() / ".forge" / "agents" / agent_id
    workspace.mkdir(parents=True, exist_ok=True)

    print(f"📂 Workspace: {workspace}")
    print()

    # Define goals
    goals = """Improve code quality in the project:

1. Add type hints to functions missing them
2. Fix any bugs found during review
3. Ensure all tests pass
4. Add docstrings where needed

The code should be production-ready when complete.
"""

    print("🎯 Goals:")
    print("-" * 70)
    print(goals)
    print("-" * 70)
    print()

    # Create harness
    print("⚙️  Initializing Supervised Harness...")
    print()

    harness = PlannerWorkerHarness(
        agent_id=agent_id,
        # Strategic model (Planner + Evaluator)
        planner_provider=AnthropicProvider(
            api_key=api_key,
            model="claude-sonnet-4",
            max_tokens=4096,
        ),
        # Tactical model (Worker)
        worker_provider=AnthropicProvider(
            api_key=api_key,
            model="claude-3-haiku-20240307",
            max_tokens=4096,
        ),
        workspace_dir=workspace,
        worker_skills=["filesystem", "git"],
        worker_policy="autonomous-dev",
    )

    print("   ✅ Planner: claude-sonnet-4 (strategic)")
    print("   ✅ Worker: claude-3-haiku-20240307 (tactical)")
    print("   ✅ Evaluator: claude-sonnet-4 (strategic)")
    print()

    # -------------------------------------------------------------------
    # RUN SUPERVISED CYCLE
    # -------------------------------------------------------------------
    print("=" * 70)
    print("SUPERVISED EXECUTION")
    print("=" * 70)
    print()

    print("🚀 Running autonomous cycles...")
    print("   Max cycles: 3")
    print("   The system will work until goals are achieved or max cycles reached")
    print()

    print("💡 Expected flow:")
    print("   Cycle 1:")
    print("     → Planner creates plan (e.g., 10 improvements)")
    print("     → Worker executes all 10 steps")
    print("     → Evaluator: 'Good! But found 3 bugs during review'")
    print()
    print("   Cycle 2:")
    print("     → Planner creates plan for 3 bug fixes")
    print("     → Worker executes fixes")
    print("     → Evaluator: 'Perfect! Tests pass. COMPLETE ✅'")
    print()
    print("-" * 70)
    print()

    try:
        result = await harness.run_supervised_cycle(
            goals=goals,
            max_cycles=3,
            max_retries_per_step=2,
            context="This is a demo project. Create example improvements.",
        )

        print()
        print("=" * 70)
        print("EXECUTION COMPLETE")
        print("=" * 70)
        print()

        if result.complete:
            print("🎉 Goals Achieved!")
            print(f"   Cycles completed: {result.cycles_completed}")
            print(f"   Confidence: {result.final_evaluation.confidence * 100:.0f}%")
            print()

            print("=" * 70)
            print("COMPLETION REPORT")
            print("=" * 70)
            print()
            print(result.completion_report)
            print()

        else:
            print("⚠️  Execution Stopped")
            print(f"   Cycles completed: {result.cycles_completed}")
            print(f"   Reason: {result.reason}")
            print()

            print("What was done:")
            for item in result.final_evaluation.what_was_done:
                print(f"  ✅ {item}")
            print()

            if result.final_evaluation.what_remains:
                print("What remains:")
                for item in result.final_evaluation.what_remains:
                    print(f"  ⏳ {item}")
                print()

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback

        traceback.print_exc()
        return

    # -------------------------------------------------------------------
    # COST ANALYSIS
    # -------------------------------------------------------------------
    print("=" * 70)
    print("COST ANALYSIS (Estimated)")
    print("=" * 70)
    print()

    cycles = result.cycles_completed

    # Estimate steps per cycle (assume 8 average)
    steps_per_cycle = 8
    total_steps = cycles * steps_per_cycle

    planning_cost = cycles * 15  # $15 per planning session
    execution_cost = total_steps * 0.25  # $0.25 per step
    evaluation_cost = cycles * 10  # $10 per evaluation

    total_cost = planning_cost + execution_cost + evaluation_cost

    sonnet_only = total_steps * 15  # If using Sonnet for everything

    print(f"Cycles: {cycles}")
    print(f"Estimated total steps: {total_steps}")
    print()
    print("💰 Cost Breakdown:")
    print(f"   Planning:   {cycles} × $15 = ${planning_cost:.2f}")
    print(f"   Execution:  {total_steps} × $0.25 = ${execution_cost:.2f}")
    print(f"   Evaluation: {cycles} × $10 = ${evaluation_cost:.2f}")
    print("   ─────────────────────────────")
    print(f"   Total:      ${total_cost:.2f}")
    print()
    print(f"vs Sonnet-only: ${sonnet_only:.2f}")
    print(
        f"Savings: ${sonnet_only - total_cost:.2f} ({((sonnet_only - total_cost) / sonnet_only * 100):.0f}%)"
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
    print()
    print(f"   📄 {workspace / 'PLAN.md'}")
    print("      - Latest execution plan")
    print("      - Archived plans from previous cycles")
    print()
    print(f"   📄 {workspace / 'PROGRESS.md'}")
    print("      - Current progress")
    print("      - Completed tasks")
    print()
    print(f"   📄 {workspace / 'STATE.json'}")
    print("      - Current cycle, phase, evaluation results")
    print()

    # -------------------------------------------------------------------
    # KEY INSIGHTS
    # -------------------------------------------------------------------
    print("=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)
    print()

    print("✅ The Supervisor Pattern Provides:")
    print()
    print("1. **Autonomous Goal Achievement**")
    print("   - User provides goals once")
    print("   - System works through multiple cycles automatically")
    print("   - Only reports when truly complete")
    print()
    print("2. **Intelligent Adaptation**")
    print("   - Evaluator finds issues during review")
    print("   - Planner creates targeted fixes")
    print("   - Worker executes precisely")
    print()
    print("3. **Cost-Effective Intelligence**")
    print("   - Sonnet for strategy (planning + evaluation)")
    print("   - Haiku for tactics (execution)")
    print("   - 85%+ savings vs Sonnet-only")
    print()
    print("4. **Quality Assurance**")
    print("   - Evaluator verifies goals met")
    print("   - Tests must pass to complete")
    print("   - High confidence threshold (>0.8)")
    print()

    print("=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())

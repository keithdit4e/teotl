"""Autonomous agent execution using Supervised pattern.

Intelligent closed-loop system:
1. PLANNER (Sonnet): Creates execution plan
2. WORKER (Haiku): Executes all steps
3. EVALUATOR (Sonnet): Assesses if goals achieved
4. If not complete: Loop back to planning with refined goals
5. If complete: Generate completion report

The system autonomously works through multiple cycles until goals are achieved.

Usage:
    # Run supervised execution
    python3 run_supervised.py

    # Limit to 2 cycles
    python3 run_supervised.py --max-cycles 2

    # Use different models
    python3 run_supervised.py --strategic-model claude-opus-4 --tactical-model claude-3-haiku-20240307
"""

import argparse
import asyncio
import os
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness


async def main():
    """Run supervised autonomous execution."""
    parser = argparse.ArgumentParser(description="Supervised autonomous execution")
    parser.add_argument(
        "--agent-id",
        default="coding-assistant",
        help="Agent ID (default: coding-assistant)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=3,
        help="Maximum execution cycles (default: 3)",
    )
    parser.add_argument(
        "--strategic-model",
        default="claude-sonnet-4",
        help="Model for planner and evaluator (default: claude-sonnet-4)",
    )
    parser.add_argument(
        "--tactical-model",
        default="claude-3-haiku-20240307",
        help="Model for worker (default: claude-3-haiku-20240307)",
    )
    args = parser.parse_args()

    print("🤖 Supervised Autonomous Execution")
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
    print("⚙️  Initializing Supervised Harness...")
    print(f"   Strategic model: {args.strategic_model} (planner + evaluator)")
    print(f"   Tactical model: {args.tactical_model} (worker)")
    print(f"   Max cycles: {args.max_cycles}")
    print()

    harness = PlannerWorkerHarness(
        agent_id=agent_id,
        planner_provider=AnthropicProvider(
            api_key=api_key,
            model=args.strategic_model,
            max_tokens=4096,
        ),
        worker_provider=AnthropicProvider(
            api_key=api_key,
            model=args.tactical_model,
            max_tokens=4096,
        ),
        workspace_dir=agent_dir,
        worker_skills=["filesystem", "git"],
        worker_policy=agent_dir / "security.yaml",
    )

    # -------------------------------------------------------------------
    # RUN SUPERVISED EXECUTION
    # -------------------------------------------------------------------
    print("=" * 70)
    print("SUPERVISED EXECUTION")
    print("=" * 70)
    print()

    print("🚀 Starting autonomous cycles...")
    print("   The system will work until goals are achieved or max cycles reached")
    print()

    try:
        result = await harness.run_supervised_cycle(
            goals=goals,
            max_cycles=args.max_cycles,
            max_retries_per_step=3,
        )

        print()
        print("=" * 70)
        print("EXECUTION COMPLETE")
        print("=" * 70)
        print()

        if result.complete:
            print("🎉 Goals Achieved!")
            print(f"   Cycles: {result.cycles_completed}")
            print(f"   Confidence: {result.final_evaluation.confidence * 100:.0f}%")
            print(f"   Tests: {result.final_evaluation.test_status}")
            print()

            # Display completion report
            print("=" * 70)
            print("COMPLETION REPORT")
            print("=" * 70)
            print()
            print(result.completion_report)
            print()

            # Save report to file
            report_path = agent_dir / "COMPLETION_REPORT.md"
            report_path.write_text(result.completion_report)
            print(f"📄 Report saved to: {report_path}")
            print()

        else:
            print("⚠️  Execution Stopped")
            print(f"   Cycles: {result.cycles_completed}")
            print(f"   Reason: {result.reason}")
            print()

            print("📊 Final Evaluation:")
            print("-" * 70)
            print(f"   Confidence: {result.final_evaluation.confidence * 100:.0f}%")
            print(f"   Tests: {result.final_evaluation.test_status}")
            print()

            print("What was accomplished:")
            for item in result.final_evaluation.what_was_done:
                print(f"  ✅ {item}")
            print()

            if result.final_evaluation.what_remains:
                print("What remains:")
                for item in result.final_evaluation.what_remains:
                    print(f"  ⏳ {item}")
                print()

                if result.final_evaluation.continuation_goals:
                    print("Next steps:")
                    print(f"  {result.final_evaluation.continuation_goals}")
                    print()

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback

        traceback.print_exc()
        return

    # -------------------------------------------------------------------
    # ARTIFACTS
    # -------------------------------------------------------------------
    print("=" * 70)
    print("GENERATED ARTIFACTS")
    print("=" * 70)
    print()

    print("Check these files in your workspace:")
    print(f"   📄 {agent_dir / 'PLAN.md'}")
    print(f"   📄 {agent_dir / 'PROGRESS.md'}")
    print(f"   📄 {agent_dir / 'STATE.json'}")
    print(f"   📄 {agent_dir / 'DECISION_LOG.md'}")
    if result.complete:
        print(f"   📄 {agent_dir / 'COMPLETION_REPORT.md'}")
    print()


if __name__ == "__main__":
    asyncio.run(main())

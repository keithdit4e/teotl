"""Demo of Advanced Context Janitor (Phase 4).

Shows LLM-powered decision extraction and smart compaction:
1. Token size tracking across turns
2. LLM-powered extraction (vs keyword matching)
3. Smart compaction when size limits exceeded
4. Integration with supervisor pattern

Demonstrates:
- Extracting decisions using cheap model (Haiku)
- Preserving important context while discarding noise
- Automatic compaction based on size and turns
- Context metrics tracking
"""

import asyncio
import os
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import AdvancedContextJanitor


async def main():
    """Demo advanced context janitor."""
    print("🧹 Advanced Context Janitor Demo")
    print("=" * 70)
    print()

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set")
        print("   This demo requires an Anthropic API key for LLM extraction.")
        return

    # Setup
    agent_id = "janitor-demo"
    workspace = Path.home() / ".forge" / "agents" / agent_id
    workspace.mkdir(parents=True, exist_ok=True)

    print(f"📂 Workspace: {workspace}")
    print()

    # -------------------------------------------------------------------
    # DEMO 1: Keyword vs LLM Extraction
    # -------------------------------------------------------------------
    print("=" * 70)
    print("DEMO 1: Keyword vs LLM Extraction")
    print("=" * 70)
    print()

    # Create janitor with LLM extraction
    janitor_llm = AdvancedContextJanitor(
        agent_id=agent_id,
        provider=AnthropicProvider(
            api_key=api_key,
            model="claude-3-haiku-20240307",
        ),
        workspace_dir=workspace,
        compact_every=5,
        max_context_tokens=10000,
        use_llm_extraction=True,
    )

    print("✅ Created janitor with LLM-powered extraction")
    print("   Model: claude-3-haiku-20240307")
    print("   Compact every: 5 turns")
    print("   Max tokens: 10,000")
    print()

    # Simulate agent responses with varying decision clarity
    print("📝 Simulating agent responses...")
    print()

    responses = [
        # Turn 1: Clear decision with "I decided"
        """I read the utils.py file and found that the parse_config function is missing
type hints. I decided to add type hints because it will improve code quality and help
catch bugs early. I changed the signature from `def parse_config(data)` to
`def parse_config(data: dict[str, Any]) -> Config`. All tests pass after this change.""",
        # Turn 2: Noisy response with tool output
        """I'm now reading the file...
<file_contents>
def process_data(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
</file_contents>

I'll refactor this to use a list comprehension for better performance.

<edit>
def process_data(items):
    return [item * 2 for item in items]
</edit>

Done! Changed the function to use list comprehension.""",
        # Turn 3: Bug fix with reasoning
        """Fixed the null pointer error in the authentication module. The issue was that
we weren't checking if the user object existed before accessing user.email. I added a
null check because this was causing crashes in production. The fix prevents the error
and logs a warning instead.""",
        # Turn 4: Process description (mostly noise)
        """I'm checking the test results now... Running pytest... The tests are passing...
Looking at the coverage report... Coverage is at 87%... That's good... Checking if there
are any warnings... No warnings found... Everything looks good. Moving on to the next task.""",
        # Turn 5: Multiple decisions
        """I refactored the database module for better maintainability. First, I extracted
the connection logic into a separate ConnectionPool class because it was duplicated across
three files. Then I added connection retry logic since the database sometimes has transient
failures. Finally, I updated all the imports across the codebase to use the new module.""",
    ]

    # Process turns
    for i, response in enumerate(responses, 1):
        print(f"{'─' * 70}")
        print(f"Turn {i}:")
        print(f"{'─' * 70}")
        print()

        # Show abbreviated response
        preview = response[:150].replace("\n", " ") + "..."
        print(f"Response: {preview}")
        print()

        # Extract decisions
        await janitor_llm.after_turn_async(
            agent_response=response,
            context_snapshot=None,
        )

        # Show what was extracted
        if janitor_llm.decision_buffer:
            latest = janitor_llm.decision_buffer[-1]
            print(f"✅ Extracted: {latest.decision}")
        else:
            print("⚠️  No decisions extracted")

        print()

        # Show metrics
        metrics = janitor_llm.get_metrics()
        print(
            f"📊 Metrics: {metrics.turn_count} turns, "
            f"~{metrics.estimated_tokens} tokens, "
            f"{metrics.decisions_extracted} decisions"
        )
        print()

    # Show compaction status
    print("=" * 70)
    print("COMPACTION STATUS")
    print("=" * 70)
    print()
    print(janitor_llm.get_compaction_summary())
    print()

    # -------------------------------------------------------------------
    # DEMO 2: Context Size Tracking and Smart Compaction
    # -------------------------------------------------------------------
    print("=" * 70)
    print("DEMO 2: Context Size Tracking and Smart Compaction")
    print("=" * 70)
    print()

    # Create janitor with low token limit to trigger compaction
    janitor_compact = AdvancedContextJanitor(
        agent_id=f"{agent_id}-compact",
        provider=AnthropicProvider(
            api_key=api_key,
            model="claude-3-haiku-20240307",
        ),
        workspace_dir=workspace,
        compact_every=3,  # Compact every 3 turns
        max_context_tokens=500,  # Very low limit to trigger size-based compaction
        use_llm_extraction=True,
    )

    print("✅ Created janitor with low token limit")
    print("   Max tokens: 500 (will trigger size-based compaction)")
    print("   Compact every: 3 turns")
    print()

    # Simulate large responses
    large_responses = [
        "I analyzed the entire authentication module and found several issues. " * 20,
        "I refactored the database layer to improve performance and reliability. " * 20,
        "I updated all the API endpoints to use the new validation framework. " * 20,
        "I fixed bugs in the error handling across multiple modules. " * 20,
    ]

    print("📝 Simulating large responses to trigger compaction...")
    print()

    for i, response in enumerate(large_responses, 1):
        print(f"Turn {i}: Processing ~{len(response)} chars (~{len(response) // 4} tokens)")

        await janitor_compact.after_turn_async(
            agent_response=response,
            context_snapshot=response * i,  # Simulated growing context
        )

        metrics = janitor_compact.get_metrics()
        print(
            f"  → Tokens: {metrics.estimated_tokens}, "
            f"Decisions: {metrics.decisions_extracted}, "
            f"Compactions: {metrics.compactions_performed}"
        )

        if janitor_compact.should_compact():
            print("  ⚠️  Compaction recommended!")

        print()

    # Final metrics
    print("=" * 70)
    print("FINAL METRICS")
    print("=" * 70)
    print()

    metrics = janitor_compact.get_metrics()
    print(f"Total turns: {metrics.turn_count}")
    print(f"Estimated tokens: {metrics.estimated_tokens}")
    print(f"Decisions extracted: {metrics.decisions_extracted}")
    print(f"Compactions performed: {metrics.compactions_performed}")
    print(f"Turns since last compaction: {metrics.turns_since_compaction}")
    print()

    # -------------------------------------------------------------------
    # DEMO 3: Integration with Supervisor Pattern
    # -------------------------------------------------------------------
    print("=" * 70)
    print("DEMO 3: Integration with Supervisor Pattern")
    print("=" * 70)
    print()

    print("💡 In production, the janitor integrates with PlannerWorkerHarness:")
    print()
    print("```python")
    print("harness = PlannerWorkerHarness(")
    print('    agent_id="coding-assistant",')
    print("    planner_provider=sonnet_provider,")
    print("    worker_provider=haiku_provider,")
    print("    enable_janitor=True,        # Enable advanced janitor")
    print("    janitor_compact_every=5,    # Compact every 5 worker steps")
    print("    janitor_max_tokens=10000,   # Force compact at 10K tokens")
    print(")")
    print()
    print("# Janitor automatically tracks worker responses")
    print("result = await harness.run_supervised_cycle(goals=goals)")
    print("```")
    print()

    print("📊 Benefits:")
    print("  • Prevents context bloat during long execution cycles")
    print("  • Uses cheap model (Haiku) for decision extraction")
    print("  • Preserves important decisions in DECISION_LOG.md")
    print("  • Enables context resets without losing state")
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
    print(f"   📄 {workspace / 'DECISION_LOG.md'}")
    print("      - Compacted decision history")
    print("      - Extracted by LLM (not just keywords)")
    print()

    # -------------------------------------------------------------------
    # KEY INSIGHTS
    # -------------------------------------------------------------------
    print("=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)
    print()

    print("✅ Advanced Context Janitor Provides:")
    print()
    print("1. **LLM-Powered Extraction**")
    print("   - Uses cheap model (Haiku ~$0.01) to extract decisions")
    print("   - Smarter than keyword matching")
    print("   - Focuses on technical decisions, ignores noise")
    print()
    print("2. **Context Size Tracking**")
    print("   - Token estimation (chars / 4)")
    print("   - Compaction based on size OR turns")
    print("   - Prevents context overflow")
    print()
    print("3. **Smart Compaction**")
    print("   - Preserves important context")
    print("   - Discards tool output and noise")
    print("   - Logs decisions to DECISION_LOG.md")
    print()
    print("4. **Supervisor Integration**")
    print("   - Tracks worker responses automatically")
    print("   - Enables long-running cycles")
    print("   - Maintains context <10K tokens")
    print()

    print("=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())

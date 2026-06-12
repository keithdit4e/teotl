"""Simple autonomous agent execution - GOALS-based with Harness Engineering.

This script runs one execution cycle of an autonomous agent with harness primitives:
1. Reads GOALS.md
2. Loads artifacts (PROGRESS.md, STATE.json, DECISION_LOG.md)
3. Agent decides what to do next based on goals + artifacts
4. Executes ONE atomic task
5. Updates artifacts with progress
6. Reports results

Harness features:
- PROGRESS.md: Tracks current task, completed tasks, remaining tasks
- STATE.json: Persists variables, flags, checkpoints
- DECISION_LOG.md: Logs key decisions, compacts context every 10 turns
- Artifact-driven: Agent reads state from files, not just conversation

Run this periodically (e.g., via cron) or integrate with HeartbeatDaemon.

Usage:
    python3 run_autonomous_agent.py
"""

import asyncio
import os
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import HarnessAgent


async def main():
    """Run one autonomous execution cycle."""
    print("🤖 Autonomous Agent Execution")
    print("=" * 60)

    # Configuration
    agent_id = "coding-assistant"
    agent_dir = Path.home() / ".forge" / "agents" / agent_id

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set")
        return

    # Load workspace files
    goals_path = agent_dir / "GOALS.md"
    instructions_path = agent_dir / "INSTRUCTIONS.md"
    personality_path = agent_dir / "PERSONALITY.md"

    if not goals_path.exists():
        print(f"❌ Error: {goals_path} not found")
        print("   Run 'forge onboard' first to create agent workspace")
        return

    print(f"📂 Agent workspace: {agent_dir}")
    print()

    # Read workspace files
    print("📖 Loading workspace files...")

    with open(goals_path) as f:
        goals = f.read()
    print(f"   ✅ GOALS.md ({len(goals)} chars)")

    instructions = ""
    if instructions_path.exists():
        with open(instructions_path) as f:
            instructions = f.read()
        print(f"   ✅ INSTRUCTIONS.md ({len(instructions)} chars)")

    personality = ""
    if personality_path.exists():
        with open(personality_path) as f:
            personality = f.read()
        print(f"   ✅ PERSONALITY.md ({len(personality)} chars)")

    print()

    # Combine into system prompt
    system_prompt_parts = []
    if personality:
        system_prompt_parts.append(personality)
    if instructions:
        system_prompt_parts.append(instructions)

    system_prompt = "\n\n---\n\n".join(system_prompt_parts)

    # Create harness-enabled agent
    print("🤖 Creating harness-enabled agent...")
    print("   Model: claude-3-haiku-20240307")
    print(f"   Security: {agent_dir / 'security.yaml'}")
    print("   Harness: PROGRESS.md, STATE.json, DECISION_LOG.md")
    print()

    agent = HarnessAgent(
        agent_id=agent_id,
        provider=AnthropicProvider(
            api_key=api_key, model="claude-3-haiku-20240307", max_tokens=4096
        ),
        instructions=system_prompt,
        skills=["filesystem", "git"],
        policy=agent_dir / "security.yaml",
        workspace_dir=agent_dir,
        # Harness options
        enable_progress=True,
        enable_state=True,
        enable_janitor=True,
        compact_every=10,
        load_artifacts_in_prompt=True,  # Auto-inject artifacts into prompt
    )

    # Check and display artifact status
    print("📋 Artifact Status:")
    if agent.progress and agent.progress.exists():
        state = agent.progress.read()
        print("   ✅ PROGRESS.md exists")
        print(f"      Current: {state.current or 'Starting...'}")
        print(f"      Completed: {len(state.completed)}")
        print(f"      Remaining: {len(state.remaining)}")
        print(f"      Progress: {state.completion_percentage:.1f}%")
    else:
        print("   ⚪ PROGRESS.md not yet created (will be created after first task)")

    if agent.state and agent.state.exists():
        state_data = agent.state.load()
        print(f"   ✅ STATE.json exists ({len(state_data)} variables)")
    else:
        print("   ⚪ STATE.json not yet created")

    if agent.janitor and agent.janitor.decision_log_path.exists():
        print(f"   ✅ DECISION_LOG.md exists (turn {agent.janitor.get_turn_count()})")
    else:
        print("   ⚪ DECISION_LOG.md not yet created")

    print()

    # Create execution prompt
    # Note: Artifacts will be auto-injected by HarnessAgent
    prompt = f"""Read your GOALS and decide on the next action to take.

{goals}

Choose ONE improvement to work on right now. Follow the execution specification in your instructions.
"""

    # Execute
    print("🚀 Starting execution...")
    print("=" * 60)
    print()

    try:
        response = await agent.run(prompt)

        print()
        print("=" * 60)
        print("✅ Execution Complete")
        print("=" * 60)
        print()
        print("📊 Agent Response:")
        print("-" * 60)
        print(response.text)
        print("-" * 60)
        print()
        print(f"🔧 Tools used: {len(response.tool_calls_made) if response.tool_calls_made else 0}")
        print()

        # Display harness status after execution
        print("📋 Harness Status:")
        if agent.janitor:
            print(f"   Turn count: {agent.janitor.get_turn_count()}")
            print(f"   Pending decisions: {len(agent.janitor.get_pending_decisions())}")
            if agent.janitor.should_reset_context():
                print(
                    f"   ⚠️  Context compaction recommended (every {agent.janitor.compact_every} turns)"
                )
        print()
        print("💡 Tip: Check these files in your workspace:")
        print(f"   - {agent_dir / 'PROGRESS.md'} (progress tracking)")
        print(f"   - {agent_dir / 'STATE.json'} (persistent state)")
        print(f"   - {agent_dir / 'DECISION_LOG.md'} (decision history)")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Execution Failed")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        return

    print("✅ Execution cycle complete")
    print()


if __name__ == "__main__":
    asyncio.run(main())

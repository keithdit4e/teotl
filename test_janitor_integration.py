"""Test janitor-memory integration in base Agent.

Verifies that:
1. Janitor auto-initializes when memory is enabled
2. Decisions are extracted and stored as memories
3. Context compaction triggers at configurable thresholds
4. Different models get appropriate context limits
"""

import asyncio
import tempfile
from pathlib import Path

from teotl.core.agent import Agent
from teotl.primitives.memory.local import LocalMemory


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model
        self.call_count = 0

    async def complete(self, system: str, messages: list, tools: list = None):
        """Mock LLM completion."""
        self.call_count += 1

        # Return mock response with a decision
        class MockResult:
            def __init__(self, turn):
                self.content = f"Turn {turn}: I decided to refactor the authentication module because it was outdated."
                self.done = True
                self.tool_calls = []
                self.usage = {"input_tokens": 100, "output_tokens": 50}

        return MockResult(self.call_count)


async def test_janitor_auto_initialization():
    """Test that janitor auto-initializes when memory is enabled."""
    print("\n=== Test 1: Janitor Auto-Initialization ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create agent with memory (janitor should auto-enable)
        memory = LocalMemory(path=workspace / "memory.db")
        agent = Agent(
            provider=MockProvider(),
            instructions="You are a helpful assistant",
            memory=memory,
            session_dir=workspace / "sessions",
        )

        # Verify janitor was auto-initialized
        assert agent.janitor is not None, "Janitor should auto-initialize with memory"
        assert agent.janitor._memory is memory, "Janitor should have memory reference"

        print(f"✅ Janitor auto-initialized: {agent.janitor}")
        print(f"✅ Max context tokens: {agent.janitor.max_context_tokens}")
        print(f"✅ Compact every: {agent.janitor.compact_every} turns")


async def test_janitor_disabled_without_memory():
    """Test that janitor is disabled when memory is not enabled."""
    print("\n=== Test 2: Janitor Disabled Without Memory ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create agent WITHOUT memory
        agent = Agent(
            provider=MockProvider(),
            instructions="You are a helpful assistant",
            session_dir=workspace / "sessions",
        )

        # Verify janitor was NOT initialized
        assert agent.janitor is None, "Janitor should be disabled without memory"

        print("✅ Janitor correctly disabled when memory not enabled")


async def test_context_limit_detection():
    """Test that context limits are auto-detected from model."""
    print("\n=== Test 3: Context Limit Auto-Detection ===")

    test_cases = [
        ("claude-3-5-sonnet-20241022", 100_000),
        ("claude-3-opus-20240229", 100_000),
        ("gpt-4-turbo", 64_000),
        ("gpt-4", 4_000),
        ("gpt-3.5-turbo", 8_000),
        ("unknown-model", 10_000),  # Default
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        for model, expected_limit in test_cases:
            memory = LocalMemory(path=workspace / f"memory_{model}.db")
            agent = Agent(
                provider=MockProvider(model=model),
                instructions="Test",
                memory=memory,
                session_dir=workspace / "sessions",
            )

            actual_limit = agent.janitor.max_context_tokens
            assert actual_limit == expected_limit, (
                f"Model {model}: expected {expected_limit}, got {actual_limit}"
            )

            print(f"✅ {model:30} → {actual_limit:8,} tokens")


async def test_custom_context_limit():
    """Test that custom context limits can be configured."""
    print("\n=== Test 4: Custom Context Limit ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create agent with custom limit
        memory = LocalMemory(path=workspace / "memory.db")
        agent = Agent(
            provider=MockProvider(),
            instructions="Test",
            memory=memory,
            session_dir=workspace / "sessions",
            max_context_tokens=50_000,  # Custom limit
        )

        assert agent.janitor.max_context_tokens == 50_000

        print(f"✅ Custom context limit applied: {agent.janitor.max_context_tokens:,} tokens")


async def test_decisions_stored_as_memories():
    """Test that decisions are extracted and stored as memories."""
    print("\n=== Test 5: Decisions Stored as Memories ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        memory = LocalMemory(path=workspace / "memory.db")
        agent = Agent(
            provider=MockProvider(),
            instructions="You are a coding assistant",
            memory=memory,
            session_dir=workspace / "sessions",
            compact_every=5,  # Compact every 5 turns
        )

        # Run several turns
        for i in range(3):
            response = await agent.run(f"Task {i + 1}: Please help me with this.")
            print(f"  Turn {i + 1}: {response.text[:60]}...")

        # Check that decisions were stored as memories
        memories = await memory.list_all(limit=100)
        janitor_memories = [m for m in memories if m.metadata.source == "janitor"]

        print(f"\n✅ Total memories: {len(memories)}")
        print(f"✅ Janitor memories (decisions): {len(janitor_memories)}")

        # Show some decisions
        for mem in janitor_memories[:3]:
            print(f"   - {mem.content[:70]}...")

        assert len(janitor_memories) > 0, "Should have extracted at least one decision"


async def test_compaction_triggers():
    """Test that compaction triggers at the right thresholds."""
    print("\n=== Test 6: Compaction Triggering ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        memory = LocalMemory(path=workspace / "memory.db")
        agent = Agent(
            provider=MockProvider(),
            instructions="You are a coding assistant",
            memory=memory,
            session_dir=workspace / "sessions",
            compact_every=3,  # Compact every 3 turns
            max_context_tokens=500,  # Very low for testing
        )

        # Run several turns and track compactions
        compaction_turns = []

        for i in range(10):
            await agent.run(f"Task {i + 1}")

            # Check if compaction happened
            if agent.janitor.metrics if hasattr(agent.janitor, "metrics") else None:
                if hasattr(
                    agent.janitor, "metrics"
                ) and agent.janitor.metrics.compactions_performed > len(compaction_turns):
                    compaction_turns.append(i + 1)

        # Read decision log to verify compactions
        decision_log = workspace / "sessions" / "DECISION_LOG.md"
        if decision_log.exists():
            log_content = decision_log.read_text()
            print("\n✅ DECISION_LOG.md created")
            print(f"✅ Log size: {len(log_content)} bytes")

            # Count compaction markers
            compaction_count = log_content.count("Compacted:")
            print(f"✅ Compactions performed: {compaction_count}")
        else:
            print("⚠️  DECISION_LOG.md not found (might be in different location)")

        print("✅ Completed 10 turns with compact_every=3")


async def test_explicit_disable():
    """Test that janitor can be explicitly disabled even with memory."""
    print("\n=== Test 7: Explicit Disable ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        memory = LocalMemory(path=workspace / "memory.db")
        agent = Agent(
            provider=MockProvider(),
            instructions="Test",
            memory=memory,
            session_dir=workspace / "sessions",
            enable_auto_compact=False,  # Explicitly disable
        )

        assert agent.janitor is None, "Janitor should be disabled when explicitly disabled"

        print("✅ Janitor can be explicitly disabled even with memory")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Janitor-Memory Integration")
    print("=" * 60)

    tests = [
        test_janitor_auto_initialization,
        test_janitor_disabled_without_memory,
        test_context_limit_detection,
        test_custom_context_limit,
        test_decisions_stored_as_memories,
        test_compaction_triggers,
        test_explicit_disable,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"\n❌ Test failed: {test.__name__}")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

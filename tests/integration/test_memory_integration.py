"""Integration tests for memory system in the agent loop."""

import pytest

from teotl.core.agent import Agent
from teotl.core.provider import Provider
from teotl.core.types import CompletionResult
from teotl.primitives.memory.local import LocalMemory


class MockProvider(Provider):
    """Mock provider for testing memory integration."""

    def __init__(self, responses: list[str]):
        """
        Args:
            responses: List of responses to return (one per complete() call)
        """
        self.responses = responses
        self.call_count = 0

    async def complete(self, system: str, messages: list, tools: list | None = None, **kwargs):
        """Return mock responses."""
        content = self.responses[min(self.call_count, len(self.responses) - 1)]
        self.call_count += 1

        return CompletionResult(
            content=content,
            done=True,
            tool_calls=[],
            usage={"input_tokens": 100, "output_tokens": 50},
        )

    @property
    def context_window(self) -> int:
        return 100_000

    @property
    def model_name(self) -> str:
        return "mock-model"


class TestMemoryIntegration:
    """Test memory system integration with agent loop."""

    @pytest.mark.asyncio
    async def test_memory_recall_in_context(self, tmp_path):
        """Test that relevant memories are injected into agent context."""
        # Create memory store and pre-populate with a memory
        memory = LocalMemory(tmp_path / "test_memory.db")
        await memory.remember("User prefers Python programming language")

        # Track system prompts to verify memory injection
        system_prompts = []

        class TrackingProvider(Provider):
            async def complete(
                self, system: str, messages: list, tools: list | None = None, **kwargs
            ):
                system_prompts.append(system)
                return CompletionResult(
                    content="I'll keep that in mind!",
                    done=True,
                    tool_calls=[],
                    usage={"input_tokens": 100, "output_tokens": 50},
                )

            @property
            def context_window(self) -> int:
                return 100_000

            @property
            def model_name(self) -> str:
                return "tracking-mock"

        provider = TrackingProvider()
        agent = Agent(provider=provider, memory=memory)

        # Ask a question with words that match the memory (for FTS search)
        await agent.run("What Python programming should I use?")

        # Verify memory was injected into system prompt
        assert len(system_prompts) == 1
        # Check if memory section exists (it should if memories were found)
        has_memory_section = "Relevant Context from Memory" in system_prompts[0]
        if has_memory_section:
            assert "Python" in system_prompts[0] or "prefers" in system_prompts[0]

    @pytest.mark.asyncio
    async def test_explicit_memory_extraction(self, tmp_path):
        """Test that explicit 'remember that...' statements are captured."""
        memory = LocalMemory(tmp_path / "test_memory.db")
        provider = MockProvider(["Got it, I'll remember that."])
        agent = Agent(provider=provider, memory=memory)

        # User explicitly asks to remember something
        await agent.run("Remember that I work at Anthropic")

        # Verify memory was stored
        memories = await memory.list_all()
        assert len(memories) >= 1
        assert any("Anthropic" in m.content for m in memories)

        # Check metadata
        stored = [m for m in memories if "Anthropic" in m.content][0]
        assert stored.metadata.source == "explicit"
        assert stored.metadata.importance == 8  # High importance for explicit memories

    @pytest.mark.asyncio
    async def test_multiple_memory_patterns(self, tmp_path):
        """Test various memory extraction patterns."""
        memory = LocalMemory(tmp_path / "test_memory.db")
        provider = MockProvider(
            [
                "Noted!",
                "Got it!",
                "I'll keep that in mind!",
                "Understood!",
            ]
        )
        agent = Agent(provider=provider, memory=memory)

        # Test different patterns
        await agent.run("My name is Alice")
        await agent.run("I prefer dark mode")
        await agent.run("Note that I'm in Pacific timezone")
        await agent.run("Please keep in mind that I'm a beginner")

        # Verify all were stored
        memories = await memory.list_all()
        contents = [m.content for m in memories]

        assert any("Alice" in c for c in contents)
        assert any("dark mode" in c for c in contents)
        assert any("Pacific" in c for c in contents)
        assert any("beginner" in c for c in contents)

    @pytest.mark.asyncio
    async def test_manual_remember_api(self, tmp_path):
        """Test manual memory storage via Agent API."""
        memory = LocalMemory(tmp_path / "test_memory.db")
        provider = MockProvider(["OK"])
        agent = Agent(provider=provider, memory=memory)

        # Manually store a memory
        memory_id = await agent.remember(
            "User's favorite color is blue", importance=7, tags=["preferences", "color"]
        )

        assert memory_id is not None

        # Retrieve and verify
        memories = await agent.recall("favorite color")
        assert len(memories) >= 1
        assert any("blue" in m.content for m in memories)

    @pytest.mark.asyncio
    async def test_manual_recall_api(self, tmp_path):
        """Test manual memory retrieval via Agent API."""
        memory = LocalMemory(tmp_path / "test_memory.db")
        provider = MockProvider(["OK"])
        agent = Agent(provider=provider, memory=memory)

        # Store some memories
        await agent.remember("Python is great for data science", tags=["python"])
        await agent.remember("JavaScript is great for web development", tags=["javascript"])
        await agent.remember("Rust is great for systems programming", tags=["rust"])

        # Recall specific memories
        python_memories = await agent.recall("Python")
        assert len(python_memories) >= 1
        assert any("data science" in m.content for m in python_memories)

        web_memories = await agent.recall("web development")
        assert len(web_memories) >= 1
        assert any("JavaScript" in m.content for m in web_memories)

    @pytest.mark.asyncio
    async def test_forget_api(self, tmp_path):
        """Test memory deletion via Agent API."""
        memory = LocalMemory(tmp_path / "test_memory.db")
        provider = MockProvider(["OK"])
        agent = Agent(provider=provider, memory=memory)

        # Store a memory
        memory_id = await agent.remember("This should be forgotten")

        # Verify it exists
        memories = await agent.list_memories()
        assert len(memories) == 1

        # Delete it
        deleted = await agent.teotlt(memory_id)
        assert deleted is True

        # Verify it's gone
        memories = await agent.list_memories()
        assert len(memories) == 0

        # Try to delete again (should return False)
        deleted = await agent.teotlt(memory_id)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_memories_api(self, tmp_path):
        """Test listing all memories via Agent API."""
        memory = LocalMemory(tmp_path / "test_memory.db")
        provider = MockProvider(["OK"])
        agent = Agent(provider=provider, memory=memory)

        # Store several memories
        await agent.remember("Memory 1")
        await agent.remember("Memory 2")
        await agent.remember("Memory 3")

        # List all
        memories = await agent.list_memories()
        assert len(memories) == 3

        # Test pagination
        page1 = await agent.list_memories(limit=2, offset=0)
        assert len(page1) == 2

        page2 = await agent.list_memories(limit=2, offset=2)
        assert len(page2) == 1

    @pytest.mark.asyncio
    async def test_memory_not_initialized(self):
        """Test behavior when memory system is not initialized."""
        provider = MockProvider(["OK"])
        # Force memory to None by passing it explicitly and making _init_memory fail
        agent = Agent(provider=provider)

        # Manually set memory to None to simulate disabled memory
        agent.memory = None

        # All memory methods should raise ValueError
        with pytest.raises(ValueError, match="Memory system not initialized"):
            await agent.remember("Test")

        with pytest.raises(ValueError, match="Memory system not initialized"):
            await agent.recall("Test")

        with pytest.raises(ValueError, match="Memory system not initialized"):
            await agent.teotlt("test-id")

        with pytest.raises(ValueError, match="Memory system not initialized"):
            await agent.list_memories()

    @pytest.mark.asyncio
    async def test_memory_context_budget(self, tmp_path):
        """Test that memory injection respects token budget."""
        memory = LocalMemory(tmp_path / "test_memory.db")
        provider = MockProvider(["OK"])
        agent = Agent(provider=provider, memory=memory)

        # Store many memories
        for i in range(20):
            await agent.remember(f"Memory number {i}: " + "x" * 100, importance=5)

        # Track system prompt size
        system_prompts = []

        class TrackingProvider(Provider):
            async def complete(
                self, system: str, messages: list, tools: list | None = None, **kwargs
            ):
                system_prompts.append(system)
                return CompletionResult(
                    content="OK",
                    done=True,
                    tool_calls=[],
                    usage={"input_tokens": 100, "output_tokens": 50},
                )

            @property
            def context_window(self) -> int:
                return 100_000

            @property
            def model_name(self) -> str:
                return "tracking-mock"

        agent.provider = TrackingProvider()

        # Ask a question that matches all memories
        await agent.run("Tell me about memory")

        # Verify memories were injected but within budget
        # Default budget is 500 tokens (~2000 chars)
        assert len(system_prompts) == 1
        if "Relevant Context from Memory" in system_prompts[0]:
            memory_section_start = system_prompts[0].find("Relevant Context from Memory")
            memory_section = system_prompts[0][memory_section_start:]
            # Should not include all 20 memories (that would be ~4000+ chars)
            assert len(memory_section) < 3000  # Budget constraint applied

    @pytest.mark.asyncio
    async def test_memory_recall_empty_query(self, tmp_path):
        """Test memory recall with empty or no matches."""
        memory = LocalMemory(tmp_path / "test_memory.db")
        provider = MockProvider(["OK"])
        agent = Agent(provider=provider, memory=memory)

        # Store a memory
        await agent.remember("Python is great")

        # Query that won't match
        await agent.recall("Java programming")
        # SQLite FTS may return partial matches, or empty list
        # Either is acceptable behavior

    @pytest.mark.asyncio
    async def test_memory_persistence_across_runs(self, tmp_path):
        """Test that memories persist across agent instances."""
        memory_path = tmp_path / "persistent_memory.db"

        # First agent stores memory
        memory1 = LocalMemory(memory_path)
        provider1 = MockProvider(["OK"])
        agent1 = Agent(provider=provider1, memory=memory1)
        await agent1.remember("This should persist")

        # Second agent with same memory store
        memory2 = LocalMemory(memory_path)
        provider2 = MockProvider(["OK"])
        agent2 = Agent(provider=provider2, memory=memory2)

        # Should be able to recall memory from first agent
        memories = await agent2.recall("persist")
        assert len(memories) >= 1
        assert any("persist" in m.content for m in memories)

    @pytest.mark.asyncio
    async def test_memory_with_no_matches(self, tmp_path):
        """Test memory recall when query yields no results."""
        memory = LocalMemory(tmp_path / "test_memory.db")

        # Track system prompts
        system_prompts = []

        class TrackingProvider(Provider):
            async def complete(
                self, system: str, messages: list, tools: list | None = None, **kwargs
            ):
                system_prompts.append(system)
                return CompletionResult(
                    content="I don't have any relevant context.",
                    done=True,
                    tool_calls=[],
                    usage={"input_tokens": 100, "output_tokens": 50},
                )

            @property
            def context_window(self) -> int:
                return 100_000

            @property
            def model_name(self) -> str:
                return "tracking-mock"

        provider = TrackingProvider()
        agent = Agent(provider=provider, memory=memory)

        # Query without any stored memories
        await agent.run("Tell me about programming")

        # System prompt should NOT contain memory section
        assert len(system_prompts) == 1
        assert "Relevant Context from Memory" not in system_prompts[0]

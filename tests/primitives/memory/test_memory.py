"""Tests for the memory system."""

import pytest

from teotl.core.types import MemoryMeta
from teotl.primitives.memory.local import LocalMemory


@pytest.fixture
async def memory(tmp_path):
    mem = LocalMemory(path=tmp_path / "test_memory.db")
    yield mem
    mem.close()


async def test_remember_and_recall(memory):
    await memory.remember("User prefers dark mode")
    results = await memory.recall("dark mode")
    assert len(results) >= 1
    assert any("dark mode" in m.content for m in results)


async def test_remember_with_metadata(memory):
    meta = MemoryMeta(source="session", tags=["preference", "ui"], importance=8)
    memory_id = await memory.remember("User prefers Python over JavaScript", meta)
    assert memory_id is not None

    results = await memory.recall("Python")
    assert len(results) >= 1


async def test_forget(memory):
    memory_id = await memory.remember("Temporary fact")
    assert await memory.count() == 1

    deleted = await memory.forget(memory_id)
    assert deleted is True
    assert await memory.count() == 0


async def test_forget_nonexistent(memory):
    deleted = await memory.forget("nonexistent_id")
    assert deleted is False


async def test_list_all(memory):
    await memory.remember("Fact one")
    await memory.remember("Fact two")
    await memory.remember("Fact three")

    all_memories = await memory.list_all()
    assert len(all_memories) == 3


async def test_list_all_with_limit(memory):
    for i in range(10):
        await memory.remember(f"Fact number {i}")

    limited = await memory.list_all(limit=5)
    assert len(limited) == 5


async def test_count(memory):
    assert await memory.count() == 0

    await memory.remember("One")
    assert await memory.count() == 1

    await memory.remember("Two")
    assert await memory.count() == 2


async def test_format_for_context(memory):
    await memory.remember("User is a Python developer")
    await memory.remember("User works at Acme Corp")

    all_mems = await memory.list_all()
    formatted = memory.format_for_context(all_mems, token_budget=500)
    assert "Python developer" in formatted
    assert "Acme Corp" in formatted


async def test_format_for_context_budget(memory):
    # Add many memories
    for i in range(50):
        await memory.remember(f"This is memory number {i} with some extra content to take up space")

    all_mems = await memory.list_all()
    formatted = memory.format_for_context(all_mems, token_budget=50)
    # Should be truncated
    lines = formatted.strip().split("\n")
    assert len(lines) < 50


async def test_recall_with_no_results(memory):
    results = await memory.recall("something that doesn't exist")
    assert results == []


class TestNaturalLanguageRecall:
    """recall() searches the question's keywords, matching memories with any of them."""

    @pytest.mark.asyncio
    async def test_question_finds_memory(self, tmp_path):
        from teotl.primitives.memory.local import LocalMemory

        memory = LocalMemory(tmp_path / "m.db", auto_cleanup=False)
        await memory.remember("my favorite deployment region is eu-west-3 and my team is called Nightjar")
        await memory.remember("the staging database password rotates monthly")

        found = await memory.recall("Which deployment region do I prefer, and what's my team called?")
        assert [m.content for m in found][0].startswith("my favorite deployment region")
        assert all("staging" not in m.content for m in found)

    @pytest.mark.asyncio
    async def test_unrelated_question_finds_nothing(self, tmp_path):
        from teotl.primitives.memory.local import LocalMemory

        memory = LocalMemory(tmp_path / "m.db", auto_cleanup=False)
        await memory.remember("my favorite deployment region is eu-west-3")
        assert await memory.recall("What's the weather like?") == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", ['"unbalanced', "a AND OR NOT (", "???", "", "O'Brien's *"])
    async def test_odd_input_does_not_raise(self, tmp_path, query):
        from teotl.primitives.memory.local import LocalMemory

        memory = LocalMemory(tmp_path / "m.db", auto_cleanup=False)
        await memory.remember("O'Brien owns the billing service")
        await memory.recall(query)  # no exception

    @pytest.mark.asyncio
    async def test_more_matching_terms_rank_first(self, tmp_path):
        from teotl.primitives.memory.local import LocalMemory

        memory = LocalMemory(tmp_path / "m.db", auto_cleanup=False)
        await memory.remember("the billing service runs on Postgres")
        await memory.remember("the billing service deploys to eu-west-3 on Postgres 16")
        found = await memory.recall("Where does the billing service deploy, and which Postgres?")
        assert "eu-west-3" in found[0].content

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

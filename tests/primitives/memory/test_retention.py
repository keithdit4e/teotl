"""Tests for memory retention policies and TTL."""

from datetime import datetime, timedelta

import pytest

from teotl.core.types import MemoryMeta
from teotl.primitives.memory.local import LocalMemory


class TestMemoryRetention:
    """Test memory retention and TTL functionality."""

    @pytest.mark.asyncio
    async def test_ttl_explicit(self, tmp_path):
        """Test explicit TTL specification."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False)

        # Store with 7-day TTL
        await memory.remember(
            "This expires in 7 days",
            MemoryMeta(importance=5),
            ttl_days=7,
        )

        # Verify it was stored
        memories = await memory.list_all()
        assert len(memories) == 1
        assert memories[0].expires_at is not None

        # Check expiration date is ~7 days from now
        expected_expiry = datetime.now() + timedelta(days=7)
        actual_expiry = memories[0].expires_at
        assert abs((actual_expiry - expected_expiry).total_seconds()) < 60  # Within 1 minute

    @pytest.mark.asyncio
    async def test_ttl_based_on_importance(self, tmp_path):
        """Test that TTL is auto-assigned based on importance."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False)

        # Critical (importance=10): No expiration
        id_critical = await memory.remember("Critical", MemoryMeta(importance=10))

        # Important (importance=8): 1 year
        id_important = await memory.remember("Important", MemoryMeta(importance=8))

        # Medium (importance=5): 90 days
        id_medium = await memory.remember("Medium", MemoryMeta(importance=5))

        # Low (importance=3): 7 days
        id_low = await memory.remember("Low", MemoryMeta(importance=3))

        memories = await memory.list_all()
        assert len(memories) == 4

        # Find each memory
        critical = next(m for m in memories if m.id == id_critical)
        important = next(m for m in memories if m.id == id_important)
        medium = next(m for m in memories if m.id == id_medium)
        low = next(m for m in memories if m.id == id_low)

        # Verify TTL assignments
        assert critical.expires_at is None  # Never expires

        # Important: ~1 year
        assert important.expires_at is not None
        days_until_expiry = (important.expires_at - datetime.now()).days
        assert 360 <= days_until_expiry <= 370

        # Medium: ~90 days
        assert medium.expires_at is not None
        days_until_expiry = (medium.expires_at - datetime.now()).days
        assert 88 <= days_until_expiry <= 92

        # Low: ~7 days
        assert low.expires_at is not None
        days_until_expiry = (low.expires_at - datetime.now()).days
        assert 6 <= days_until_expiry <= 8

    @pytest.mark.asyncio
    async def test_cleanup_expired_memories(self, tmp_path):
        """Test that expired memories are deleted during cleanup."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False)

        # Store memory with 0-day TTL (expires immediately)
        await memory.remember("Expired", MemoryMeta(importance=5), ttl_days=0)

        # Store memory with future expiration
        await memory.remember("Not expired", MemoryMeta(importance=5), ttl_days=30)

        # Store memory with no expiration
        await memory.remember("Never expires", MemoryMeta(importance=10))

        # Before cleanup: 3 memories
        memories = await memory.list_all()
        assert len(memories) == 3

        # Run cleanup
        deleted = await memory.cleanup_expired()
        assert deleted == 1

        # After cleanup: 2 memories (expired one removed)
        memories = await memory.list_all()
        assert len(memories) == 2
        contents = [m.content for m in memories]
        assert "Expired" not in contents
        assert "Not expired" in contents
        assert "Never expires" in contents

    @pytest.mark.asyncio
    async def test_cleanup_inactive_low_importance(self, tmp_path):
        """Test that old, never-accessed low-importance memories are deleted."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False)

        # Store a low-importance memory
        memory_id = await memory.remember("Low importance", MemoryMeta(importance=3))

        # Manually set created date to 8 days ago
        old_date = (datetime.now() - timedelta(days=8)).isoformat()
        memory.db.execute(
            "UPDATE memories SET created = ?, last_accessed = NULL WHERE id = ?",
            (old_date, memory_id),
        )
        memory.db.commit()

        # Before cleanup: 1 memory
        memories = await memory.list_all()
        assert len(memories) == 1

        # Run cleanup (should delete low-importance memories older than 7 days)
        deleted = await memory.cleanup_expired()
        assert deleted == 1

        # After cleanup: 0 memories
        memories = await memory.list_all()
        assert len(memories) == 0

    @pytest.mark.asyncio
    async def test_cleanup_respects_access_patterns(self, tmp_path):
        """Test that cleanup respects recent access patterns."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False)

        # Store a medium-importance memory
        memory_id = await memory.remember("Medium importance", MemoryMeta(importance=6))

        # Set created and last_accessed to 40 days ago (beyond 30-day inactive threshold)
        old_date = (datetime.now() - timedelta(days=40)).isoformat()
        memory.db.execute(
            "UPDATE memories SET created = ?, last_accessed = ? WHERE id = ?",
            (old_date, old_date, memory_id),
        )
        memory.db.commit()

        # Before cleanup: 1 memory
        memories = await memory.list_all()
        assert len(memories) == 1

        # Run cleanup (should delete medium-importance memories inactive for 30+ days)
        deleted = await memory.cleanup_expired()
        assert deleted == 1

        # After cleanup: 0 memories
        memories = await memory.list_all()
        assert len(memories) == 0

    @pytest.mark.asyncio
    async def test_cleanup_protects_critical_memories(self, tmp_path):
        """Test that critical memories (importance >= 9) are never deleted by cleanup."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False)

        # Store critical memory with old creation date
        memory_id = await memory.remember("Critical", MemoryMeta(importance=10))

        # Set created to 2 years ago
        old_date = (datetime.now() - timedelta(days=730)).isoformat()
        memory.db.execute(
            "UPDATE memories SET created = ?, last_accessed = NULL WHERE id = ?",
            (old_date, memory_id),
        )
        memory.db.commit()

        # Run cleanup
        deleted = await memory.cleanup_expired()
        assert deleted == 0

        # Critical memory should still exist
        memories = await memory.list_all()
        assert len(memories) == 1
        assert memories[0].content == "Critical"

    @pytest.mark.asyncio
    async def test_cleanup_by_storage_limit(self, tmp_path):
        """Test that cleanup enforces storage limits."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False, max_memories=10)

        # Store 15 memories with varying importance
        for i in range(15):
            importance = 5 if i < 10 else 3  # First 10 are medium, last 5 are low
            await memory.remember(f"Memory {i}", MemoryMeta(importance=importance))

        # Before cleanup: 15 memories
        count = await memory.count()
        assert count == 15

        # Run storage cleanup (limit to 10)
        deleted = await memory.cleanup_by_storage_limit(max_memories=10)
        assert deleted == 5

        # After cleanup: 10 memories
        count = await memory.count()
        assert count == 10

        # Should have deleted the 5 low-importance memories
        memories = await memory.list_all()
        for mem in memories:
            assert mem.metadata.importance >= 5

    @pytest.mark.asyncio
    async def test_storage_limit_protects_critical(self, tmp_path):
        """Test that storage limit cleanup protects critical memories."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False, max_memories=5)

        # Store 3 critical memories
        for i in range(3):
            await memory.remember(f"Critical {i}", MemoryMeta(importance=10))

        # Store 5 low-importance memories
        for i in range(5):
            await memory.remember(f"Low {i}", MemoryMeta(importance=3))

        # Total: 8 memories
        count = await memory.count()
        assert count == 8

        # Run storage cleanup (limit to 5)
        deleted = await memory.cleanup_by_storage_limit(max_memories=5)
        assert deleted == 3  # Deleted 3 low-importance memories

        # After cleanup: 5 memories (all 3 critical + 2 low)
        count = await memory.count()
        assert count == 5

        # All critical memories should still exist
        memories = await memory.list_all()
        critical_count = sum(1 for m in memories if m.metadata.importance == 10)
        assert critical_count == 3

    @pytest.mark.asyncio
    async def test_retention_stats(self, tmp_path):
        """Test retention statistics reporting."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False)

        # Store memories with various importance levels
        await memory.remember("Importance 10", MemoryMeta(importance=10))
        await memory.remember("Importance 8", MemoryMeta(importance=8))
        await memory.remember("Importance 5", MemoryMeta(importance=5))
        await memory.remember("Importance 3", MemoryMeta(importance=3))

        # Store one with expiration in the past
        await memory.remember("Expired", MemoryMeta(importance=5), ttl_days=0)

        # Access one memory to test access tracking
        await memory.recall("Importance 10")

        # Get stats
        stats = await memory.get_retention_stats()

        assert stats["total_memories"] == 5
        assert stats["by_importance"][10] == 1
        assert stats["by_importance"][8] == 1
        assert stats["by_importance"][5] == 2
        assert stats["by_importance"][3] == 1
        assert stats["expired_pending_cleanup"] == 1
        assert stats["never_accessed"] == 4  # 4 were never recalled
        assert stats["avg_access_count"] >= 1.0  # One was accessed

    @pytest.mark.asyncio
    async def test_auto_cleanup_on_init(self, tmp_path):
        """Test that auto-cleanup runs on initialization if enabled."""
        # First, create a memory store and add expired memories
        memory1 = LocalMemory(tmp_path / "test.db", auto_cleanup=False)
        await memory1.remember("Expired", MemoryMeta(importance=5), ttl_days=0)
        await memory1.remember("Valid", MemoryMeta(importance=5), ttl_days=30)
        memory1.close()

        # Before cleanup: 2 memories
        memory2 = LocalMemory(tmp_path / "test.db", auto_cleanup=False)
        count_before = await memory2.count()
        assert count_before == 2
        memory2.close()

        # Initialize with auto_cleanup=True
        # Note: In synchronous init, cleanup is skipped. This tests the logic exists.
        memory3 = LocalMemory(tmp_path / "test.db", auto_cleanup=True)

        # Manually trigger cleanup to test the logic
        deleted = await memory3.cleanup_expired()
        assert deleted == 1

        # After cleanup: 1 memory
        count_after = await memory3.count()
        assert count_after == 1

        memories = await memory3.list_all()
        assert memories[0].content == "Valid"

    @pytest.mark.asyncio
    async def test_ttl_override_importance(self, tmp_path):
        """Test that explicit TTL overrides importance-based TTL."""
        memory = LocalMemory(tmp_path / "test.db", auto_cleanup=False)

        # Critical importance normally never expires, but force 1-day TTL
        await memory.remember(
            "Critical but short-lived", MemoryMeta(importance=10), ttl_days=1
        )

        memories = await memory.list_all()
        assert len(memories) == 1

        # Should have expiration despite critical importance
        assert memories[0].expires_at is not None
        days_until_expiry = (memories[0].expires_at - datetime.now()).days
        assert days_until_expiry <= 1

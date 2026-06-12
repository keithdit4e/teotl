"""SQLite-backed local memory. Zero external service dependencies."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import ulid

from teotl.core.types import Memory, MemoryMeta

logger = logging.getLogger(__name__)


class LocalMemory:
    """
    SQLite-backed local memory store.

    Features:
    - Keyword-based search (full-text search via FTS5)
    - Recency weighting
    - Tag filtering
    - Optional vector similarity (requires sentence-transformers + sqlite-vec)

    The vector path is optional — keyword search works well for most use cases
    and requires zero additional dependencies.
    """

    def __init__(
        self,
        path: Path | str | None = None,
        *,
        auto_cleanup: bool = True,
        max_memories: int = 10000,
    ) -> None:
        """
        Initialize local memory store.

        Args:
            path: Path to SQLite database file (default: ~/.forge/memory.db)
            auto_cleanup: Run cleanup on initialization (default: True)
            max_memories: Maximum number of memories to keep (default: 10,000)
        """
        self.path = Path(path) if path else Path.home() / ".forge" / "memory.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.row_factory = sqlite3.Row
        self._ensure_schema()
        self._embedder = None  # Lazy-loaded
        self.max_memories = max_memories

        # Run cleanup on init if enabled
        if auto_cleanup:
            import asyncio

            try:
                # Try to run cleanup (works if called from async context)
                asyncio.create_task(self._initial_cleanup())
            except RuntimeError:
                # Not in async context, skip initial cleanup
                # Will run on first recall() call
                logger.debug("Skipping initial cleanup (not in async context)")

    async def _initial_cleanup(self) -> None:
        """Run initial cleanup on memory store initialization."""
        try:
            expired = await self.cleanup_expired()
            storage = await self.cleanup_by_storage_limit(self.max_memories)
            if expired or storage:
                logger.info(
                    f"Initial memory cleanup: {expired} expired, {storage} over storage limit"
                )
        except Exception as e:
            logger.warning(f"Initial memory cleanup failed: {e}")

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                tags TEXT DEFAULT '[]',
                importance INTEGER DEFAULT 5,
                session_id TEXT,
                created TEXT NOT NULL,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                expires_at TEXT  -- ISO timestamp when memory expires (NULL = never)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content,
                tags,
                content='memories',
                content_rowid='rowid'
            );

            -- Triggers to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, tags)
                VALUES (new.rowid, new.content, new.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, tags)
                VALUES ('delete', old.rowid, old.content, old.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, tags)
                VALUES ('delete', old.rowid, old.content, old.tags);
                INSERT INTO memories_fts(rowid, content, tags)
                VALUES (new.rowid, new.content, new.tags);
            END;
        """)
        self.db.commit()

        # Migrate existing memories to add expires_at column if needed
        try:
            self.db.execute("SELECT expires_at FROM memories LIMIT 1")
        except sqlite3.OperationalError:
            logger.info("Migrating memory schema to add expires_at column")
            self.db.execute("ALTER TABLE memories ADD COLUMN expires_at TEXT")
            self.db.commit()

    async def remember(
        self, content: str, metadata: MemoryMeta | None = None, ttl_days: int | None = None
    ) -> str:
        """
        Store a memory.

        Args:
            content: The information to remember
            metadata: Memory metadata (source, tags, importance, etc.)
            ttl_days: Time-to-live in days (None = use importance-based default)

        Returns:
            Memory ID
        """
        meta = metadata or MemoryMeta()
        memory_id = ulid.new().str

        # Calculate expiration based on TTL or importance
        expires_at = None
        if ttl_days is not None:
            expires_at = (datetime.now() + timedelta(days=ttl_days)).isoformat()
        else:
            # Auto-TTL based on importance (if not critical)
            ttl = self._get_default_ttl(meta.importance)
            if ttl:
                expires_at = (datetime.now() + timedelta(days=ttl)).isoformat()

        self.db.execute(
            """INSERT INTO memories (id, content, source, tags, importance, session_id, created, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory_id,
                content,
                meta.source,
                json.dumps(meta.tags),
                meta.importance,
                meta.session_id,
                datetime.now().isoformat(),
                expires_at,
            ),
        )
        self.db.commit()
        logger.debug(f"Stored memory {memory_id}: {content[:50]}...")
        return memory_id

    def _get_default_ttl(self, importance: int) -> int | None:
        """
        Get default TTL in days based on importance.

        Returns:
            Days until expiration, or None for permanent storage
        """
        # Critical memories (9-10): Never expire
        if importance >= 9:
            return None

        # Important memories (7-8): 1 year
        if importance >= 7:
            return 365

        # Medium memories (5-6): 90 days
        if importance >= 5:
            return 90

        # Low memories (1-4): 7 days
        return 7

    async def recall(self, query: str, *, limit: int = 10) -> list[Memory]:
        """
        Retrieve relevant memories using hybrid search.

        Combines:
        1. Full-text search (BM25 ranking via FTS5)
        2. Recency boost (newer memories rank higher)
        3. Importance weighting
        """
        # FTS5 search with BM25 ranking
        try:
            rows = self.db.execute(
                """
                SELECT m.*, bm25(memories_fts) as rank
                FROM memories_fts fts
                JOIN memories m ON m.rowid = fts.rowid
                WHERE memories_fts MATCH ?
                ORDER BY
                    rank * (m.importance / 5.0) *
                    (1.0 + 1.0 / (1.0 + julianday('now') - julianday(m.created)))
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS query syntax error — fall back to LIKE
            rows = self.db.execute(
                """
                SELECT * FROM memories
                WHERE content LIKE ?
                ORDER BY importance DESC, created DESC
                LIMIT ?
                """,
                (f"%{query}%", limit),
            ).fetchall()

        memories = [self._row_to_memory(row) for row in rows]

        # Update access tracking
        for mem in memories:
            self.db.execute(
                "UPDATE memories SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
                (datetime.now().isoformat(), mem.id),
            )
        self.db.commit()

        return memories

    async def forget(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        cursor = self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.db.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug(f"Deleted memory {memory_id}")
        return deleted

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[Memory]:
        """List all memories with pagination."""
        rows = self.db.execute(
            "SELECT * FROM memories ORDER BY created DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    async def count(self) -> int:
        """Return total number of stored memories."""
        row = self.db.execute("SELECT COUNT(*) FROM memories").fetchone()
        return row[0]

    def format_for_context(self, memories: list[Memory], *, token_budget: int = 500) -> str:
        """Format memories for injection into agent context."""
        if not memories:
            return ""

        lines = []
        tokens_used = 0
        for mem in memories:
            line = f"- {mem.content}"
            # Rough estimate: 4 chars per token
            line_tokens = len(line) // 4
            if tokens_used + line_tokens > token_budget:
                break
            lines.append(line)
            tokens_used += line_tokens

        return "\n".join(lines)

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Convert a database row to a Memory object."""
        # Check if expires_at exists in row (for backward compatibility)
        expires_at = None
        if "expires_at" in row.keys() and row["expires_at"]:
            expires_at = datetime.fromisoformat(row["expires_at"])

        # Get session_id if exists (for backward compatibility)
        session_id = row["session_id"] if "session_id" in row.keys() else None

        return Memory(
            id=row["id"],
            content=row["content"],
            metadata=MemoryMeta(
                source=row["source"],
                tags=json.loads(row["tags"]),
                importance=row["importance"],
                session_id=session_id,
            ),
            created=datetime.fromisoformat(row["created"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"])
            if row["last_accessed"]
            else None,
            access_count=row["access_count"],
            expires_at=expires_at,
        )

    async def cleanup_expired(self) -> int:
        """
        Delete expired memories based on TTL and retention policies.

        Returns:
            Number of memories deleted
        """
        now = datetime.now()
        deleted_count = 0

        # 1. Delete memories past their expiration date
        cursor = self.db.execute(
            "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now.isoformat(),),
        )
        deleted_count += cursor.rowcount

        # 2. Delete old, never-accessed memories (inactive cleanup)
        # Low importance (1-4): delete if not accessed in 7 days
        cursor = self.db.execute(
            """DELETE FROM memories
               WHERE importance < 5
               AND (last_accessed IS NULL OR last_accessed < ?)
               AND created < ?""",
            ((now - timedelta(days=7)).isoformat(), (now - timedelta(days=7)).isoformat()),
        )
        deleted_count += cursor.rowcount

        # Medium importance (5-6): delete if not accessed in 30 days
        cursor = self.db.execute(
            """DELETE FROM memories
               WHERE importance >= 5 AND importance < 7
               AND last_accessed IS NOT NULL
               AND last_accessed < ?""",
            ((now - timedelta(days=30)).isoformat(),),
        )
        deleted_count += cursor.rowcount

        # Important (7-8): delete if not accessed in 6 months
        cursor = self.db.execute(
            """DELETE FROM memories
               WHERE importance >= 7 AND importance < 9
               AND last_accessed IS NOT NULL
               AND last_accessed < ?""",
            ((now - timedelta(days=180)).isoformat(),),
        )
        deleted_count += cursor.rowcount

        self.db.commit()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired/inactive memories")

        return deleted_count

    async def cleanup_by_storage_limit(self, max_memories: int = 10000) -> int:
        """
        Delete oldest, least important memories to stay under storage limit.

        Args:
            max_memories: Maximum number of memories to keep

        Returns:
            Number of memories deleted
        """
        current_count = await self.count()

        if current_count <= max_memories:
            return 0

        to_delete = current_count - max_memories

        # Delete oldest memories with lowest importance (but protect critical memories)
        cursor = self.db.execute(
            """DELETE FROM memories
               WHERE id IN (
                   SELECT id FROM memories
                   WHERE importance < 9
                   ORDER BY importance ASC, created ASC
                   LIMIT ?
               )""",
            (to_delete,),
        )
        deleted_count = cursor.rowcount
        self.db.commit()

        if deleted_count > 0:
            logger.info(
                f"Deleted {deleted_count} memories to stay under storage limit ({max_memories})"
            )

        return deleted_count

    async def get_retention_stats(self) -> dict:
        """
        Get statistics about memory retention and storage.

        Returns:
            Dictionary with retention statistics
        """
        total = await self.count()

        # Count by importance
        importance_counts = {}
        for i in range(1, 11):
            row = self.db.execute(
                "SELECT COUNT(*) FROM memories WHERE importance = ?", (i,)
            ).fetchone()
            importance_counts[i] = row[0]

        # Count expired but not cleaned up
        expired_row = self.db.execute(
            "SELECT COUNT(*) FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
            (datetime.now().isoformat(),),
        ).fetchone()

        # Count never accessed
        never_accessed_row = self.db.execute(
            "SELECT COUNT(*) FROM memories WHERE last_accessed IS NULL"
        ).fetchone()

        # Average access count
        avg_access_row = self.db.execute(
            "SELECT AVG(access_count) FROM memories WHERE access_count > 0"
        ).fetchone()

        return {
            "total_memories": total,
            "by_importance": importance_counts,
            "expired_pending_cleanup": expired_row[0],
            "never_accessed": never_accessed_row[0],
            "avg_access_count": round(avg_access_row[0], 2) if avg_access_row[0] else 0,
        }

    def close(self) -> None:
        """Close the database connection."""
        self.db.close()

"""Memory store protocol — the interface all backends implement."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from teotl.core.types import Memory, MemoryMeta


@runtime_checkable
class MemoryStore(Protocol):
    """
    Interface for memory backends.

    Implement this to create custom memory storage (Redis, Postgres, cloud, etc.).
    The framework ships with LocalMemory (SQLite + local embeddings).
    """

    async def remember(self, content: str, metadata: MemoryMeta | None = None) -> str:
        """
        Store a memory. Returns memory ID.

        Args:
            content: The text content to remember.
            metadata: Optional metadata (source, tags, importance).

        Returns:
            Unique memory ID.
        """
        ...

    async def recall(self, query: str, *, limit: int = 10) -> list[Memory]:
        """
        Retrieve relevant memories for a query.

        Uses hybrid retrieval: embedding similarity + keyword + recency.

        Args:
            query: The query to search for.
            limit: Maximum number of memories to return.

        Returns:
            List of relevant memories, ordered by relevance.
        """
        ...

    async def forget(self, memory_id: str) -> bool:
        """
        Delete a specific memory.

        Args:
            memory_id: ID of the memory to delete.

        Returns:
            True if deleted, False if not found.
        """
        ...

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[Memory]:
        """List all memories with pagination."""
        ...

    async def count(self) -> int:
        """Return total number of stored memories."""
        ...

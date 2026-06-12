"""Persistent task storage for immediate execution requests.

Tasks are short-lived execution requests that differ from missions:
- Tasks are immediate (execute ASAP) vs missions (scheduled)
- Tasks have priorities (can interrupt missions)
- Tasks expire (auto-cleanup old tasks)
- Tasks come from users, agents, or systems
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any

import ulid
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    """Task priority levels (higher number = higher priority)."""

    CRITICAL = 5  # System critical, always interrupts missions
    URGENT = 4  # User urgent request, interrupts by default
    HIGH = 3  # Important, queued before next mission
    NORMAL = 2  # Standard priority
    LOW = 1  # Background, best-effort


class TaskSource(StrEnum):
    """Source of task request."""

    USER = "user"  # Direct user request
    AGENT = "agent"  # Another agent via A2A
    SYSTEM = "system"  # System-generated (health checks, monitoring)


class TaskState(StrEnum):
    """Task execution state."""

    PENDING = "pending"  # Waiting to execute
    IN_PROGRESS = "in_progress"  # Currently executing
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed execution
    EXPIRED = "expired"  # Deadline/expiration passed
    CANCELLED = "cancelled"  # Manually cancelled


class Task(BaseModel):
    """An immediate execution request.

    Tasks differ from missions in that they:
    - Execute ASAP (not scheduled)
    - Have explicit priorities
    - Expire automatically
    - Can interrupt running missions
    """

    id: str = Field(default_factory=lambda: ulid.new().str)
    description: str = Field(..., min_length=1, max_length=2000)

    # Priority and scheduling
    priority: Priority = Priority.NORMAL
    state: TaskState = TaskState.PENDING

    # Source tracking
    source: TaskSource = TaskSource.USER
    requester_agent_id: str | None = None  # If source=AGENT, who requested it

    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    deadline: datetime | None = None  # Must complete by this time
    expires_at: datetime  # Auto-expire (default: 24h)

    # Context
    context: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    # Results
    result: dict[str, Any] | None = None
    error: str | None = None

    def __init__(self, **data):
        """Initialize with default expiration if not provided."""
        if "expires_at" not in data:
            data["expires_at"] = datetime.now() + timedelta(hours=24)
        super().__init__(**data)

    def start(self) -> None:
        """Mark task as started."""
        self.state = TaskState.IN_PROGRESS
        self.started_at = datetime.now()
        logger.debug(f"Task {self.id[:8]} started")

    def complete(self, result: dict[str, Any] | None = None) -> None:
        """Mark task as completed."""
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
        logger.info(f"Task {self.id[:8]} completed")

    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.state = TaskState.FAILED
        self.completed_at = datetime.now()
        self.error = error
        logger.error(f"Task {self.id[:8]} failed: {error}")

    def cancel(self) -> None:
        """Cancel task execution."""
        self.state = TaskState.CANCELLED
        self.completed_at = datetime.now()
        logger.info(f"Task {self.id[:8]} cancelled")

    def is_expired(self) -> bool:
        """Check if task has expired."""
        return datetime.now() >= self.expires_at

    def is_past_deadline(self) -> bool:
        """Check if task is past its deadline."""
        if self.deadline is None:
            return False
        return datetime.now() >= self.deadline


class TaskStore:
    """SQLite-backed task storage with priority queuing.

    Stores tasks for immediate execution with:
    - Priority-based retrieval
    - Automatic expiration cleanup
    - Deadline tracking
    - Source tracking for A2A
    """

    def __init__(self, path: Path | str | None = None) -> None:
        """Initialize task store.

        Args:
            path: Path to SQLite database file (default: ~/.forge/tasks.db)
        """
        self.path = Path(path) if path else Path.home() / ".forge" / "tasks.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                priority INTEGER NOT NULL,
                state TEXT NOT NULL,
                source TEXT NOT NULL,
                requester_agent_id TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                deadline TEXT,
                expires_at TEXT NOT NULL,
                context TEXT DEFAULT '{}',
                tags TEXT DEFAULT '[]',
                result TEXT,
                error TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC, created_at ASC);
            CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
            CREATE INDEX IF NOT EXISTS idx_tasks_expires_at ON tasks(expires_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
        """)
        self.db.commit()

    async def create(self, task: Task) -> str:
        """Create a new task.

        Args:
            task: Task to create

        Returns:
            Task ID
        """
        self.db.execute(
            """INSERT INTO tasks (
                id, description, priority, state, source, requester_agent_id,
                created_at, started_at, completed_at, deadline, expires_at,
                context, tags, result, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.id,
                task.description,
                task.priority.value,
                task.state.value,
                task.source.value,
                task.requester_agent_id,
                task.created_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                task.deadline.isoformat() if task.deadline else None,
                task.expires_at.isoformat(),
                json.dumps(task.context),
                json.dumps(task.tags),
                json.dumps(task.result) if task.result else None,
                task.error,
            ),
        )
        self.db.commit()
        logger.info(
            f"Created task {task.id[:8]} (priority={task.priority.name}): {task.description[:50]}..."
        )
        return task.id

    async def get(self, task_id: str) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        row = self.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        return self._row_to_task(row)

    async def update(self, task: Task) -> bool:
        """Update a task.

        Args:
            task: Task to update

        Returns:
            True if updated, False if not found
        """
        cursor = self.db.execute(
            """UPDATE tasks SET
                description = ?, priority = ?, state = ?, source = ?, requester_agent_id = ?,
                started_at = ?, completed_at = ?, deadline = ?, expires_at = ?,
                context = ?, tags = ?, result = ?, error = ?
            WHERE id = ?""",
            (
                task.description,
                task.priority.value,
                task.state.value,
                task.source.value,
                task.requester_agent_id,
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                task.deadline.isoformat() if task.deadline else None,
                task.expires_at.isoformat(),
                json.dumps(task.context),
                json.dumps(task.tags),
                json.dumps(task.result) if task.result else None,
                task.error,
                task.id,
            ),
        )
        self.db.commit()
        updated = cursor.rowcount > 0
        if updated:
            logger.debug(f"Updated task {task.id[:8]}")
        return updated

    async def delete(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        cursor = self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.db.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted task {task_id[:8]}")
        return deleted

    async def get_by_priority(
        self, min_priority: Priority, *, state: TaskState = TaskState.PENDING, limit: int = 10
    ) -> list[Task]:
        """Get tasks by minimum priority level.

        Args:
            min_priority: Minimum priority level
            state: Filter by state (default: PENDING)
            limit: Maximum tasks to return

        Returns:
            List of tasks ordered by priority (highest first), then creation time
        """
        rows = self.db.execute(
            """SELECT * FROM tasks
               WHERE priority >= ? AND state = ?
               ORDER BY priority DESC, created_at ASC
               LIMIT ?""",
            (min_priority.value, state.value, limit),
        ).fetchall()
        return [self._row_to_task(row) for row in rows]

    async def get_pending(self, *, limit: int = 10) -> list[Task]:
        """Get pending tasks ordered by priority.

        Args:
            limit: Maximum tasks to return

        Returns:
            List of pending tasks ordered by priority (highest first)
        """
        rows = self.db.execute(
            """SELECT * FROM tasks
               WHERE state = ?
               ORDER BY priority DESC, created_at ASC
               LIMIT ?""",
            (TaskState.PENDING.value, limit),
        ).fetchall()
        return [self._row_to_task(row) for row in rows]

    async def get_past_deadline(self) -> list[Task]:
        """Get tasks past their deadline.

        Returns:
            List of tasks past deadline
        """
        now = datetime.now().isoformat()
        rows = self.db.execute(
            """SELECT * FROM tasks
               WHERE state = ? AND deadline IS NOT NULL AND deadline < ?
               ORDER BY deadline ASC""",
            (TaskState.PENDING.value, now),
        ).fetchall()
        return [self._row_to_task(row) for row in rows]

    async def cleanup_expired(self) -> int:
        """Delete expired and old completed tasks.

        Returns:
            Number of tasks deleted
        """
        now = datetime.now().isoformat()

        # Delete expired tasks
        cursor = self.db.execute(
            "DELETE FROM tasks WHERE expires_at < ?",
            (now,),
        )
        deleted_count = cursor.rowcount

        # Delete old completed/failed tasks (older than 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor = self.db.execute(
            """DELETE FROM tasks
               WHERE state IN (?, ?, ?) AND completed_at < ?""",
            (
                TaskState.COMPLETED.value,
                TaskState.FAILED.value,
                TaskState.CANCELLED.value,
                week_ago,
            ),
        )
        deleted_count += cursor.rowcount

        self.db.commit()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired/old tasks")

        return deleted_count

    async def count(self, state: TaskState | None = None) -> int:
        """Count tasks.

        Args:
            state: Filter by state (optional)

        Returns:
            Number of tasks
        """
        if state:
            row = self.db.execute(
                "SELECT COUNT(*) FROM tasks WHERE state = ?", (state.value,)
            ).fetchone()
        else:
            row = self.db.execute("SELECT COUNT(*) FROM tasks").fetchone()
        return row[0]

    async def list_all(
        self, *, state: TaskState | None = None, limit: int = 100, offset: int = 0
    ) -> list[Task]:
        """List all tasks.

        Args:
            state: Filter by state (optional)
            limit: Maximum tasks to return
            offset: Pagination offset

        Returns:
            List of tasks ordered by priority, then creation time
        """
        if state:
            rows = self.db.execute(
                """SELECT * FROM tasks WHERE state = ?
                   ORDER BY priority DESC, created_at DESC
                   LIMIT ? OFFSET ?""",
                (state.value, limit, offset),
            ).fetchall()
        else:
            rows = self.db.execute(
                """SELECT * FROM tasks
                   ORDER BY priority DESC, created_at DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object."""
        return Task(
            id=row["id"],
            description=row["description"],
            priority=Priority(row["priority"]),
            state=TaskState(row["state"]),
            source=TaskSource(row["source"]),
            requester_agent_id=row["requester_agent_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
            deadline=datetime.fromisoformat(row["deadline"]) if row["deadline"] else None,
            expires_at=datetime.fromisoformat(row["expires_at"]),
            context=json.loads(row["context"]),
            tags=json.loads(row["tags"]),
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
        )

    def close(self) -> None:
        """Close the database connection."""
        self.db.close()

"""Persistent mission storage for autonomous agents.

Missions are long-running objectives that survive restarts and execute on a schedule.
They are the foundation of autonomous agent behavior.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import ulid
from pydantic import BaseModel, Field, field_validator

# Import Priority from tasks for interrupt_threshold
from teotl.primitives.tasks.persistent import Priority

logger = logging.getLogger(__name__)


class MissionState(StrEnum):
    """Mission execution state."""

    ACTIVE = "active"  # Mission is running on schedule
    PAUSED = "paused"  # Mission execution is paused
    COMPLETED = "completed"  # Mission was successfully completed
    FAILED = "failed"  # Mission failed and is not retrying
    CANCELLED = "cancelled"  # Mission was manually cancelled


class MissionInterval(StrEnum):
    """Mission execution interval."""

    ONCE = "once"  # Execute once immediately
    MINUTES_5 = "minutes_5"  # Execute every 5 minutes
    MINUTES_10 = "minutes_10"  # Execute every 10 minutes
    MINUTES_30 = "minutes_30"  # Execute every 30 minutes
    HOURLY = "hourly"  # Execute every hour
    DAILY = "daily"  # Execute once per day
    WEEKLY = "weekly"  # Execute once per week
    MANUAL = "manual"  # Only execute when manually triggered


class MissionBudget(BaseModel):
    """Execution budget limits for a mission."""

    max_api_calls: int | None = None  # Maximum API calls per execution
    max_cost_usd: float | None = None  # Maximum cost in USD per execution
    max_duration_seconds: int | None = None  # Maximum execution time

    def is_exceeded(self, api_calls: int, cost_usd: float, duration_seconds: int) -> bool:
        """Check if any budget limit is exceeded."""
        if self.max_api_calls and api_calls >= self.max_api_calls:
            return True
        if self.max_cost_usd and cost_usd >= self.max_cost_usd:
            return True
        return bool(self.max_duration_seconds and duration_seconds >= self.max_duration_seconds)


class MissionExecution(BaseModel):
    """Record of a single mission execution."""

    id: str = Field(default_factory=lambda: ulid.new().str)
    mission_id: str
    started_at: datetime
    completed_at: datetime | None = None
    state: MissionState
    api_calls: int = 0
    cost_usd: float = 0.0
    duration_seconds: int = 0
    error: str | None = None
    result: str | None = None


class Mission(BaseModel):
    """A persistent mission for autonomous execution.

    Missions are long-running objectives that:
    - Survive agent restarts
    - Execute on a schedule (hourly, daily, weekly)
    - Have budget limits (API calls, cost, time)
    - Track execution history
    - Support pause/resume/cancel
    - Can be interrupted by high-priority tasks
    - Support multi-agent delegation
    """

    id: str = Field(default_factory=lambda: ulid.new().str)
    description: str = Field(..., min_length=1, max_length=2000)
    state: MissionState = MissionState.ACTIVE
    interval: MissionInterval = MissionInterval.MANUAL
    budget: MissionBudget = Field(default_factory=MissionBudget)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_executed_at: datetime | None = None
    next_execution_at: datetime | None = None

    # Execution tracking
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    # Multi-agent support
    originator_agent_id: str | None = None  # Who created this mission (rollup target)
    current_agent_id: str | None = None  # Who is executing it now
    parent_mission_id: str | None = None  # If delegated, link to parent
    delegation_chain: list[str] = Field(default_factory=list)  # Track full delegation path

    # Interruption control
    can_be_interrupted: bool = True  # Can pause for urgent tasks
    interrupt_threshold: Priority = Priority.URGENT  # What priority interrupts this

    # Context
    context: dict[str, Any] = Field(default_factory=dict)  # Additional context for execution
    tags: list[str] = Field(default_factory=list)  # Tags for organization

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is not empty."""
        if not v.strip():
            raise ValueError("Mission description cannot be empty")
        return v.strip()

    def pause(self) -> None:
        """Pause mission execution."""
        if self.state == MissionState.ACTIVE:
            self.state = MissionState.PAUSED
            self.updated_at = datetime.now()
            logger.info(f"Mission {self.id[:8]} paused")

    def resume(self) -> None:
        """Resume mission execution."""
        if self.state == MissionState.PAUSED:
            self.state = MissionState.ACTIVE
            self.updated_at = datetime.now()
            logger.info(f"Mission {self.id[:8]} resumed")

    def complete(self) -> None:
        """Mark mission as completed."""
        self.state = MissionState.COMPLETED
        self.updated_at = datetime.now()
        logger.info(f"Mission {self.id[:8]} completed")

    def fail(self, error: str | None = None) -> None:
        """Mark mission as failed."""
        self.state = MissionState.FAILED
        self.updated_at = datetime.now()
        if error:
            logger.error(f"Mission {self.id[:8]} failed: {error}")
        else:
            logger.error(f"Mission {self.id[:8]} failed")

    def cancel(self) -> None:
        """Cancel mission execution."""
        self.state = MissionState.CANCELLED
        self.updated_at = datetime.now()
        logger.info(f"Mission {self.id[:8]} cancelled")


class MissionStore:
    """SQLite-backed persistent mission storage.

    Stores missions and their execution history for autonomous agents.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        """Initialize mission store.

        Args:
            path: Path to SQLite database file (default: ~/.forge/missions.db)
        """
        self.path = Path(path) if path else Path.home() / ".forge" / "missions.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                state TEXT NOT NULL,
                interval TEXT NOT NULL,
                budget_max_api_calls INTEGER,
                budget_max_cost_usd REAL,
                budget_max_duration_seconds INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_executed_at TEXT,
                next_execution_at TEXT,
                execution_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                originator_agent_id TEXT,
                current_agent_id TEXT,
                parent_mission_id TEXT,
                delegation_chain TEXT DEFAULT '[]',
                can_be_interrupted INTEGER DEFAULT 1,
                interrupt_threshold INTEGER DEFAULT 4,
                context TEXT DEFAULT '{}',
                tags TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS mission_executions (
                id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                state TEXT NOT NULL,
                api_calls INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                duration_seconds INTEGER DEFAULT 0,
                error TEXT,
                result TEXT,
                FOREIGN KEY (mission_id) REFERENCES missions (id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_missions_state ON missions(state);
            CREATE INDEX IF NOT EXISTS idx_missions_next_execution ON missions(next_execution_at);
            CREATE INDEX IF NOT EXISTS idx_executions_mission_id ON mission_executions(mission_id);
            CREATE INDEX IF NOT EXISTS idx_executions_started_at ON mission_executions(started_at);
        """)
        self.db.commit()

    async def create(self, mission: Mission) -> str:
        """Create a new mission.

        Args:
            mission: Mission to create

        Returns:
            Mission ID
        """
        self.db.execute(
            """INSERT INTO missions (
                id, description, state, interval,
                budget_max_api_calls, budget_max_cost_usd, budget_max_duration_seconds,
                created_at, updated_at, last_executed_at, next_execution_at,
                execution_count, success_count, failure_count,
                originator_agent_id, current_agent_id, parent_mission_id, delegation_chain,
                can_be_interrupted, interrupt_threshold,
                context, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mission.id,
                mission.description,
                mission.state.value,
                mission.interval.value,
                mission.budget.max_api_calls,
                mission.budget.max_cost_usd,
                mission.budget.max_duration_seconds,
                mission.created_at.isoformat(),
                mission.updated_at.isoformat(),
                mission.last_executed_at.isoformat() if mission.last_executed_at else None,
                mission.next_execution_at.isoformat() if mission.next_execution_at else None,
                mission.execution_count,
                mission.success_count,
                mission.failure_count,
                mission.originator_agent_id,
                mission.current_agent_id,
                mission.parent_mission_id,
                json.dumps(mission.delegation_chain),
                1 if mission.can_be_interrupted else 0,
                mission.interrupt_threshold.value,
                json.dumps(mission.context),
                json.dumps(mission.tags),
            ),
        )
        self.db.commit()
        logger.info(f"Created mission {mission.id[:8]}: {mission.description[:50]}...")
        return mission.id

    async def get(self, mission_id: str) -> Mission | None:
        """Get a mission by ID.

        Args:
            mission_id: Mission ID

        Returns:
            Mission if found, None otherwise
        """
        row = self.db.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
        if not row:
            return None
        return self._row_to_mission(row)

    async def update(self, mission: Goal) -> bool:
        """Update a mission.

        Args:
            mission: Mission to update

        Returns:
            True if updated, False if not found
        """
        mission.updated_at = datetime.now()
        cursor = self.db.execute(
            """UPDATE missions SET
                description = ?, state = ?, interval = ?,
                budget_max_api_calls = ?, budget_max_cost_usd = ?, budget_max_duration_seconds = ?,
                updated_at = ?, last_executed_at = ?, next_execution_at = ?,
                execution_count = ?, success_count = ?, failure_count = ?,
                originator_agent_id = ?, current_agent_id = ?, parent_mission_id = ?, delegation_chain = ?,
                can_be_interrupted = ?, interrupt_threshold = ?,
                context = ?, tags = ?
            WHERE id = ?""",
            (
                mission.description,
                mission.state.value,
                mission.interval.value,
                mission.budget.max_api_calls,
                mission.budget.max_cost_usd,
                mission.budget.max_duration_seconds,
                mission.updated_at.isoformat(),
                mission.last_executed_at.isoformat() if mission.last_executed_at else None,
                mission.next_execution_at.isoformat() if mission.next_execution_at else None,
                mission.execution_count,
                mission.success_count,
                mission.failure_count,
                mission.originator_agent_id,
                mission.current_agent_id,
                mission.parent_mission_id,
                json.dumps(mission.delegation_chain),
                1 if mission.can_be_interrupted else 0,
                mission.interrupt_threshold.value,
                json.dumps(mission.context),
                json.dumps(mission.tags),
                mission.id,
            ),
        )
        self.db.commit()
        updated = cursor.rowcount > 0
        if updated:
            logger.debug(f"Updated mission {mission.id[:8]}")
        return updated

    async def delete(self, mission_id: str) -> bool:
        """Delete a mission.

        Args:
            mission_id: Mission ID

        Returns:
            True if deleted, False if not found
        """
        cursor = self.db.execute("DELETE FROM missions WHERE id = ?", (mission_id,))
        self.db.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted mission {mission_id[:8]}")
        return deleted

    async def list_all(
        self, *, state: MissionState | None = None, limit: int = 100, offset: int = 0
    ) -> list[Mission]:
        """List all missions.

        Args:
            state: Filter by state (optional)
            limit: Maximum number of goals to return
            offset: Pagination offset

        Returns:
            List of goals
        """
        if state:
            rows = self.db.execute(
                "SELECT * FROM missions WHERE state = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (state.value, limit, offset),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM missions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_mission(row) for row in rows]

    async def list_active(self) -> list[Mission]:
        """List all active missions.

        Returns:
            List of active goals
        """
        return await self.list_all(state=MissionState.ACTIVE)

    async def list_due(self) -> list[Mission]:
        """List all missions due for execution.

        Returns:
            List of missions due for execution
        """
        now = datetime.now().isoformat()
        rows = self.db.execute(
            """SELECT * FROM missions
               WHERE state = ? AND next_execution_at IS NOT NULL AND next_execution_at <= ?
               ORDER BY next_execution_at ASC""",
            (MissionState.ACTIVE.value, now),
        ).fetchall()
        return [self._row_to_mission(row) for row in rows]

    async def count(self, state: MissionState | None = None) -> int:
        """Count missions.

        Args:
            state: Filter by state (optional)

        Returns:
            Number of goals
        """
        if state:
            row = self.db.execute(
                "SELECT COUNT(*) FROM missions WHERE state = ?", (state.value,)
            ).fetchone()
        else:
            row = self.db.execute("SELECT COUNT(*) FROM missions").fetchone()
        return row[0]

    async def record_execution(self, execution: MissionExecution) -> str:
        """Record a mission execution.

        Args:
            execution: Execution record

        Returns:
            Execution ID
        """
        self.db.execute(
            """INSERT INTO mission_executions (
                id, mission_id, started_at, completed_at, state,
                api_calls, cost_usd, duration_seconds, error, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                execution.id,
                execution.mission_id,
                execution.started_at.isoformat(),
                execution.completed_at.isoformat() if execution.completed_at else None,
                execution.state.value,
                execution.api_calls,
                execution.cost_usd,
                execution.duration_seconds,
                execution.error,
                execution.result,
            ),
        )
        self.db.commit()
        logger.debug(
            f"Recorded execution {execution.id[:8]} for mission {execution.mission_id[:8]}"
        )
        return execution.id

    async def get_executions(self, mission_id: str, *, limit: int = 10) -> list[MissionExecution]:
        """Get execution history for a mission.

        Args:
            mission_id: Mission ID
            limit: Maximum number of executions to return

        Returns:
            List of executions
        """
        rows = self.db.execute(
            """SELECT * FROM mission_executions
               WHERE mission_id = ?
               ORDER BY started_at DESC
               LIMIT ?""",
            (mission_id, limit),
        ).fetchall()
        return [self._row_to_execution(row) for row in rows]

    def _row_to_mission(self, row: sqlite3.Row) -> Mission:
        """Convert database row to Mission object."""
        # Handle backward compatibility for databases without new fields
        can_be_interrupted = (
            bool(row["can_be_interrupted"]) if "can_be_interrupted" in row.keys() else True
        )
        interrupt_threshold = (
            Priority(row["interrupt_threshold"])
            if "interrupt_threshold" in row.keys()
            else Priority.URGENT
        )

        return Mission(
            id=row["id"],
            description=row["description"],
            state=MissionState(row["state"]),
            interval=MissionInterval(row["interval"]),
            budget=MissionBudget(
                max_api_calls=row["budget_max_api_calls"],
                max_cost_usd=row["budget_max_cost_usd"],
                max_duration_seconds=row["budget_max_duration_seconds"],
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_executed_at=(
                datetime.fromisoformat(row["last_executed_at"]) if row["last_executed_at"] else None
            ),
            next_execution_at=(
                datetime.fromisoformat(row["next_execution_at"])
                if row["next_execution_at"]
                else None
            ),
            execution_count=row["execution_count"],
            success_count=row["success_count"],
            failure_count=row["failure_count"],
            originator_agent_id=row["originator_agent_id"]
            if "originator_agent_id" in row.keys()
            else None,
            current_agent_id=row["current_agent_id"] if "current_agent_id" in row.keys() else None,
            parent_mission_id=row["parent_mission_id"] if "parent_mission_id" in row.keys() else None,
            delegation_chain=json.loads(row["delegation_chain"])
            if "delegation_chain" in row.keys()
            else [],
            can_be_interrupted=can_be_interrupted,
            interrupt_threshold=interrupt_threshold,
            context=json.loads(row["context"]),
            tags=json.loads(row["tags"]),
        )

    def _row_to_execution(self, row: sqlite3.Row) -> MissionExecution:
        """Convert database row to MissionExecution object."""
        return MissionExecution(
            id=row["id"],
            mission_id=row["mission_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
            ),
            state=MissionState(row["state"]),
            api_calls=row["api_calls"],
            cost_usd=row["cost_usd"],
            duration_seconds=row["duration_seconds"],
            error=row["error"],
            result=row["result"],
        )

    def close(self) -> None:
        """Close the database connection."""
        self.db.close()

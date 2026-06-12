"""Tests for persistent mission storage."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from teotl.primitives.missions import (
    Mission,
    MissionBudget,
    MissionExecution,
    MissionInterval,
    MissionState,
    MissionStore,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_missions.db"


@pytest.fixture
async def store(temp_db):
    """Create a mission store for testing."""
    store = MissionStore(temp_db)
    yield store
    store.close()


@pytest.mark.asyncio
async def test_create_mission(store):
    """Test creating a mission."""
    mission = Mission(
        description="Test mission",
        interval=MissionInterval.DAILY,
        budget=MissionBudget(max_api_calls=100, max_cost_usd=1.0),
    )

    mission_id = await store.create(mission)
    assert mission_id == mission.id

    # Verify it was stored
    retrieved = await store.get(mission_id)
    assert retrieved is not None
    assert retrieved.description == "Test mission"
    assert retrieved.state == MissionState.ACTIVE
    assert retrieved.interval == MissionInterval.DAILY
    assert retrieved.budget.max_api_calls == 100
    assert retrieved.budget.max_cost_usd == 1.0


@pytest.mark.asyncio
async def test_update_mission(store):
    """Test updating a mission."""
    mission = Mission(description="Original description")
    await store.create(mission)

    # Update description
    mission.description = "Updated description"
    updated = await store.update(mission)
    assert updated is True

    # Verify update
    retrieved = await store.get(mission.id)
    assert retrieved.description == "Updated description"
    assert retrieved.updated_at > retrieved.created_at


@pytest.mark.asyncio
async def test_delete_mission(store):
    """Test deleting a mission."""
    mission = Mission(description="Test mission")
    await store.create(mission)

    # Delete mission
    deleted = await store.delete(mission.id)
    assert deleted is True

    # Verify deletion
    retrieved = await store.get(mission.id)
    assert retrieved is None

    # Deleting again returns False
    deleted_again = await store.delete(mission.id)
    assert deleted_again is False


@pytest.mark.asyncio
async def test_list_all_missions(store):
    """Test listing all missions."""
    # Create multiple missions
    mission1 = Mission(description="Goal 1")
    mission2 = Mission(description="Goal 2")
    mission3 = Mission(description="Goal 3")

    await store.create(mission1)
    await store.create(mission2)
    await store.create(mission3)

    # List all
    missions = await store.list_all()
    assert len(missions) == 3

    # Check pagination
    missions_page1 = await store.list_all(limit=2, offset=0)
    assert len(missions_page1) == 2

    missions_page2 = await store.list_all(limit=2, offset=2)
    assert len(missions_page2) == 1


@pytest.mark.asyncio
async def test_list_by_state(store):
    """Test listing missions filtered by state."""
    # Create missions with different states
    mission1 = Mission(description="Active mission", state=MissionState.ACTIVE)
    mission2 = Mission(description="Paused mission", state=MissionState.PAUSED)
    mission3 = Mission(description="Completed mission", state=MissionState.COMPLETED)

    await store.create(mission1)
    await store.create(mission2)
    await store.create(mission3)

    # List active missions
    active = await store.list_all(state=MissionState.ACTIVE)
    assert len(active) == 1
    assert active[0].description == "Active mission"

    # List paused missions
    paused = await store.list_all(state=MissionState.PAUSED)
    assert len(paused) == 1
    assert paused[0].description == "Paused mission"


@pytest.mark.asyncio
async def test_list_active_missions(store):
    """Test listing active missions."""
    # Create missions with different states
    await store.create(Mission(description="Active 1", state=MissionState.ACTIVE))
    await store.create(Mission(description="Active 2", state=MissionState.ACTIVE))
    await store.create(Mission(description="Paused", state=MissionState.PAUSED))
    await store.create(Mission(description="Completed", state=MissionState.COMPLETED))

    # List active only
    active = await store.list_active()
    assert len(active) == 2


@pytest.mark.asyncio
async def test_list_due_missions(store):
    """Test listing missions due for execution."""
    now = datetime.now()

    # Create missions with different execution times
    mission1 = Mission(description="Due now", next_execution_at=now - timedelta(hours=1))
    mission2 = Mission(description="Due later", next_execution_at=now + timedelta(hours=1))
    mission3 = Mission(description="No schedule")

    await store.create(mission1)
    await store.create(mission2)
    await store.create(mission3)

    # List due missions
    due = await store.list_due()
    assert len(due) == 1
    assert due[0].description == "Due now"


@pytest.mark.asyncio
async def test_count_missions(store):
    """Test counting missions."""
    await store.create(Mission(description="Goal 1", state=MissionState.ACTIVE))
    await store.create(Mission(description="Goal 2", state=MissionState.ACTIVE))
    await store.create(Mission(description="Goal 3", state=MissionState.PAUSED))

    # Count all
    total = await store.count()
    assert total == 3

    # Count by state
    active_count = await store.count(state=MissionState.ACTIVE)
    assert active_count == 2

    paused_count = await store.count(state=MissionState.PAUSED)
    assert paused_count == 1


@pytest.mark.asyncio
async def test_mission_lifecycle(store):
    """Test mission lifecycle methods."""
    mission = Mission(description="Test mission", state=MissionState.ACTIVE)
    await store.create(mission)

    # Pause
    mission.pause()
    assert mission.state == MissionState.PAUSED
    await store.update(mission)

    retrieved = await store.get(mission.id)
    assert retrieved.state == MissionState.PAUSED

    # Resume
    mission.resume()
    assert mission.state == MissionState.ACTIVE
    await store.update(mission)

    # Complete
    mission.complete()
    assert mission.state == MissionState.COMPLETED
    await store.update(mission)

    retrieved = await store.get(mission.id)
    assert retrieved.state == MissionState.COMPLETED


@pytest.mark.asyncio
async def test_mission_fail(store):
    """Test marking mission as failed."""
    mission = Mission(description="Test mission")
    await store.create(mission)

    mission.fail("Test error")
    assert mission.state == MissionState.FAILED
    await store.update(mission)

    retrieved = await store.get(mission.id)
    assert retrieved.state == MissionState.FAILED


@pytest.mark.asyncio
async def test_mission_cancel(store):
    """Test cancelling a mission."""
    mission = Mission(description="Test mission")
    await store.create(mission)

    mission.cancel()
    assert mission.state == MissionState.CANCELLED
    await store.update(mission)

    retrieved = await store.get(mission.id)
    assert retrieved.state == MissionState.CANCELLED


@pytest.mark.asyncio
async def test_mission_budget_exceeded(store):
    """Test budget exceeded check."""
    budget = MissionBudget(max_api_calls=10, max_cost_usd=1.0, max_duration_seconds=60)

    # Not exceeded
    assert not budget.is_exceeded(api_calls=5, cost_usd=0.5, duration_seconds=30)

    # API calls exceeded
    assert budget.is_exceeded(api_calls=10, cost_usd=0.5, duration_seconds=30)

    # Cost exceeded
    assert budget.is_exceeded(api_calls=5, cost_usd=1.0, duration_seconds=30)

    # Duration exceeded
    assert budget.is_exceeded(api_calls=5, cost_usd=0.5, duration_seconds=60)


@pytest.mark.asyncio
async def test_record_execution(store):
    """Test recording mission execution."""
    mission = Mission(description="Test mission")
    await store.create(mission)

    # Record execution
    execution = MissionExecution(
        mission_id=mission.id,
        started_at=datetime.now(),
        completed_at=datetime.now(),
        state=MissionState.COMPLETED,
        api_calls=5,
        cost_usd=0.25,
        duration_seconds=10,
        result="Success",
    )

    exec_id = await store.record_execution(execution)
    assert exec_id == execution.id

    # Get executions
    executions = await store.get_executions(mission.id)
    assert len(executions) == 1
    assert executions[0].api_calls == 5
    assert executions[0].cost_usd == 0.25
    assert executions[0].result == "Success"


@pytest.mark.asyncio
async def test_execution_history(store):
    """Test getting execution history."""
    mission = Mission(description="Test mission")
    await store.create(mission)

    # Record multiple executions
    for i in range(5):
        execution = MissionExecution(
            mission_id=mission.id,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            state=MissionState.COMPLETED,
            api_calls=i + 1,
        )
        await store.record_execution(execution)

    # Get history (limited)
    executions = await store.get_executions(mission.id, limit=3)
    assert len(executions) == 3

    # Most recent first
    assert executions[0].api_calls > executions[1].api_calls


@pytest.mark.asyncio
async def test_mission_context(store):
    """Test mission context storage."""
    mission = Mission(
        description="Test mission",
        context={"user_id": "123", "preferences": {"theme": "dark"}},
        tags=["important", "recurring"],
    )

    await store.create(mission)

    # Verify context is preserved
    retrieved = await store.get(mission.id)
    assert retrieved.context == {"user_id": "123", "preferences": {"theme": "dark"}}
    assert retrieved.tags == ["important", "recurring"]


@pytest.mark.asyncio
async def test_mission_validation(store):
    """Test mission validation."""
    # Empty description should be trimmed and raise error
    with pytest.raises(ValueError, match="cannot be empty"):
        Mission(description="   ")

    # Valid description with whitespace gets trimmed
    mission = Mission(description="  Test mission  ")
    assert mission.description == "Test mission"


@pytest.mark.asyncio
async def test_execution_with_error(store):
    """Test recording execution with error."""
    mission = Mission(description="Test mission")
    await store.create(mission)

    execution = MissionExecution(
        mission_id=mission.id,
        started_at=datetime.now(),
        completed_at=datetime.now(),
        state=MissionState.FAILED,
        error="Test error message",
    )

    await store.record_execution(execution)

    executions = await store.get_executions(mission.id)
    assert len(executions) == 1
    assert executions[0].state == MissionState.FAILED
    assert executions[0].error == "Test error message"


@pytest.mark.asyncio
async def test_mission_intervals(store):
    """Test different mission intervals."""
    intervals = [
        MissionInterval.ONCE,
        MissionInterval.HOURLY,
        MissionInterval.DAILY,
        MissionInterval.WEEKLY,
        MissionInterval.MANUAL,
    ]

    for interval in intervals:
        mission = Mission(description=f"Goal with {interval.value} interval", interval=interval)
        await store.create(mission)

        retrieved = await store.get(mission.id)
        assert retrieved.interval == interval

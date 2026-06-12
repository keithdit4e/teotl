"""Tests for persistent task storage."""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from teotl.primitives.tasks import Priority, Task, TaskSource, TaskState, TaskStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_tasks.db"


@pytest.fixture
async def store(temp_db):
    """Create a task store for testing."""
    store = TaskStore(temp_db)
    yield store
    store.close()


@pytest.mark.asyncio
async def test_create_task(store):
    """Test creating a task."""
    task = Task(
        description="Test task",
        priority=Priority.HIGH,
        source=TaskSource.USER,
    )

    task_id = await store.create(task)
    assert task_id == task.id

    # Verify it was stored
    retrieved = await store.get(task_id)
    assert retrieved is not None
    assert retrieved.description == "Test task"
    assert retrieved.priority == Priority.HIGH
    assert retrieved.state == TaskState.PENDING
    assert retrieved.source == TaskSource.USER


@pytest.mark.asyncio
async def test_task_default_expiration(store):
    """Test that tasks get default 24h expiration."""
    task = Task(description="Test task")

    # Should have expiration ~24h from now
    assert task.expires_at is not None
    expected = datetime.now() + timedelta(hours=24)
    assert abs((task.expires_at - expected).total_seconds()) < 10  # Within 10 seconds


@pytest.mark.asyncio
async def test_task_custom_expiration(store):
    """Test custom expiration time."""
    custom_expiry = datetime.now() + timedelta(hours=2)
    task = Task(description="Test task", expires_at=custom_expiry)

    assert task.expires_at == custom_expiry


@pytest.mark.asyncio
async def test_update_task(store):
    """Test updating a task."""
    task = Task(description="Original description")
    await store.create(task)

    # Update description and state
    task.description = "Updated description"
    task.state = TaskState.IN_PROGRESS
    updated = await store.update(task)
    assert updated is True

    # Verify update
    retrieved = await store.get(task.id)
    assert retrieved.description == "Updated description"
    assert retrieved.state == TaskState.IN_PROGRESS


@pytest.mark.asyncio
async def test_delete_task(store):
    """Test deleting a task."""
    task = Task(description="Test task")
    await store.create(task)

    # Delete task
    deleted = await store.delete(task.id)
    assert deleted is True

    # Verify deletion
    retrieved = await store.get(task.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_by_priority(store):
    """Test retrieving tasks by priority."""
    # Create tasks with different priorities
    await store.create(Task(description="Low", priority=Priority.LOW))
    await store.create(Task(description="Normal", priority=Priority.NORMAL))
    await store.create(Task(description="High", priority=Priority.HIGH))
    await store.create(Task(description="Urgent", priority=Priority.URGENT))
    await store.create(Task(description="Critical", priority=Priority.CRITICAL))

    # Get URGENT and above
    urgent_tasks = await store.get_by_priority(Priority.URGENT)
    assert len(urgent_tasks) == 2
    assert urgent_tasks[0].priority == Priority.CRITICAL  # Highest first
    assert urgent_tasks[1].priority == Priority.URGENT

    # Get HIGH and above
    high_tasks = await store.get_by_priority(Priority.HIGH)
    assert len(high_tasks) == 3


@pytest.mark.asyncio
async def test_get_pending_ordered_by_priority(store):
    """Test pending tasks are ordered by priority."""
    # Create tasks in random order
    await store.create(Task(description="Normal", priority=Priority.NORMAL))
    await store.create(Task(description="Critical", priority=Priority.CRITICAL))
    await store.create(Task(description="Low", priority=Priority.LOW))
    await store.create(Task(description="Urgent", priority=Priority.URGENT))

    pending = await store.get_pending()
    assert len(pending) == 4

    # Should be ordered by priority (highest first)
    assert pending[0].priority == Priority.CRITICAL
    assert pending[1].priority == Priority.URGENT
    assert pending[2].priority == Priority.NORMAL
    assert pending[3].priority == Priority.LOW


@pytest.mark.asyncio
async def test_task_lifecycle(store):
    """Test task lifecycle methods."""
    task = Task(description="Test task")
    await store.create(task)

    # Start task
    task.start()
    assert task.state == TaskState.IN_PROGRESS
    assert task.started_at is not None
    await store.update(task)

    # Complete task
    task.complete(result={"status": "success"})
    assert task.state == TaskState.COMPLETED
    assert task.completed_at is not None
    assert task.result == {"status": "success"}
    await store.update(task)

    retrieved = await store.get(task.id)
    assert retrieved.state == TaskState.COMPLETED
    assert retrieved.result == {"status": "success"}


@pytest.mark.asyncio
async def test_task_fail(store):
    """Test task failure."""
    task = Task(description="Test task")
    await store.create(task)

    task.start()
    task.fail("Something went wrong")
    await store.update(task)

    retrieved = await store.get(task.id)
    assert retrieved.state == TaskState.FAILED
    assert retrieved.error == "Something went wrong"
    assert retrieved.completed_at is not None


@pytest.mark.asyncio
async def test_task_cancel(store):
    """Test task cancellation."""
    task = Task(description="Test task")
    await store.create(task)

    task.cancel()
    await store.update(task)

    retrieved = await store.get(task.id)
    assert retrieved.state == TaskState.CANCELLED
    assert retrieved.completed_at is not None


@pytest.mark.asyncio
async def test_task_expiration_check(store):
    """Test task expiration checking."""
    # Task that expires in past
    expired_task = Task(description="Expired", expires_at=datetime.now() - timedelta(hours=1))
    assert expired_task.is_expired() is True

    # Task that expires in future
    valid_task = Task(description="Valid", expires_at=datetime.now() + timedelta(hours=1))
    assert valid_task.is_expired() is False


@pytest.mark.asyncio
async def test_task_deadline_check(store):
    """Test task deadline checking."""
    # Task past deadline
    past_deadline = Task(description="Late", deadline=datetime.now() - timedelta(hours=1))
    assert past_deadline.is_past_deadline() is True

    # Task before deadline
    before_deadline = Task(description="On time", deadline=datetime.now() + timedelta(hours=1))
    assert before_deadline.is_past_deadline() is False

    # Task with no deadline
    no_deadline = Task(description="No deadline")
    assert no_deadline.is_past_deadline() is False


@pytest.mark.asyncio
async def test_get_past_deadline(store):
    """Test retrieving tasks past deadline."""
    # Create tasks with different deadlines
    await store.create(
        Task(description="Past deadline", deadline=datetime.now() - timedelta(hours=1))
    )
    await store.create(
        Task(description="Future deadline", deadline=datetime.now() + timedelta(hours=1))
    )
    await store.create(Task(description="No deadline"))

    past_deadline = await store.get_past_deadline()
    assert len(past_deadline) == 1
    assert past_deadline[0].description == "Past deadline"


@pytest.mark.asyncio
async def test_cleanup_expired(store):
    """Test cleanup of expired tasks."""
    # Create expired task
    await store.create(Task(description="Expired", expires_at=datetime.now() - timedelta(hours=1)))

    # Create old completed task (8 days ago)
    old_completed = Task(description="Old completed", state=TaskState.COMPLETED)
    old_completed.completed_at = datetime.now() - timedelta(days=8)
    await store.create(old_completed)

    # Create recent completed task
    await store.create(Task(description="Recent", state=TaskState.COMPLETED))

    # Create valid pending task
    await store.create(Task(description="Valid"))

    # Cleanup should remove 2 tasks (expired + old completed)
    deleted = await store.cleanup_expired()
    assert deleted == 2

    # Verify only valid tasks remain
    remaining = await store.list_all()
    assert len(remaining) == 2


@pytest.mark.asyncio
async def test_task_source_tracking(store):
    """Test task source tracking."""
    # User task
    user_task = Task(description="User task", source=TaskSource.USER)
    await store.create(user_task)

    # Agent task
    agent_task = Task(
        description="Agent task", source=TaskSource.AGENT, requester_agent_id="email-agent-1"
    )
    await store.create(agent_task)

    # System task
    system_task = Task(description="System task", source=TaskSource.SYSTEM)
    await store.create(system_task)

    # Verify source tracking
    retrieved_agent = await store.get(agent_task.id)
    assert retrieved_agent.source == TaskSource.AGENT
    assert retrieved_agent.requester_agent_id == "email-agent-1"


@pytest.mark.asyncio
async def test_task_context_and_tags(store):
    """Test task context and tags."""
    task = Task(
        description="Test task",
        context={"user_id": "123", "action": "send_email"},
        tags=["email", "urgent"],
    )
    await store.create(task)

    retrieved = await store.get(task.id)
    assert retrieved.context == {"user_id": "123", "action": "send_email"}
    assert retrieved.tags == ["email", "urgent"]


@pytest.mark.asyncio
async def test_count_tasks(store):
    """Test counting tasks."""
    await store.create(Task(description="Task 1", state=TaskState.PENDING))
    await store.create(Task(description="Task 2", state=TaskState.PENDING))
    await store.create(Task(description="Task 3", state=TaskState.COMPLETED))

    # Count all
    total = await store.count()
    assert total == 3

    # Count by state
    pending = await store.count(state=TaskState.PENDING)
    assert pending == 2

    completed = await store.count(state=TaskState.COMPLETED)
    assert completed == 1


@pytest.mark.asyncio
async def test_list_all_tasks(store):
    """Test listing all tasks."""
    # Create multiple tasks
    await store.create(Task(description="Task 1", priority=Priority.LOW))
    await store.create(Task(description="Task 2", priority=Priority.HIGH))
    await store.create(Task(description="Task 3", priority=Priority.NORMAL))

    # List all (should be ordered by priority)
    tasks = await store.list_all()
    assert len(tasks) == 3
    assert tasks[0].priority == Priority.HIGH  # Highest first

    # Test pagination
    page1 = await store.list_all(limit=2, offset=0)
    assert len(page1) == 2

    page2 = await store.list_all(limit=2, offset=2)
    assert len(page2) == 1


@pytest.mark.asyncio
async def test_priority_enum_ordering(store):
    """Test that priority enum values order correctly."""
    assert Priority.CRITICAL > Priority.URGENT
    assert Priority.URGENT > Priority.HIGH
    assert Priority.HIGH > Priority.NORMAL
    assert Priority.NORMAL > Priority.LOW

    # Verify numeric values
    assert Priority.CRITICAL.value == 5
    assert Priority.URGENT.value == 4
    assert Priority.HIGH.value == 3
    assert Priority.NORMAL.value == 2
    assert Priority.LOW.value == 1


@pytest.mark.asyncio
async def test_same_priority_ordered_by_creation(store):
    """Test that tasks with same priority are ordered by creation time."""
    # Create multiple HIGH priority tasks
    task1 = Task(description="First", priority=Priority.HIGH)
    await asyncio.sleep(0.01)  # Small delay to ensure different timestamps
    task2 = Task(description="Second", priority=Priority.HIGH)
    await asyncio.sleep(0.01)
    task3 = Task(description="Third", priority=Priority.HIGH)

    await store.create(task1)
    await store.create(task2)
    await store.create(task3)

    # Should be ordered by creation time (oldest first for same priority)
    tasks = await store.get_pending()
    assert tasks[0].description == "First"
    assert tasks[1].description == "Second"
    assert tasks[2].description == "Third"

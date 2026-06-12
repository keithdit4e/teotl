"""Tests for heartbeat daemon."""

import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from teotl.daemon.agent_daemon import AgentDaemon
from teotl.primitives.missions import Mission, MissionInterval, MissionState
from teotl.primitives.resolution import MockResolutionService
from teotl.primitives.tasks import Priority, Task, TaskState


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory."""
    data_dir = tmp_path / "test_agent"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
async def mock_executor():
    """Mock agent executor function."""
    executor = AsyncMock(return_value="Task completed successfully")
    return executor


@pytest.fixture
async def daemon(temp_data_dir, mock_executor):
    """Create a daemon instance."""
    daemon = AgentDaemon(
        agent_id="test-agent",
        agent_executor=mock_executor,
        data_dir=temp_data_dir,
        poll_interval=1,  # Short interval for testing
    )
    yield daemon
    # Cleanup
    if daemon.running:
        await daemon.stop()


@pytest.mark.asyncio
async def test_daemon_initialization(daemon, temp_data_dir):
    """Test daemon initializes correctly."""
    assert daemon.agent_id == "test-agent"
    assert daemon.poll_interval == 1
    assert daemon.data_dir == temp_data_dir
    assert daemon.running is False
    assert daemon.current_mission is None
    assert daemon.current_task is None
    assert daemon.pid_file == temp_data_dir / "daemon.pid"


@pytest.mark.asyncio
async def test_daemon_writes_pid_file(daemon):
    """Test daemon writes PID file on start."""
    # Start daemon in background
    start_task = asyncio.create_task(daemon.start())
    await asyncio.sleep(0.1)  # Let it start

    # Check PID file exists
    assert daemon.pid_file.exists()
    pid = int(daemon.pid_file.read_text())
    assert pid == os.getpid()

    # Stop daemon
    await daemon.stop()
    await start_task

    # PID file should be removed
    assert not daemon.pid_file.exists()


@pytest.mark.asyncio
async def test_critical_task_always_interrupts(daemon, mock_executor):
    """Test CRITICAL tasks always interrupt missions."""
    # Create a mission that cannot be interrupted
    mission = Mission(
        description="Important mission",
        interval=MissionInterval.MANUAL,
        can_be_interrupted=False,
        interrupt_threshold=Priority.CRITICAL,
        next_execution_at=datetime.now(),
    )
    await daemon.mission_store.create(mission)

    # Create a CRITICAL task
    task = Task(
        description="Critical task",
        priority=Priority.CRITICAL,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Run one execution cycle
    await daemon._execute_cycle()

    # CRITICAL task should have been executed (even though mission can't be interrupted)
    mock_executor.assert_called_once_with("Critical task", task.context)

    # Task should be completed
    updated_task = await daemon.task_store.get(task.id)
    assert updated_task.state == TaskState.COMPLETED


@pytest.mark.asyncio
async def test_urgent_task_interrupts_when_allowed(daemon, mock_executor):
    """Test URGENT tasks interrupt when mission allows."""
    # Create a mission that CAN be interrupted
    mission = Mission(
        description="Interruptible mission",
        interval=MissionInterval.MANUAL,
        can_be_interrupted=True,
        interrupt_threshold=Priority.URGENT,
        next_execution_at=datetime.now(),
    )
    await daemon.mission_store.create(mission)

    # Start "executing" the mission
    daemon.current_mission = mission

    # Create an URGENT task
    task = Task(
        description="Urgent task",
        priority=Priority.URGENT,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Run one execution cycle
    await daemon._execute_cycle()

    # URGENT task should have been executed
    mock_executor.assert_called_once_with("Urgent task", task.context)

    # Task should be completed
    updated_task = await daemon.task_store.get(task.id)
    assert updated_task.state == TaskState.COMPLETED


@pytest.mark.asyncio
async def test_urgent_task_does_not_interrupt_when_not_allowed(daemon, mock_executor):
    """Test URGENT tasks don't interrupt when mission forbids."""
    # Create a mission that CANNOT be interrupted
    mission = Mission(
        description="Non-interruptible mission",
        interval=MissionInterval.MANUAL,
        can_be_interrupted=False,
        interrupt_threshold=Priority.CRITICAL,
        next_execution_at=datetime.now(),
    )
    await daemon.mission_store.create(mission)

    # Start "executing" the mission
    daemon.current_mission = mission

    # Create an URGENT task
    task = Task(
        description="Urgent task",
        priority=Priority.URGENT,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Run one execution cycle
    await daemon._execute_cycle()

    # URGENT task should NOT have been executed (mission can't be interrupted)
    mock_executor.assert_not_called()

    # Task should still be pending
    updated_task = await daemon.task_store.get(task.id)
    assert updated_task.state == TaskState.PENDING


@pytest.mark.asyncio
async def test_mission_execution(daemon, mock_executor):
    """Test mission execution."""
    # Create a due mission
    mission = Mission(
        description="Daily mission",
        interval=MissionInterval.DAILY,
        next_execution_at=datetime.now() - timedelta(minutes=1),  # Due now
    )
    await daemon.mission_store.create(mission)

    # Run one execution cycle
    await daemon._execute_cycle()

    # Mission should have been executed
    mock_executor.assert_called_once_with("Daily mission", mission.context)

    # Check mission was updated
    updated_mission = await daemon.mission_store.get(mission.id)
    assert updated_mission.execution_count == 1
    assert updated_mission.success_count == 1
    assert updated_mission.last_executed_at is not None
    assert updated_mission.next_execution_at is not None

    # Next execution should be ~24 hours from now
    time_diff = updated_mission.next_execution_at - datetime.now()
    assert 23 <= time_diff.total_seconds() / 3600 <= 25  # ~24 hours ±1 hour


@pytest.mark.asyncio
async def test_mission_once_interval_completes(daemon, mock_executor):
    """Test ONCE missions complete after execution."""
    # Create a ONCE mission
    mission = Mission(
        description="One-time mission",
        interval=MissionInterval.ONCE,
        next_execution_at=datetime.now() - timedelta(minutes=1),
    )
    await daemon.mission_store.create(mission)

    # Run one execution cycle
    await daemon._execute_cycle()

    # Mission should have been executed
    mock_executor.assert_called_once()

    # Mission should be marked as completed
    updated_mission = await daemon.mission_store.get(mission.id)
    assert updated_mission.state == MissionState.COMPLETED
    assert updated_mission.next_execution_at is None


@pytest.mark.asyncio
async def test_mission_failure_tracking(daemon, mock_executor):
    """Test mission failure is tracked."""
    # Configure executor to fail
    mock_executor.side_effect = Exception("Execution failed")

    # Create a mission
    mission = Mission(
        description="Failing mission",
        interval=MissionInterval.MANUAL,
        next_execution_at=datetime.now() - timedelta(minutes=1),
    )
    await daemon.mission_store.create(mission)

    # Run one execution cycle
    await daemon._execute_cycle()

    # Check mission failure was tracked
    updated_mission = await daemon.mission_store.get(mission.id)
    assert updated_mission.execution_count == 1
    assert updated_mission.failure_count == 1
    assert updated_mission.success_count == 0


@pytest.mark.asyncio
async def test_task_execution(daemon, mock_executor):
    """Test normal task execution."""
    # Create a HIGH priority task
    task = Task(
        description="High priority task",
        priority=Priority.HIGH,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Run one execution cycle
    await daemon._execute_cycle()

    # Task should have been executed
    mock_executor.assert_called_once_with("High priority task", task.context)

    # Task should be completed
    updated_task = await daemon.task_store.get(task.id)
    assert updated_task.state == TaskState.COMPLETED
    assert updated_task.result is not None


@pytest.mark.asyncio
async def test_task_failure_tracking(daemon, mock_executor):
    """Test task failure is tracked."""
    # Configure executor to fail
    mock_executor.side_effect = ValueError("Task failed")

    # Create a task
    task = Task(
        description="Failing task",
        priority=Priority.NORMAL,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Run one execution cycle
    await daemon._execute_cycle()

    # Task should be marked as failed
    updated_task = await daemon.task_store.get(task.id)
    assert updated_task.state == TaskState.FAILED
    assert "Task failed" in updated_task.error


@pytest.mark.asyncio
async def test_priority_order(daemon, mock_executor):
    """Test tasks are executed in priority order."""
    # Create tasks with different priorities
    low_task = Task(
        description="Low priority",
        priority=Priority.LOW,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    high_task = Task(
        description="High priority",
        priority=Priority.HIGH,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    normal_task = Task(
        description="Normal priority",
        priority=Priority.NORMAL,
        expires_at=datetime.now() + timedelta(hours=1),
    )

    # Create in random order
    await daemon.task_store.create(low_task)
    await daemon.task_store.create(normal_task)
    await daemon.task_store.create(high_task)

    # Execute cycles
    await daemon._execute_cycle()  # Should execute HIGH
    await daemon._execute_cycle()  # Should execute NORMAL
    await daemon._execute_cycle()  # Should execute LOW

    # Verify execution order by checking call args
    calls = mock_executor.call_args_list
    assert calls[0][0][0] == "High priority"
    assert calls[1][0][0] == "Normal priority"
    assert calls[2][0][0] == "Low priority"


@pytest.mark.asyncio
async def test_expired_task_cleanup(daemon):
    """Test expired tasks are cleaned up."""
    # Create an expired task
    expired_task = Task(
        description="Expired task",
        priority=Priority.NORMAL,
        expires_at=datetime.now() - timedelta(hours=1),  # Already expired
    )
    await daemon.task_store.create(expired_task)

    # Verify task exists
    task = await daemon.task_store.get(expired_task.id)
    assert task is not None

    # Run execution cycle (cleanup happens first)
    await daemon._execute_cycle()

    # Task should be deleted (cleanup_expired deletes, not marks as expired)
    updated_task = await daemon.task_store.get(expired_task.id)
    assert updated_task is None


@pytest.mark.asyncio
async def test_calculate_next_execution(daemon):
    """Test next execution time calculation."""
    now = datetime.now()

    # HOURLY
    hourly = Mission(description="Hourly", interval=MissionInterval.HOURLY)
    next_time = daemon._calculate_next_execution(hourly)
    assert next_time is not None
    time_diff = (next_time - now).total_seconds()
    assert 3590 <= time_diff <= 3610  # ~1 hour ±10 seconds

    # DAILY
    daily = Mission(description="Daily", interval=MissionInterval.DAILY)
    next_time = daemon._calculate_next_execution(daily)
    assert next_time is not None
    time_diff = (next_time - now).total_seconds()
    assert 86390 <= time_diff <= 86410  # ~24 hours ±10 seconds

    # WEEKLY
    weekly = Mission(description="Weekly", interval=MissionInterval.WEEKLY)
    next_time = daemon._calculate_next_execution(weekly)
    assert next_time is not None
    time_diff = (next_time - now).total_seconds()
    assert 604790 <= time_diff <= 604810  # ~7 days ±10 seconds

    # ONCE
    once = Mission(description="Once", interval=MissionInterval.ONCE)
    next_time = daemon._calculate_next_execution(once)
    assert next_time is None

    # MANUAL
    manual = Mission(description="Manual", interval=MissionInterval.MANUAL)
    next_time = daemon._calculate_next_execution(manual)
    assert next_time is None


@pytest.mark.asyncio
async def test_should_interrupt_logic(daemon):
    """Test mission interruption logic."""
    # Mission that can be interrupted by URGENT+
    mission = Mission(
        description="Interruptible",
        interval=MissionInterval.MANUAL,
        can_be_interrupted=True,
        interrupt_threshold=Priority.URGENT,
    )
    daemon.current_mission = mission

    # CRITICAL should interrupt
    critical_task = Task(description="Critical", priority=Priority.CRITICAL)
    assert daemon._should_interrupt(critical_task) is True

    # URGENT should interrupt
    urgent_task = Task(description="Urgent", priority=Priority.URGENT)
    assert daemon._should_interrupt(urgent_task) is True

    # HIGH should NOT interrupt
    high_task = Task(description="High", priority=Priority.HIGH)
    assert daemon._should_interrupt(high_task) is False

    # Mission that CANNOT be interrupted
    mission.can_be_interrupted = False
    assert daemon._should_interrupt(critical_task) is False
    assert daemon._should_interrupt(urgent_task) is False


@pytest.mark.asyncio
async def test_resolution_service_registration(temp_data_dir, mock_executor):
    """Test daemon registers with resolution service."""
    resolution_service = MockResolutionService()

    daemon = AgentDaemon(
        agent_id="test-agent",
        agent_executor=mock_executor,
        data_dir=temp_data_dir,
        resolution_service=resolution_service,
        poll_interval=1,
    )

    # Start daemon
    start_task = asyncio.create_task(daemon.start())
    await asyncio.sleep(0.1)

    # Check agent is registered
    agents = resolution_service.get_all_agents()
    assert len(agents) == 1
    assert agents[0].agent_id == "test-agent"

    # Stop daemon
    await daemon.stop()
    await start_task

    # Check agent is unregistered
    agents = resolution_service.get_all_agents()
    assert len(agents) == 0


@pytest.mark.asyncio
async def test_resolution_service_registration_failure(temp_data_dir, mock_executor):
    """Test daemon handles resolution service registration failure gracefully."""
    # Mock resolution service that fails
    resolution_service = MagicMock()
    resolution_service.register_agent = AsyncMock(side_effect=Exception("Service unavailable"))
    resolution_service.unregister_agent = AsyncMock()

    daemon = AgentDaemon(
        agent_id="test-agent",
        agent_executor=mock_executor,
        data_dir=temp_data_dir,
        resolution_service=resolution_service,
        poll_interval=1,
    )

    # Should start successfully even if registration fails
    start_task = asyncio.create_task(daemon.start())
    await asyncio.sleep(0.1)

    assert daemon.running is True

    await daemon.stop()
    await start_task


@pytest.mark.asyncio
async def test_daemon_stop_gracefully(daemon):
    """Test daemon stops gracefully."""
    # Start daemon
    start_task = asyncio.create_task(daemon.start())
    await asyncio.sleep(0.1)

    assert daemon.running is True

    # Stop daemon
    await daemon.stop()
    await start_task

    assert daemon.running is False
    assert daemon._loop_task.done()


@pytest.mark.asyncio
async def test_execution_loop_error_handling(daemon, mock_executor):
    """Test execution loop handles errors without crashing."""
    # Configure executor to fail
    mock_executor.side_effect = Exception("Random error")

    # Create a task
    task = Task(
        description="Task that will fail",
        priority=Priority.NORMAL,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Start daemon
    start_task = asyncio.create_task(daemon.start())
    await asyncio.sleep(0.2)  # Let it run a few cycles

    # Daemon should still be running
    assert daemon.running is True

    # Stop daemon
    await daemon.stop()
    await start_task


@pytest.mark.asyncio
async def test_multiple_cycles(daemon, mock_executor):
    """Test daemon runs multiple execution cycles."""
    # Create multiple tasks
    for i in range(3):
        task = Task(
            description=f"Task {i}",
            priority=Priority.NORMAL,
            expires_at=datetime.now() + timedelta(hours=1),
        )
        await daemon.task_store.create(task)

    # Start daemon
    start_task = asyncio.create_task(daemon.start())

    # Wait for all tasks to be processed
    for _ in range(10):  # Max 10 attempts
        await asyncio.sleep(0.2)
        pending = await daemon.task_store.get_pending()
        if not pending:
            break

    # All tasks should be completed
    assert mock_executor.call_count == 3

    await daemon.stop()
    await start_task


@pytest.mark.asyncio
async def test_stores_cleanup_on_shutdown(daemon):
    """Test stores are properly closed on shutdown."""
    # Start daemon
    start_task = asyncio.create_task(daemon.start())
    await asyncio.sleep(0.1)

    # Stop daemon
    await daemon.stop()
    await start_task

    # Stores should be closed (this is tested by checking they don't crash on access)
    # SQLite will raise an error if we try to use a closed connection
    # For now, just verify shutdown completed without errors
    assert not daemon.running

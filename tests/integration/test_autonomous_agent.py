"""Integration test for autonomous agent execution.

Tests the full stack: HeartbeatDaemon + AgentExecutor + Agent
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from teotl.daemon.agent_daemon import AgentDaemon
from teotl.daemon.executor import create_simple_executor
from teotl.primitives.missions import Mission, MissionInterval
from teotl.primitives.tasks import Priority, Task


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory."""
    data_dir = tmp_path / "test_autonomous_agent"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    provider = Mock()
    provider.complete = AsyncMock(
        return_value=Mock(message=Mock(content="Task completed successfully", tool_calls=[]))
    )
    return provider


@pytest.mark.asyncio
@patch("teotl.daemon.executor.Agent")
async def test_daemon_executes_task_via_agent(mock_agent_class, temp_data_dir, mock_provider):
    """Test that daemon executes tasks through agent executor."""
    # Setup mock agent
    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=Mock(text="Email sent successfully"))
    mock_agent_class.return_value = mock_agent_instance

    # Create executor
    executor = create_simple_executor(
        provider=mock_provider,
        instructions="You are an email assistant",
        skills=["gmail"],
    )

    # Create daemon
    daemon = AgentDaemon(
        agent_id="email-agent",
        agent_executor=executor,
        data_dir=temp_data_dir,
        poll_interval=1,
    )

    # Create a task
    task = Task(
        description="Send email to alice@example.com",
        priority=Priority.HIGH,
        context={"to": "alice@example.com", "subject": "Hello"},
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Execute one cycle
    await daemon._execute_cycle()

    # Agent should have been called
    mock_agent_instance.run.assert_called_once()

    # Task should be completed
    updated_task = await daemon.task_store.get(task.id)
    assert updated_task.state.value == "completed"
    assert "Email sent successfully" in str(updated_task.result)


@pytest.mark.asyncio
@patch("teotl.daemon.executor.Agent")
async def test_daemon_executes_mission_via_agent(mock_agent_class, temp_data_dir, mock_provider):
    """Test that daemon executes missions through agent executor."""
    # Setup mock agent
    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=Mock(text="Checked email, 3 new messages"))
    mock_agent_class.return_value = mock_agent_instance

    # Create executor
    executor = create_simple_executor(
        provider=mock_provider,
        instructions="You are an email assistant",
    )

    # Create daemon
    daemon = AgentDaemon(
        agent_id="email-agent",
        agent_executor=executor,
        data_dir=temp_data_dir,
        poll_interval=1,
    )

    # Create a due mission
    mission = Mission(
        description="Check for new emails",
        interval=MissionInterval.HOURLY,
        next_execution_at=datetime.now() - timedelta(minutes=5),  # Due
    )
    await daemon.mission_store.create(mission)

    # Execute one cycle
    await daemon._execute_cycle()

    # Agent should have been called
    mock_agent_instance.run.assert_called_once()

    # Mission should be updated
    updated_mission = await daemon.mission_store.get(mission.id)
    assert updated_mission.execution_count == 1
    assert updated_mission.success_count == 1
    assert updated_mission.next_execution_at is not None


@pytest.mark.asyncio
@patch("teotl.daemon.executor.Agent")
async def test_task_context_passed_to_agent(mock_agent_class, temp_data_dir, mock_provider):
    """Test that task context is passed to agent."""
    # Setup mock agent
    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=Mock(text="Done"))
    mock_agent_class.return_value = mock_agent_instance

    # Create executor
    executor = create_simple_executor(provider=mock_provider)

    # Create daemon
    daemon = AgentDaemon(
        agent_id="test-agent",
        agent_executor=executor,
        data_dir=temp_data_dir,
        poll_interval=1,
    )

    # Create task with context
    task = Task(
        description="Process user data",
        priority=Priority.NORMAL,
        context={"user_id": "123", "action": "export"},
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Execute
    await daemon._execute_cycle()

    # Check agent was called with context-enhanced prompt
    call_args = mock_agent_instance.run.call_args
    prompt = call_args[0][0]

    assert "Process user data" in prompt
    assert "user_id: 123" in prompt
    assert "action: export" in prompt


@pytest.mark.asyncio
@patch("teotl.daemon.executor.Agent")
async def test_critical_task_interrupts_mission(mock_agent_class, temp_data_dir, mock_provider):
    """Test that CRITICAL tasks interrupt missions."""
    # Setup mock agent
    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=Mock(text="Emergency handled"))
    mock_agent_class.return_value = mock_agent_instance

    # Create executor
    executor = create_simple_executor(provider=mock_provider)

    # Create daemon
    daemon = AgentDaemon(
        agent_id="test-agent",
        agent_executor=executor,
        data_dir=temp_data_dir,
        poll_interval=1,
    )

    # Create a non-interruptible mission
    mission = Mission(
        description="Long running mission",
        interval=MissionInterval.MANUAL,
        can_be_interrupted=False,
        next_execution_at=datetime.now() - timedelta(minutes=1),
    )
    await daemon.mission_store.create(mission)

    # Simulate mission in progress
    daemon.current_mission = mission

    # Create CRITICAL task
    critical_task = Task(
        description="CRITICAL: Server down!",
        priority=Priority.CRITICAL,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(critical_task)

    # Execute cycle
    await daemon._execute_cycle()

    # CRITICAL task should execute (interrupting mission)
    call_args = mock_agent_instance.run.call_args
    prompt = call_args[0][0]
    assert "CRITICAL: Server down!" in prompt


@pytest.mark.asyncio
@patch("teotl.daemon.executor.Agent")
async def test_agent_error_marks_task_failed(mock_agent_class, temp_data_dir, mock_provider):
    """Test that agent errors properly mark task as failed."""
    # Setup mock agent that fails
    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(side_effect=ValueError("Agent crashed"))
    mock_agent_class.return_value = mock_agent_instance

    # Create executor
    executor = create_simple_executor(provider=mock_provider)

    # Create daemon
    daemon = AgentDaemon(
        agent_id="test-agent",
        agent_executor=executor,
        data_dir=temp_data_dir,
        poll_interval=1,
    )

    # Create task
    task = Task(
        description="Failing task",
        priority=Priority.NORMAL,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Execute
    await daemon._execute_cycle()

    # Task should be marked as failed
    updated_task = await daemon.task_store.get(task.id)
    assert updated_task.state.value == "failed"
    assert "Agent crashed" in updated_task.error


@pytest.mark.asyncio
@patch("teotl.daemon.executor.Agent")
async def test_multiple_tasks_processed_in_priority_order(
    mock_agent_class, temp_data_dir, mock_provider
):
    """Test that daemon processes multiple tasks in priority order."""
    # Setup mock agent
    executed_tasks = []

    async def track_execution(prompt, **kwargs):
        executed_tasks.append(prompt)
        return Mock(text="Done")

    mock_agent_instance = Mock()
    mock_agent_instance.run = track_execution
    mock_agent_class.return_value = mock_agent_instance

    # Create executor
    executor = create_simple_executor(provider=mock_provider)

    # Create daemon
    daemon = AgentDaemon(
        agent_id="test-agent",
        agent_executor=executor,
        data_dir=temp_data_dir,
        poll_interval=1,
    )

    # Create tasks with different priorities
    tasks = [
        Task(
            description="Low priority task",
            priority=Priority.LOW,
            expires_at=datetime.now() + timedelta(hours=1),
        ),
        Task(
            description="High priority task",
            priority=Priority.HIGH,
            expires_at=datetime.now() + timedelta(hours=1),
        ),
        Task(
            description="Normal priority task",
            priority=Priority.NORMAL,
            expires_at=datetime.now() + timedelta(hours=1),
        ),
    ]

    for task in tasks:
        await daemon.task_store.create(task)

    # Execute multiple cycles
    for _ in range(3):
        await daemon._execute_cycle()

    # Should execute in priority order: HIGH -> NORMAL -> LOW
    assert len(executed_tasks) == 3
    assert "High priority task" in executed_tasks[0]
    assert "Normal priority task" in executed_tasks[1]
    assert "Low priority task" in executed_tasks[2]


@pytest.mark.asyncio
@patch("teotl.daemon.executor.Agent")
async def test_daemon_full_lifecycle(mock_agent_class, temp_data_dir, mock_provider):
    """Test daemon full lifecycle: start, execute, stop."""
    # Setup mock agent
    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=Mock(text="Task done"))
    mock_agent_class.return_value = mock_agent_instance

    # Create executor
    executor = create_simple_executor(provider=mock_provider)

    # Create daemon
    daemon = AgentDaemon(
        agent_id="test-agent",
        agent_executor=executor,
        data_dir=temp_data_dir,
        poll_interval=0.1,  # Fast polling for test
    )

    # Create a task
    task = Task(
        description="Test task",
        priority=Priority.NORMAL,
        expires_at=datetime.now() + timedelta(hours=1),
    )
    await daemon.task_store.create(task)

    # Start daemon in background
    start_task = asyncio.create_task(daemon.start())

    # Wait for task to be processed
    task_completed = False
    for _ in range(50):  # Max 5 seconds
        await asyncio.sleep(0.1)
        updated_task = await daemon.task_store.get(task.id)
        if updated_task.state.value == "completed":
            task_completed = True
            break

    # Verify task was completed (before stopping daemon)
    assert task_completed

    # Stop daemon
    await daemon.stop()
    await start_task

    # Verify daemon stopped cleanly
    assert not daemon.running
    assert not daemon.pid_file.exists()

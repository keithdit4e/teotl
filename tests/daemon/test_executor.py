"""Tests for agent executor bridge."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from teotl.core.agent import Agent
from teotl.daemon.executor import (
    AgentExecutor,
    AgentExecutorFactory,
    create_simple_executor,
)


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = MagicMock(spec=Agent)
    agent.run = AsyncMock(return_value=Mock(text="Task completed successfully"))
    return agent


@pytest.fixture
def agent_factory(mock_agent):
    """Create an agent factory that returns mock agent."""

    def factory():
        return mock_agent

    return factory


@pytest.mark.asyncio
async def test_executor_with_agent_instance(mock_agent):
    """Test executor with pre-configured agent instance."""
    executor = AgentExecutor(agent=mock_agent)

    result = await executor.execute("Test task", {"key": "value"})

    assert result == "Task completed successfully"
    mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_executor_with_factory(agent_factory, mock_agent):
    """Test executor with agent factory."""
    executor = AgentExecutor(agent_factory=agent_factory)

    result = await executor.execute("Test task")

    assert result == "Task completed successfully"
    mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_executor_requires_agent_or_factory():
    """Test that executor requires either agent or factory."""
    with pytest.raises(ValueError, match="Must provide either agent_factory or agent"):
        AgentExecutor()


@pytest.mark.asyncio
async def test_execute_with_context(mock_agent):
    """Test execution with context injection."""
    executor = AgentExecutor(agent=mock_agent)

    context = {"filename": "test.txt", "content": "Hello"}
    result = await executor.execute("Write file", context)

    # Should have called agent.run with context-enhanced prompt
    call_args = mock_agent.run.call_args
    prompt = call_args[0][0]

    assert "Write file" in prompt
    assert "filename: test.txt" in prompt
    assert "content: Hello" in prompt
    assert result == "Task completed successfully"


@pytest.mark.asyncio
async def test_execute_without_context(mock_agent):
    """Test execution without context."""
    executor = AgentExecutor(agent=mock_agent)

    result = await executor.execute("Simple task")

    # Should call agent.run with description only
    call_args = mock_agent.run.call_args
    prompt = call_args[0][0]

    assert prompt == "Simple task"
    assert result == "Task completed successfully"


@pytest.mark.asyncio
async def test_execute_timeout(mock_agent):
    """Test execution timeout."""

    # Make agent.run hang
    async def hang(*args, **kwargs):
        await asyncio.sleep(10)

    mock_agent.run = hang

    executor = AgentExecutor(agent=mock_agent, timeout=0.1)

    with pytest.raises(asyncio.TimeoutError):
        await executor.execute("Long task")


@pytest.mark.asyncio
async def test_execute_override_timeout(mock_agent):
    """Test overriding timeout per execution."""

    # Make agent.run take some time
    async def slow_run(*args, **kwargs):
        await asyncio.sleep(0.2)
        return Mock(text="Done")

    mock_agent.run = slow_run

    executor = AgentExecutor(agent=mock_agent, timeout=0.1)

    # Should timeout with default
    with pytest.raises(asyncio.TimeoutError):
        await executor.execute("Task", timeout=0.05)

    # Should succeed with override
    result = await executor.execute("Task", timeout=1.0)
    assert result == "Done"


@pytest.mark.asyncio
async def test_execute_agent_error(mock_agent):
    """Test handling agent execution errors."""
    mock_agent.run = AsyncMock(side_effect=ValueError("Agent failed"))

    executor = AgentExecutor(agent=mock_agent)

    with pytest.raises(ValueError, match="Agent failed"):
        await executor.execute("Failing task")


@pytest.mark.asyncio
async def test_execute_returns_text_attribute(mock_agent):
    """Test that executor extracts .text from response."""
    response = Mock(text="Response text")
    mock_agent.run = AsyncMock(return_value=response)

    executor = AgentExecutor(agent=mock_agent)
    result = await executor.execute("Task")

    assert result == "Response text"


@pytest.mark.asyncio
async def test_execute_returns_str_if_no_text_attr(mock_agent):
    """Test that executor converts to string if no .text attribute."""
    mock_agent.run = AsyncMock(return_value="Plain string response")

    executor = AgentExecutor(agent=mock_agent)
    result = await executor.execute("Task")

    assert result == "Plain string response"


@pytest.mark.asyncio
async def test_auto_approve_setting(mock_agent):
    """Test that auto_approve is passed to headless UI."""
    executor = AgentExecutor(agent=mock_agent, auto_approve=False)

    await executor.execute("Task")

    # Check that UI was created with auto_approve=False
    call_args = mock_agent.run.call_args
    ui = call_args[1]["ui"]
    assert ui.auto_approve is False


@pytest.mark.asyncio
async def test_factory_creates_fresh_instances():
    """Test that factory creates new agent instances."""
    call_count = 0

    def factory():
        nonlocal call_count
        call_count += 1
        agent = MagicMock(spec=Agent)
        agent.run = AsyncMock(return_value=Mock(text=f"Response {call_count}"))
        return agent

    executor = AgentExecutor(agent_factory=factory)

    # Execute multiple times
    result1 = await executor.execute("Task 1")
    result2 = await executor.execute("Task 2")

    # Factory should be called each time
    assert call_count == 2
    assert result1 == "Response 1"
    assert result2 == "Response 2"


@pytest.mark.asyncio
async def test_executor_factory_create():
    """Test AgentExecutorFactory.create()."""
    mock_provider = Mock()

    factory = AgentExecutorFactory(
        provider=mock_provider,
        policy="strict",
        timeout=600,
    )

    executor = factory.create(
        instructions="Test instructions",
        skills=["filesystem"],
        timeout=120,
    )

    assert executor.timeout == 120
    assert executor.auto_approve is True

    # Should create agent with correct config
    agent = executor.agent
    assert agent is not None
    # Agent exists and was created with the factory


@pytest.mark.asyncio
async def test_executor_factory_defaults():
    """Test AgentExecutorFactory uses defaults."""
    mock_provider = Mock()

    factory = AgentExecutorFactory(
        provider=mock_provider,
        policy="minimal",
        timeout=300,
        auto_approve=False,
    )

    executor = factory.create(instructions="Test")

    # Should use factory defaults
    assert executor.timeout == 300
    assert executor.auto_approve is False

    agent = executor.agent
    assert agent is not None


@pytest.mark.asyncio
async def test_executor_factory_override_defaults():
    """Test overriding factory defaults."""
    mock_provider = Mock()

    factory = AgentExecutorFactory(
        provider=mock_provider,
        policy="standard",
    )

    executor = factory.create(
        instructions="Test",
        policy="strict",  # Override
        auto_approve=True,  # Override
    )

    agent = executor.agent
    assert agent is not None
    assert executor.auto_approve is True


@pytest.mark.asyncio
@patch("teotl.daemon.executor.Agent")
async def test_create_simple_executor(mock_agent_class):
    """Test create_simple_executor convenience function."""
    mock_provider = Mock()
    mock_agent_instance = MagicMock()
    mock_agent_instance.run = AsyncMock(return_value=Mock(text="Done"))
    mock_agent_class.return_value = mock_agent_instance

    executor_fn = create_simple_executor(
        provider=mock_provider,
        instructions="Test agent",
        skills=["git"],
    )

    # Should return async function
    assert asyncio.iscoroutinefunction(executor_fn)

    # Execute task
    result = await executor_fn("Test task", {"key": "value"})

    assert result == "Done"
    mock_agent_instance.run.assert_called_once()


@pytest.mark.asyncio
@patch("teotl.daemon.executor.Agent")
async def test_create_simple_executor_matches_heartbeat_signature(mock_agent_class):
    """Test that create_simple_executor matches HeartbeatDaemon signature."""
    mock_provider = Mock()
    mock_agent_instance = MagicMock()
    mock_agent_instance.run = AsyncMock(return_value=Mock(text="Success"))
    mock_agent_class.return_value = mock_agent_instance

    executor_fn = create_simple_executor(
        provider=mock_provider,
        instructions="Test",
    )

    # HeartbeatDaemon calls executor with (description, context)
    result = await executor_fn("Task description", {"var": "value"})

    assert result == "Success"


@pytest.mark.asyncio
async def test_build_prompt_formats_context():
    """Test that _build_prompt correctly formats context."""
    executor = AgentExecutor(agent=MagicMock())

    context = {"name": "Alice", "age": 30, "role": "developer"}
    prompt = executor._build_prompt("Process user", context)

    assert "Process user" in prompt
    assert "name: Alice" in prompt
    assert "age: 30" in prompt
    assert "role: developer" in prompt
    assert "Context:" in prompt


@pytest.mark.asyncio
async def test_build_prompt_empty_context():
    """Test _build_prompt with empty context."""
    executor = AgentExecutor(agent=MagicMock())

    prompt = executor._build_prompt("Simple task", {})

    # Should still include context section (just empty)
    assert "Simple task" in prompt
    assert "Context:" in prompt


@pytest.mark.asyncio
async def test_executor_logging(mock_agent, caplog):
    """Test that executor logs execution events."""
    import logging

    caplog.set_level(logging.INFO)

    executor = AgentExecutor(agent=mock_agent)
    await executor.execute("Test task")

    # Check logs
    assert "Executing: Test task" in caplog.text
    assert "Execution completed successfully" in caplog.text


@pytest.mark.asyncio
async def test_executor_error_logging(mock_agent, caplog):
    """Test that executor logs errors."""
    import logging

    caplog.set_level(logging.ERROR)

    mock_agent.run = AsyncMock(side_effect=RuntimeError("Crash"))

    executor = AgentExecutor(agent=mock_agent)

    with pytest.raises(RuntimeError):
        await executor.execute("Failing task")

    assert "Execution failed" in caplog.text
    assert "Crash" in caplog.text


@pytest.mark.asyncio
async def test_executor_timeout_logging(mock_agent, caplog):
    """Test that executor logs timeouts."""
    import logging

    caplog.set_level(logging.ERROR)

    async def hang(*args, **kwargs):
        await asyncio.sleep(10)

    mock_agent.run = hang

    executor = AgentExecutor(agent=mock_agent, timeout=0.1)

    with pytest.raises(asyncio.TimeoutError):
        await executor.execute("Slow task")

    assert "timed out" in caplog.text

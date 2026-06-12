"""Tests for mock resolution service."""

import pytest

from teotl.primitives.resolution import (
    AgentNotFoundError,
    MockResolutionService,
)


@pytest.fixture
async def service():
    """Create a fresh mock resolution service."""
    svc = MockResolutionService()
    yield svc
    svc.clear()


@pytest.mark.asyncio
async def test_register_agent(service):
    """Test registering an agent."""
    registered = await service.register_agent(
        agent_id="email-agent-1",
        capabilities=["email.send", "email.search"],
        endpoint="http://localhost:8001/a2a",
        protocol="agent-protocol",
        metadata={"version": "1.0.0"},
    )

    assert registered is True

    # Verify it's in the registry
    agents = service.get_all_agents()
    assert len(agents) == 1
    assert agents[0].agent_id == "email-agent-1"
    assert agents[0].capabilities == ["email.send", "email.search"]


@pytest.mark.asyncio
async def test_unregister_agent(service):
    """Test unregistering an agent."""
    await service.register_agent(
        agent_id="test-agent",
        capabilities=["test"],
        endpoint="http://localhost:8000",
    )

    # Unregister
    unregistered = await service.unregister_agent("test-agent")
    assert unregistered is True

    # Verify it's gone
    agents = service.get_all_agents()
    assert len(agents) == 0

    # Unregistering again returns False
    unregistered_again = await service.unregister_agent("test-agent")
    assert unregistered_again is False


@pytest.mark.asyncio
async def test_resolve_capability(service):
    """Test resolving a capability."""
    await service.register_agent(
        agent_id="email-agent",
        capabilities=["email.send"],
        endpoint="http://localhost:8001/a2a",
    )

    # Resolve the capability
    endpoint = await service.resolve_capability("email.send")

    assert endpoint.agent_id == "email-agent"
    assert endpoint.endpoint == "http://localhost:8001/a2a"
    assert "email.send" in endpoint.capabilities


@pytest.mark.asyncio
async def test_resolve_nonexistent_capability(service):
    """Test resolving a capability that doesn't exist."""
    with pytest.raises(AgentNotFoundError, match="No agent found for capability"):
        await service.resolve_capability("nonexistent.capability")


@pytest.mark.asyncio
async def test_round_robin_load_balancing(service):
    """Test round-robin load balancing."""
    # Register 3 email agents
    await service.register_agent(
        agent_id="email-agent-1",
        capabilities=["email.send"],
        endpoint="http://localhost:8001/a2a",
    )
    await service.register_agent(
        agent_id="email-agent-2",
        capabilities=["email.send"],
        endpoint="http://localhost:8002/a2a",
    )
    await service.register_agent(
        agent_id="email-agent-3",
        capabilities=["email.send"],
        endpoint="http://localhost:8003/a2a",
    )

    # Resolve 6 times, should cycle through all 3 agents twice
    results = []
    for _ in range(6):
        endpoint = await service.resolve_capability("email.send", load_balance=True)
        results.append(endpoint.agent_id)

    # Should cycle: 1, 2, 3, 1, 2, 3
    assert results[0] == "email-agent-1"
    assert results[1] == "email-agent-2"
    assert results[2] == "email-agent-3"
    assert results[3] == "email-agent-1"
    assert results[4] == "email-agent-2"
    assert results[5] == "email-agent-3"


@pytest.mark.asyncio
async def test_filter_by_protocol(service):
    """Test filtering agents by protocol."""
    # Register agents with different protocols
    await service.register_agent(
        agent_id="agent-protocol-1",
        capabilities=["email.send"],
        endpoint="http://localhost:8001/a2a",
        protocol="agent-protocol",
    )
    await service.register_agent(
        agent_id="mcp-agent-1",
        capabilities=["email.send"],
        endpoint="http://localhost:8002/mcp",
        protocol="mcp",
    )

    # Request agent-protocol specifically
    endpoint = await service.resolve_capability(
        "email.send", requirements={"protocol": "agent-protocol"}
    )
    assert endpoint.agent_id == "agent-protocol-1"
    assert endpoint.protocol == "agent-protocol"

    # Request MCP specifically
    endpoint = await service.resolve_capability("email.send", requirements={"protocol": "mcp"})
    assert endpoint.agent_id == "mcp-agent-1"
    assert endpoint.protocol == "mcp"


@pytest.mark.asyncio
async def test_no_agents_matching_requirements(service):
    """Test when no agents match requirements."""
    await service.register_agent(
        agent_id="mcp-agent",
        capabilities=["email.send"],
        endpoint="http://localhost:8001",
        protocol="mcp",
    )

    # Request agent-protocol but only MCP exists
    with pytest.raises(AgentNotFoundError, match="No agents for capability .* with protocol"):
        await service.resolve_capability("email.send", requirements={"protocol": "agent-protocol"})


@pytest.mark.asyncio
async def test_multiple_capabilities_per_agent(service):
    """Test agent with multiple capabilities."""
    await service.register_agent(
        agent_id="multi-agent",
        capabilities=["email.send", "email.search", "calendar.create"],
        endpoint="http://localhost:8001",
    )

    # Should be resolvable by any of its capabilities
    email_endpoint = await service.resolve_capability("email.send")
    assert email_endpoint.agent_id == "multi-agent"

    calendar_endpoint = await service.resolve_capability("calendar.create")
    assert calendar_endpoint.agent_id == "multi-agent"


@pytest.mark.asyncio
async def test_get_agents_by_capability(service):
    """Test getting all agents with a capability."""
    await service.register_agent(
        agent_id="email-1",
        capabilities=["email.send"],
        endpoint="http://localhost:8001",
    )
    await service.register_agent(
        agent_id="email-2",
        capabilities=["email.send", "email.search"],
        endpoint="http://localhost:8002",
    )
    await service.register_agent(
        agent_id="calendar-1",
        capabilities=["calendar.create"],
        endpoint="http://localhost:8003",
    )

    # Get all email.send agents
    email_agents = service.get_agents_by_capability("email.send")
    assert len(email_agents) == 2
    agent_ids = [a.agent_id for a in email_agents]
    assert "email-1" in agent_ids
    assert "email-2" in agent_ids

    # Get calendar agents
    calendar_agents = service.get_agents_by_capability("calendar.create")
    assert len(calendar_agents) == 1
    assert calendar_agents[0].agent_id == "calendar-1"


@pytest.mark.asyncio
async def test_health_check(service):
    """Test health check (always healthy for mock)."""
    healthy = await service.health_check()
    assert healthy is True


@pytest.mark.asyncio
async def test_clear_registry(service):
    """Test clearing all registrations."""
    await service.register_agent(
        agent_id="agent-1", capabilities=["test"], endpoint="http://localhost:8001"
    )
    await service.register_agent(
        agent_id="agent-2", capabilities=["test"], endpoint="http://localhost:8002"
    )

    assert len(service.get_all_agents()) == 2

    service.clear()

    assert len(service.get_all_agents()) == 0

    # Should raise error after clear
    with pytest.raises(AgentNotFoundError):
        await service.resolve_capability("test")


@pytest.mark.asyncio
async def test_unregister_removes_from_capability_index(service):
    """Test that unregistering removes agent from capability lookups."""
    await service.register_agent(
        agent_id="email-agent",
        capabilities=["email.send"],
        endpoint="http://localhost:8001",
    )

    # Can resolve
    endpoint = await service.resolve_capability("email.send")
    assert endpoint.agent_id == "email-agent"

    # Unregister
    await service.unregister_agent("email-agent")

    # Can no longer resolve
    with pytest.raises(AgentNotFoundError):
        await service.resolve_capability("email.send")


@pytest.mark.asyncio
async def test_agent_metadata(service):
    """Test storing and retrieving agent metadata."""
    await service.register_agent(
        agent_id="email-agent",
        capabilities=["email.send"],
        endpoint="http://localhost:8001",
        metadata={
            "version": "2.0.0",
            "max_concurrent": 10,
            "health": "healthy",
        },
    )

    endpoint = await service.resolve_capability("email.send")

    assert endpoint.metadata["version"] == "2.0.0"
    assert endpoint.metadata["max_concurrent"] == 10
    assert endpoint.metadata["health"] == "healthy"

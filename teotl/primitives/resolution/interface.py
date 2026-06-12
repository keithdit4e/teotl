"""Resolution service interface.

This is the contract between the agent framework and external resolution services.
Agents use this interface to register themselves and discover other agents.

The actual resolution service will be implemented as a separate project.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class AgentEndpoint(BaseModel):
    """Agent endpoint information returned by resolution service."""

    agent_id: str  # Unique agent instance ID
    endpoint: str  # HTTP/WebSocket endpoint (e.g., "http://localhost:8001/a2a")
    protocol: str = "agent-protocol"  # Communication protocol
    capabilities: list[str] = []  # What this agent can do
    metadata: dict[str, Any] = {}  # Additional info (load, version, etc.)


class AgentRegistration(BaseModel):
    """Agent registration information."""

    agent_id: str
    capabilities: list[str]  # What this agent provides
    endpoint: str
    protocol: str = "agent-protocol"
    metadata: dict[str, Any] = {}  # Health status, capacity, etc.


class ResolutionService(ABC):
    """Abstract interface for agent resolution services.

    Resolution services handle:
    - Agent registration and discovery
    - Capability-based routing
    - Load balancing across agent instances
    - Health monitoring

    Agents are NOT required to use a resolution service. They can:
    - Use hardcoded endpoints (simple deployments)
    - Read from config files
    - Use environment variables
    - Directly call other agents

    Resolution services enable dynamic multi-agent systems where:
    - Agents can scale to zero and auto-scale
    - New agents can be added without reconfiguration
    - Failed agents are automatically removed
    """

    @abstractmethod
    async def register_agent(
        self,
        agent_id: str,
        capabilities: list[str],
        endpoint: str,
        protocol: str = "agent-protocol",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Register an agent with the resolution service.

        Args:
            agent_id: Unique agent instance ID (e.g., "email-agent-1")
            capabilities: List of capabilities this agent provides
                         (e.g., ["email.send", "email.search"])
            endpoint: Agent's A2A endpoint (e.g., "http://localhost:8001/a2a")
            protocol: Communication protocol (default: "agent-protocol")
            metadata: Additional metadata (health, capacity, version, etc.)

        Returns:
            True if registration successful

        Raises:
            ConnectionError: If cannot reach resolution service
        """
        pass

    @abstractmethod
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent (e.g., on shutdown).

        Args:
            agent_id: Agent instance ID to unregister

        Returns:
            True if unregistered successfully
        """
        pass

    @abstractmethod
    async def resolve_capability(
        self,
        capability: str,
        requirements: dict[str, Any] | None = None,
        load_balance: bool = True,
    ) -> AgentEndpoint:
        """Find an agent that provides a capability.

        Args:
            capability: Capability needed (e.g., "email.send")
            requirements: Additional requirements (e.g., {"protocol": "agent-protocol"})
            load_balance: If True, return least-loaded instance

        Returns:
            Agent endpoint information

        Raises:
            AgentNotFoundError: If no agent provides this capability
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if resolution service is reachable.

        Returns:
            True if resolution service is healthy
        """
        pass


class AgentNotFoundError(Exception):
    """Raised when no agent found for requested capability."""

    pass

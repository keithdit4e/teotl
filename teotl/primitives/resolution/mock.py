"""Mock resolution service for testing.

This is a simple in-memory implementation for testing and development.
It does NOT provide production features like:
- Persistence
- Distributed consensus
- Health monitoring
- Load metrics

Use a real resolution service in production.
"""

from __future__ import annotations

import logging
from typing import Any

from teotl.primitives.resolution.interface import (
    AgentEndpoint,
    AgentNotFoundError,
    AgentRegistration,
    ResolutionService,
)

logger = logging.getLogger(__name__)


class MockResolutionService(ResolutionService):
    """In-memory mock resolution service for testing.

    Features:
    - In-memory agent registry
    - Capability-based lookup
    - Simple round-robin load balancing
    - No persistence (resets on restart)

    NOT suitable for production.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._registry: dict[str, AgentRegistration] = {}
        self._capability_index: dict[str, list[str]] = {}  # capability -> [agent_ids]
        self._round_robin_counters: dict[str, int] = {}  # capability -> counter

    async def register_agent(
        self,
        agent_id: str,
        capabilities: list[str],
        endpoint: str,
        protocol: str = "agent-protocol",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Register agent in memory."""
        registration = AgentRegistration(
            agent_id=agent_id,
            capabilities=capabilities,
            endpoint=endpoint,
            protocol=protocol,
            metadata=metadata or {},
        )

        self._registry[agent_id] = registration

        # Index by capabilities
        for capability in capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            if agent_id not in self._capability_index[capability]:
                self._capability_index[capability].append(agent_id)

        logger.info(f"Registered agent {agent_id} with capabilities: {', '.join(capabilities)}")
        return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister agent from memory."""
        if agent_id not in self._registry:
            return False

        registration = self._registry[agent_id]

        # Remove from capability index
        for capability in registration.capabilities:
            if capability in self._capability_index:
                self._capability_index[capability].remove(agent_id)
                if not self._capability_index[capability]:
                    del self._capability_index[capability]

        del self._registry[agent_id]
        logger.info(f"Unregistered agent {agent_id}")
        return True

    async def resolve_capability(
        self,
        capability: str,
        requirements: dict[str, Any] | None = None,
        load_balance: bool = True,
    ) -> AgentEndpoint:
        """Find agent with capability using simple round-robin."""
        # Find agents with this capability
        if capability not in self._capability_index:
            raise AgentNotFoundError(f"No agent found for capability: {capability}")

        agent_ids = self._capability_index[capability]
        if not agent_ids:
            raise AgentNotFoundError(f"No active agents for capability: {capability}")

        # Filter by requirements if provided
        if requirements:
            protocol = requirements.get("protocol")
            if protocol:
                agent_ids = [aid for aid in agent_ids if self._registry[aid].protocol == protocol]
                if not agent_ids:
                    raise AgentNotFoundError(
                        f"No agents for capability {capability} with protocol {protocol}"
                    )

        # Simple round-robin load balancing
        if load_balance and len(agent_ids) > 1:
            counter = self._round_robin_counters.get(capability, 0)
            selected_id = agent_ids[counter % len(agent_ids)]
            self._round_robin_counters[capability] = counter + 1
        else:
            selected_id = agent_ids[0]

        registration = self._registry[selected_id]

        return AgentEndpoint(
            agent_id=registration.agent_id,
            endpoint=registration.endpoint,
            protocol=registration.protocol,
            capabilities=registration.capabilities,
            metadata=registration.metadata,
        )

    async def health_check(self) -> bool:
        """Always healthy (in-memory)."""
        return True

    def get_all_agents(self) -> list[AgentRegistration]:
        """Get all registered agents (for testing/debugging)."""
        return list(self._registry.values())

    def get_agents_by_capability(self, capability: str) -> list[AgentRegistration]:
        """Get all agents with a specific capability (for testing)."""
        if capability not in self._capability_index:
            return []
        return [self._registry[agent_id] for agent_id in self._capability_index[capability]]

    def clear(self) -> None:
        """Clear all registrations (for testing)."""
        self._registry.clear()
        self._capability_index.clear()
        self._round_robin_counters.clear()
        logger.debug("Cleared all agent registrations")

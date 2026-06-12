"""File-based local agent discovery.

Simple agent registry using a YAML file (~/.forge/agents-registry.yaml).
Agents automatically register when they start and unregister when they stop.

This is the simple alternative to enterprise orchestration (ResolutionService).
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class AgentInfo(BaseModel):
    """Information about a registered agent."""

    agent_id: str
    endpoint: str  # e.g., "http://localhost:8001/a2a"
    capabilities: list[str] = []
    pid: int | None = None
    workspace: str | None = None
    registered_at: datetime = datetime.now()
    last_heartbeat: datetime = datetime.now()
    metadata: dict[str, Any] = {}


class LocalDiscovery:
    """File-based agent discovery for local multi-agent deployments.

    Agents register themselves in ~/.forge/agents-registry.yaml when they start.
    Other agents can discover them by capability or agent_id.

    Example:
        # Register agent
        discovery = LocalDiscovery()
        await discovery.register(
            agent_id="email-agent",
            endpoint="http://localhost:8001/a2a",
            capabilities=["email.send", "email.search"],
        )

        # Find agent
        agent = await discovery.find_by_capability("email.send")
        print(agent.endpoint)  # http://localhost:8001/a2a

        # Unregister on shutdown
        await discovery.unregister("email-agent")
    """

    def __init__(self, registry_path: Path | None = None):
        """Initialize local discovery.

        Args:
            registry_path: Path to registry file (default: ~/.forge/agents-registry.yaml)
        """
        if registry_path is None:
            registry_path = Path.home() / ".forge" / "agents-registry.yaml"

        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize empty registry if it doesn't exist
        if not self.registry_path.exists():
            self._save_registry({})

    def _load_registry(self) -> dict[str, dict[str, Any]]:
        """Load registry from file."""
        if not self.registry_path.exists():
            return {}

        with open(self.registry_path) as f:
            data = yaml.safe_load(f) or {}

        return data.get("agents", {})

    def _save_registry(self, agents: dict[str, dict[str, Any]]) -> None:
        """Save registry to file."""
        with open(self.registry_path, "w") as f:
            yaml.dump({"agents": agents}, f, default_flow_style=False)

    async def register(
        self,
        agent_id: str,
        endpoint: str,
        capabilities: list[str] | None = None,
        workspace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Register an agent in the local registry.

        Args:
            agent_id: Unique agent identifier
            endpoint: Agent's A2A endpoint (e.g., "http://localhost:8001/a2a")
            capabilities: List of capabilities (e.g., ["email.send", "slack.post"])
            workspace: Agent's workspace directory
            metadata: Additional metadata

        Returns:
            True if registered successfully
        """
        registry = self._load_registry()

        agent_info = {
            "agent_id": agent_id,
            "endpoint": endpoint,
            "capabilities": capabilities or [],
            "pid": os.getpid(),
            "workspace": workspace,
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        registry[agent_id] = agent_info
        self._save_registry(registry)

        return True

    async def unregister(self, agent_id: str) -> bool:
        """Unregister an agent from the local registry.

        Args:
            agent_id: Agent identifier to unregister

        Returns:
            True if unregistered successfully
        """
        registry = self._load_registry()

        if agent_id in registry:
            del registry[agent_id]
            self._save_registry(registry)
            return True

        return False

    async def update_heartbeat(self, agent_id: str) -> bool:
        """Update agent's last heartbeat timestamp.

        Args:
            agent_id: Agent identifier

        Returns:
            True if updated successfully
        """
        registry = self._load_registry()

        if agent_id in registry:
            registry[agent_id]["last_heartbeat"] = datetime.now().isoformat()
            self._save_registry(registry)
            return True

        return False

    async def find_by_id(self, agent_id: str) -> AgentInfo | None:
        """Find agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent info if found, None otherwise
        """
        registry = self._load_registry()

        if agent_id in registry:
            return AgentInfo(**registry[agent_id])

        return None

    async def find_by_capability(self, capability: str) -> AgentInfo | None:
        """Find first agent that provides a capability.

        Args:
            capability: Capability to search for (e.g., "email.send")

        Returns:
            Agent info if found, None otherwise
        """
        registry = self._load_registry()

        for _agent_id, agent_data in registry.items():
            if capability in agent_data.get("capabilities", []):
                return AgentInfo(**agent_data)

        return None

    async def find_all_by_capability(self, capability: str) -> list[AgentInfo]:
        """Find all agents that provide a capability.

        Args:
            capability: Capability to search for

        Returns:
            List of agent info objects
        """
        registry = self._load_registry()
        agents = []

        for _agent_id, agent_data in registry.items():
            if capability in agent_data.get("capabilities", []):
                agents.append(AgentInfo(**agent_data))

        return agents

    async def list_all(self) -> list[AgentInfo]:
        """List all registered agents.

        Returns:
            List of all registered agents
        """
        registry = self._load_registry()
        return [AgentInfo(**data) for data in registry.values()]

    async def health_check(self) -> bool:
        """Check if discovery service is available.

        For local discovery, this just checks if the registry file is accessible.

        Returns:
            True if registry is accessible
        """
        return self.registry_path.exists() and os.access(self.registry_path, os.W_OK)

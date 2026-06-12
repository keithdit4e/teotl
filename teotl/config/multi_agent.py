"""Multi-agent configuration parser.

Supports both single-agent and multi-agent config formats.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    agent_id: str
    instructions: str
    workspace: str | None = None
    skills: list[str] = []
    auto_approve: bool = True
    port: int | None = None  # A2A server port


class ProviderConfig(BaseModel):
    """LLM provider configuration."""

    type: str  # "anthropic", "openai", "ollama"
    model: str
    api_key_env: str | None = None


class DaemonConfig(BaseModel):
    """Daemon configuration."""

    poll_interval: int = 30  # seconds
    data_dir: str | None = None


class RateLimitsConfig(BaseModel):
    """Rate limits configuration."""

    max_requests_per_minute: int = 10
    max_cost_per_minute: float = 0.50


class TaskConfig(BaseModel):
    """Task configuration."""

    description: str
    priority: str = "NORMAL"
    expires_minutes: int | None = None
    expires_days: int | None = None
    context: dict[str, Any] = {}


class MissionConfig(BaseModel):
    """Mission configuration."""

    description: str
    interval: str  # "HOURLY", "DAILY", "WEEKLY"
    can_be_interrupted: bool = True
    interrupt_threshold: str = "URGENT"


class MultiAgentConfig(BaseModel):
    """Multi-agent configuration.

    Supports both formats:
    1. Single agent: config has "agent" key
    2. Multiple agents: config has "agents" key (dict of agent configs)
    """

    agents: dict[str, AgentConfig]
    provider: ProviderConfig
    daemon: DaemonConfig | None = None
    rate_limits: RateLimitsConfig | None = None
    tasks: list[TaskConfig] = []
    missions: list[MissionConfig] = []

    @property
    def is_multi_agent(self) -> bool:
        """Check if this is a multi-agent configuration."""
        return len(self.agents) > 1

    @property
    def agent_ids(self) -> list[str]:
        """Get list of all agent IDs."""
        return list(self.agents.keys())

    def get_agent(self, agent_id: str) -> AgentConfig | None:
        """Get configuration for specific agent."""
        return self.agents.get(agent_id)


def load_multi_agent_config(config_path: str | Path) -> MultiAgentConfig:
    """Load multi-agent configuration from YAML file.

    Supports both single-agent and multi-agent formats:

    Single agent format:
        agent:
          agent_id: my-agent
          instructions: "..."
        provider: {...}

    Multi-agent format:
        agents:
          personal:
            agent_id: personal
            instructions: "..."
          work:
            agent_id: work
            instructions: "..."
        provider: {...}

    Args:
        config_path: Path to config YAML file

    Returns:
        MultiAgentConfig with normalized agents dict

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If config is invalid
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError("Empty config file")

    # Normalize config format
    if "agent" in data:
        # Single agent format -> convert to multi-agent format
        agent_config = data.pop("agent")
        agent_id = agent_config.get("agent_id", "main")

        data["agents"] = {
            agent_id: agent_config,
        }

    elif "agents" not in data:
        raise ValueError("Config must have 'agent' or 'agents' key")

    # Parse and validate
    try:
        return MultiAgentConfig(**data)
    except Exception as e:
        raise ValueError(f"Invalid config format: {e}")

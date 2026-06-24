"""Configuration loading and parsing for Teotl.

This module provides YAML-based configuration for agents with full feature support:
- Memory system configuration
- Harness components (cost tracking, heartbeat, checkpoints, state, audit)
- Security policies
- Planner-worker architecture
- Model parameters

Example usage:

    from teotl.config import create_agent_from_yaml

    # Simple: create agent from YAML
    agent = create_agent_from_yaml("config.yaml")
    response = await agent.run("Hello!")

    # Advanced: load config and create manually
    from teotl.config import load_multi_agent_config, create_provider, create_agent_from_config

    config = load_multi_agent_config("config.yaml")
    provider = create_provider(config.provider)
    agent = create_agent_from_config(config.get_agent("my-agent"), provider)
"""

from teotl.config.factory import (
    create_agent_from_config,
    create_agent_from_yaml,
    create_agents_from_config,
    create_provider,
)
from teotl.config.multi_agent import (
    AgentConfig,
    AuditConfig,
    CheckpointConfig,
    CostTrackingConfig,
    DaemonConfig,
    HarnessConfig,
    HeartbeatConfig,
    JanitorConfig,
    MemoryConfig,
    MissionConfig,
    ModelParametersConfig,
    MultiAgentConfig,
    PlannerConfig,
    PlannerWorkerConfig,
    ProviderConfig,
    RateLimitsConfig,
    SecurityConfig,
    StateConfig,
    TaskConfig,
    WorkerConfig,
    load_multi_agent_config,
)

__all__ = [
    # Loading functions
    "load_multi_agent_config",
    # Factory functions
    "create_provider",
    "create_agent_from_config",
    "create_agents_from_config",
    "create_agent_from_yaml",
    # Config classes
    "MultiAgentConfig",
    "AgentConfig",
    "ProviderConfig",
    "ModelParametersConfig",
    "DaemonConfig",
    "RateLimitsConfig",
    "TaskConfig",
    "MissionConfig",
    # Memory & Janitor
    "MemoryConfig",
    "JanitorConfig",
    # Harness
    "HarnessConfig",
    "CostTrackingConfig",
    "HeartbeatConfig",
    "CheckpointConfig",
    "StateConfig",
    "AuditConfig",
    # Security
    "SecurityConfig",
    # Planner-Worker
    "PlannerWorkerConfig",
    "PlannerConfig",
    "WorkerConfig",
]

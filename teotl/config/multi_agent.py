"""Multi-agent configuration parser.

Supports both single-agent and multi-agent config formats with full feature support.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


# =============================================================================
# Memory Configuration
# =============================================================================


class MemoryConfig(BaseModel):
    """Memory system configuration."""

    enabled: bool = False
    backend: Literal["local", "encrypted"] = "local"
    path: str | None = None  # Custom path for memory database
    auto_cleanup: bool = True
    max_memories: int = 10000
    # Encrypted memory options
    encryption_key_env: str | None = None  # Environment variable for encryption key


# =============================================================================
# Janitor (Context Management) Configuration
# =============================================================================


class JanitorConfig(BaseModel):
    """Context management/janitor configuration."""

    enabled: bool = True  # Auto-enabled if memory is enabled
    compact_every: int = 15  # Compact context every N turns
    max_context_tokens: int | None = None  # Auto-detect from model if None


# =============================================================================
# Harness Components Configuration
# =============================================================================


class CostTrackingConfig(BaseModel):
    """Cost tracking configuration."""

    enabled: bool = False
    max_per_hour: float = 5.0
    max_per_day: float = 50.0
    max_per_month: float = 500.0
    currency: str = "USD"
    log_file_name: str = "COST_LOG.jsonl"


class HeartbeatConfig(BaseModel):
    """Heartbeat monitoring configuration."""

    enabled: bool = False
    check_interval_turns: int = 5
    max_turns_without_progress: int = 10
    max_consecutive_errors: int = 5
    min_completion_per_hour: float = 5.0
    # Escalation
    notify_on_critical: bool = True
    notify_on_warning: bool = False
    # Cleanup
    archive_logs_older_than_days: int = 7
    max_archived_plans: int = 10


class CheckpointConfig(BaseModel):
    """Checkpoint/rollback configuration."""

    enabled: bool = False
    auto_checkpoint: bool = True
    checkpoint_prefix: str = "teotl-checkpoint"


class StateConfig(BaseModel):
    """Persistent state configuration."""

    enabled: bool = False
    enable_validation: bool = True


class AuditConfig(BaseModel):
    """Audit logging configuration."""

    enabled: bool = False
    log_file_name: str = "AUDIT_LOG.jsonl"
    redact_pii: bool = True
    max_prompt_length: int = 5000
    max_response_length: int = 10000


class HarnessConfig(BaseModel):
    """Combined harness components configuration."""

    cost_tracking: CostTrackingConfig | bool = False
    heartbeat: HeartbeatConfig | bool = False
    checkpoints: CheckpointConfig | bool = False
    state: StateConfig | bool = False
    audit: AuditConfig | bool = False

    def model_post_init(self, __context: Any) -> None:
        """Convert boolean shortcuts to full config objects."""
        if isinstance(self.cost_tracking, bool):
            object.__setattr__(
                self, "cost_tracking", CostTrackingConfig(enabled=self.cost_tracking)
            )
        if isinstance(self.heartbeat, bool):
            object.__setattr__(self, "heartbeat", HeartbeatConfig(enabled=self.heartbeat))
        if isinstance(self.checkpoints, bool):
            object.__setattr__(self, "checkpoints", CheckpointConfig(enabled=self.checkpoints))
        if isinstance(self.state, bool):
            object.__setattr__(self, "state", StateConfig(enabled=self.state))
        if isinstance(self.audit, bool):
            object.__setattr__(self, "audit", AuditConfig(enabled=self.audit))


# =============================================================================
# Security Configuration
# =============================================================================


class SecurityConfig(BaseModel):
    """Security policy configuration."""

    preset: Literal["strict", "moderate", "permissive", "autonomous-dev"] | None = None
    policy_file: str | None = None  # Path to security.yaml
    # Inline overrides (optional)
    log_level: Literal["minimal", "standard", "detailed", "paranoid"] | None = None
    cost_limits: dict[str, float] | None = None
    allowed_domains: list[str] | None = None
    blocked_paths: list[str] | None = None


# =============================================================================
# Model/Provider Configuration
# =============================================================================


class ModelParametersConfig(BaseModel):
    """Model-specific parameters."""

    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: list[str] | None = None


class ProviderConfig(BaseModel):
    """LLM provider configuration."""

    type: str  # "anthropic", "openai", "ollama", "google"
    model: str
    api_key_env: str | None = None
    base_url: str | None = None  # For custom endpoints
    parameters: ModelParametersConfig | None = None


# =============================================================================
# Planner-Worker Architecture
# =============================================================================


class WorkerConfig(BaseModel):
    """Worker configuration in planner-worker architecture."""

    provider: str | None = None  # Model name (uses parent provider type)
    skills: list[str] = []
    instructions: str | None = None
    max_turns: int = 50


class PlannerConfig(BaseModel):
    """Planner configuration in planner-worker architecture."""

    provider: str | None = None  # Model name (uses parent provider type)
    instructions: str | None = None


class PlannerWorkerConfig(BaseModel):
    """Planner-worker architecture configuration."""

    enabled: bool = False
    planner: PlannerConfig | None = None
    worker: WorkerConfig | None = None
    # Optional harness for planner-worker
    harness: HarnessConfig | None = None


# =============================================================================
# Agent Configuration
# =============================================================================


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    agent_id: str
    instructions: str = ""
    workspace: str | None = None
    skills: list[str] = []
    auto_approve: bool = True
    port: int | None = None  # A2A server port
    max_turns: int = 50

    # Optional: Enable injection defense
    enable_injection_defense: bool = True

    # Memory configuration
    memory: MemoryConfig | bool = False

    # Context management
    janitor: JanitorConfig | bool = Field(default=True)

    # Harness components
    harness: HarnessConfig | None = None

    # Security configuration
    security: SecurityConfig | None = None

    # Planner-worker architecture
    planner_worker: PlannerWorkerConfig | None = None

    # Work types this agent handles
    work_types: list[str] = []  # e.g., ["Tasks", "Missions", "Goals"]

    # Capabilities for routing
    capabilities: list[str] = []  # e.g., ["feature-impl", "bug-fixing"]

    def model_post_init(self, __context: Any) -> None:
        """Convert boolean shortcuts to full config objects."""
        if isinstance(self.memory, bool):
            object.__setattr__(self, "memory", MemoryConfig(enabled=self.memory))
        if isinstance(self.janitor, bool):
            object.__setattr__(self, "janitor", JanitorConfig(enabled=self.janitor))


# =============================================================================
# Daemon, Rate Limits, Tasks, Missions
# =============================================================================


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


# =============================================================================
# Multi-Agent Configuration
# =============================================================================


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


# =============================================================================
# Loading Functions
# =============================================================================


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

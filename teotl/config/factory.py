"""Factory functions for creating agents from YAML configuration.

This module provides the bridge between YAML config and actual Agent instances,
instantiating all necessary components (memory, harness, security, etc.).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from teotl.config.multi_agent import (
    AgentConfig,
    AuditConfig,
    CheckpointConfig,
    CostTrackingConfig,
    HeartbeatConfig,
    HarnessConfig,
    JanitorConfig,
    MemoryConfig,
    MultiAgentConfig,
    ProviderConfig,
    SecurityConfig,
    StateConfig,
    load_multi_agent_config,
)

if TYPE_CHECKING:
    from teotl.core.agent import Agent
    from teotl.core.provider import Provider

logger = logging.getLogger(__name__)


def create_provider(config: ProviderConfig) -> "Provider":
    """Create an LLM provider from configuration.

    Args:
        config: Provider configuration

    Returns:
        Configured Provider instance

    Raises:
        ValueError: If provider type is not supported
    """
    provider_type = config.type.lower()

    # Get API key from environment if specified
    api_key = None
    if config.api_key_env:
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            logger.warning(f"API key environment variable {config.api_key_env} not set")

    # Build extra kwargs from parameters
    # Note: Most providers only accept max_tokens at init time
    # Other params (temperature, top_p, etc.) are passed at request time
    extra_kwargs: dict[str, Any] = {}
    if config.parameters:
        if config.parameters.max_tokens is not None:
            extra_kwargs["max_tokens"] = config.parameters.max_tokens
        # Store other parameters for request-time use (if supported by provider)
        # These could be stored on the provider instance for use in complete()

    if provider_type == "anthropic":
        from teotl.core.provider import AnthropicProvider

        return AnthropicProvider(
            model=config.model,
            api_key=api_key,
            **extra_kwargs,
        )
    elif provider_type == "openai":
        from teotl.core.provider import OpenAIProvider

        return OpenAIProvider(
            model=config.model,
            api_key=api_key,
            base_url=config.base_url,
            **extra_kwargs,
        )
    elif provider_type == "ollama":
        from teotl.core.provider import OllamaProvider

        return OllamaProvider(
            model=config.model,
            host=config.base_url or "http://localhost:11434",
            **extra_kwargs,
        )
    elif provider_type == "google":
        from teotl.core.provider import GeminiProvider

        return GeminiProvider(
            model=config.model,
            api_key=api_key,
            **extra_kwargs,
        )
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")


def _create_memory(config: MemoryConfig, agent_id: str):
    """Create memory system from configuration.

    Args:
        config: Memory configuration
        agent_id: Agent identifier for default paths

    Returns:
        Memory instance or None if disabled
    """
    if not config.enabled:
        return None

    # Determine memory path
    if config.path:
        memory_path = Path(config.path).expanduser()
    else:
        memory_path = Path.home() / ".teotl" / "agents" / agent_id / "memory.db"

    if config.backend == "local":
        from teotl.primitives.memory.local import LocalMemory

        return LocalMemory(
            path=memory_path,
            auto_cleanup=config.auto_cleanup,
            max_memories=config.max_memories,
        )
    elif config.backend == "encrypted":
        from teotl.primitives.memory.encrypted import EncryptedMemory

        # Get encryption key from environment
        encryption_key = None
        if config.encryption_key_env:
            encryption_key = os.environ.get(config.encryption_key_env)
            if not encryption_key:
                raise ValueError(
                    f"Encryption key environment variable {config.encryption_key_env} not set"
                )

        return EncryptedMemory(
            path=memory_path,
            encryption_key=encryption_key,
            auto_cleanup=config.auto_cleanup,
            max_memories=config.max_memories,
        )
    else:
        raise ValueError(f"Unsupported memory backend: {config.backend}")


def _create_cost_tracker(config: CostTrackingConfig, workspace_dir: Path):
    """Create cost tracker from configuration.

    Args:
        config: Cost tracking configuration
        workspace_dir: Workspace directory for cost log

    Returns:
        CostTracker instance or None if disabled
    """
    if not config.enabled:
        return None

    from teotl.core.security.policy import CostLimits
    from teotl.primitives.harness.cost_tracker import CostTracker

    limits = CostLimits(
        max_per_hour=config.max_per_hour,
        max_per_day=config.max_per_day,
        max_per_month=config.max_per_month,
        currency=config.currency,
    )

    return CostTracker(
        limits=limits,
        workspace_dir=workspace_dir,
        log_file_name=config.log_file_name,
    )


def _create_heartbeat_monitor(config: HeartbeatConfig, agent_id: str, workspace_dir: Path):
    """Create heartbeat monitor from configuration.

    Args:
        config: Heartbeat configuration
        agent_id: Agent identifier
        workspace_dir: Workspace directory

    Returns:
        HeartbeatMonitor instance or None if disabled
    """
    if not config.enabled:
        return None

    from teotl.primitives.harness.heartbeat import (
        CleanupPolicy,
        ErrorThresholdCheck,
        EscalationPolicy,
        HeartbeatMonitor,
        ProgressRateCheck,
        StuckDetectionCheck,
    )

    # Create health checks
    checks = [
        StuckDetectionCheck(max_turns_without_progress=config.max_turns_without_progress),
        ErrorThresholdCheck(max_consecutive_errors=config.max_consecutive_errors),
        ProgressRateCheck(min_completion_per_hour=config.min_completion_per_hour),
    ]

    # Create escalation policy
    escalation_policy = EscalationPolicy(
        notify_on_critical=config.notify_on_critical,
        notify_on_warning=config.notify_on_warning,
    )

    # Create cleanup policy
    cleanup_policy = CleanupPolicy(
        archive_logs_older_than_days=config.archive_logs_older_than_days,
        max_archived_plans=config.max_archived_plans,
    )

    return HeartbeatMonitor(
        agent_id=agent_id,
        workspace_dir=workspace_dir,
        checks=checks,
        escalation_policy=escalation_policy,
        cleanup_policy=cleanup_policy,
        check_interval_turns=config.check_interval_turns,
    )


def _create_checkpoint_manager(config: CheckpointConfig, workspace_dir: Path):
    """Create checkpoint manager from configuration.

    Args:
        config: Checkpoint configuration
        workspace_dir: Workspace directory

    Returns:
        CheckpointManager instance or None if disabled
    """
    if not config.enabled:
        return None

    from teotl.primitives.harness.checkpoint import CheckpointManager

    return CheckpointManager(
        workspace_dir=workspace_dir,
        auto_checkpoint_enabled=config.auto_checkpoint,
        checkpoint_prefix=config.checkpoint_prefix,
    )


def _create_state_manager(config: StateConfig, agent_id: str, workspace_dir: Path):
    """Create state manager from configuration.

    Args:
        config: State configuration
        agent_id: Agent identifier
        workspace_dir: Workspace directory

    Returns:
        StateManager instance or None if disabled
    """
    if not config.enabled:
        return None

    from teotl.primitives.harness.state import StateManager

    return StateManager(
        agent_id=agent_id,
        workspace_dir=workspace_dir,
        enable_validation=config.enable_validation,
    )


def _create_audit_logger(config: AuditConfig, agent_id: str, workspace_dir: Path):
    """Create audit logger from configuration.

    Args:
        config: Audit configuration
        agent_id: Agent identifier
        workspace_dir: Workspace directory

    Returns:
        AuditLogger instance or None if disabled
    """
    if not config.enabled:
        return None

    from teotl.primitives.harness.audit import AuditLogger

    return AuditLogger(
        workspace_dir=workspace_dir,
        agent_id=agent_id,
        log_file_name=config.log_file_name,
        redact_pii=config.redact_pii,
        max_prompt_length=config.max_prompt_length,
        max_response_length=config.max_response_length,
    )


def _create_security_policy(config: SecurityConfig | None, agent_id: str):
    """Create security policy from configuration.

    Args:
        config: Security configuration
        agent_id: Agent identifier

    Returns:
        SecurityPolicy instance or string preset name
    """
    if not config:
        return "standard"  # Default policy

    # Load from file if specified
    if config.policy_file:
        from teotl.core.security.policy import SecurityPolicy

        return SecurityPolicy.from_file(Path(config.policy_file))

    # Create from preset
    if config.preset:
        from teotl.core.security.policy import SecurityPolicy

        policy = SecurityPolicy.create_default(agent_id, preset=config.preset)

        # Apply inline overrides if any
        if config.log_level:
            from teotl.core.security.policy import LogLevel

            policy.log_level = LogLevel(config.log_level)

        if config.cost_limits:
            if "max_per_hour" in config.cost_limits:
                policy.cost_limits.max_per_hour = config.cost_limits["max_per_hour"]
            if "max_per_day" in config.cost_limits:
                policy.cost_limits.max_per_day = config.cost_limits["max_per_day"]
            if "max_per_month" in config.cost_limits:
                policy.cost_limits.max_per_month = config.cost_limits["max_per_month"]

        if config.allowed_domains:
            policy.network.allowed_domains = config.allowed_domains

        if config.blocked_paths:
            policy.filesystem.blocked_paths = config.blocked_paths

        return policy

    return "standard"


def create_agent_from_config(
    agent_config: AgentConfig,
    provider: "Provider",
    workspace_dir: Path | None = None,
) -> "Agent":
    """Create an Agent instance from configuration.

    This is the main factory function that instantiates an Agent with all
    configured components (memory, harness, security, etc.).

    Args:
        agent_config: Agent configuration
        provider: LLM provider instance
        workspace_dir: Optional workspace directory override

    Returns:
        Fully configured Agent instance

    Example:
        ```python
        config = load_multi_agent_config("config.yaml")
        provider = create_provider(config.provider)

        for agent_id in config.agent_ids:
            agent_config = config.get_agent(agent_id)
            agent = create_agent_from_config(agent_config, provider)
        ```
    """
    from teotl.core.agent import Agent

    # Determine workspace directory
    if workspace_dir is None:
        if agent_config.workspace:
            workspace_dir = Path(agent_config.workspace).expanduser()
        else:
            workspace_dir = Path.home() / ".teotl" / "agents" / agent_config.agent_id

    # Ensure workspace exists
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Create memory system
    memory = None
    if isinstance(agent_config.memory, MemoryConfig):
        memory = _create_memory(agent_config.memory, agent_config.agent_id)

    # Create harness components
    cost_tracker = None
    heartbeat_monitor = None
    checkpoint_manager = None
    state_manager = None
    audit_logger = None

    if agent_config.harness:
        harness = agent_config.harness

        if isinstance(harness.cost_tracking, CostTrackingConfig):
            cost_tracker = _create_cost_tracker(harness.cost_tracking, workspace_dir)

        if isinstance(harness.heartbeat, HeartbeatConfig):
            heartbeat_monitor = _create_heartbeat_monitor(
                harness.heartbeat, agent_config.agent_id, workspace_dir
            )

        if isinstance(harness.checkpoints, CheckpointConfig):
            checkpoint_manager = _create_checkpoint_manager(harness.checkpoints, workspace_dir)

        if isinstance(harness.state, StateConfig):
            state_manager = _create_state_manager(
                harness.state, agent_config.agent_id, workspace_dir
            )

        if isinstance(harness.audit, AuditConfig):
            audit_logger = _create_audit_logger(harness.audit, agent_config.agent_id, workspace_dir)

    # Create security policy
    policy = _create_security_policy(agent_config.security, agent_config.agent_id)

    # Get janitor settings
    enable_auto_compact = None
    compact_every = 15
    max_context_tokens = None

    if isinstance(agent_config.janitor, JanitorConfig):
        enable_auto_compact = agent_config.janitor.enabled
        compact_every = agent_config.janitor.compact_every
        max_context_tokens = agent_config.janitor.max_context_tokens

    # Create the agent
    agent = Agent(
        provider=provider,
        instructions=agent_config.instructions,
        skills=agent_config.skills if agent_config.skills else None,
        policy=policy,
        memory=memory,
        max_turns=agent_config.max_turns,
        enable_injection_defense=agent_config.enable_injection_defense,
        # Harness components
        cost_tracker=cost_tracker,
        audit_logger=audit_logger,
        checkpoint_manager=checkpoint_manager,
        heartbeat_monitor=heartbeat_monitor,
        state_manager=state_manager,
        # Context management
        enable_auto_compact=enable_auto_compact,
        compact_every=compact_every,
        max_context_tokens=max_context_tokens,
    )

    # Store agent_id on the agent for reference
    agent.agent_id = agent_config.agent_id

    logger.info(
        f"Created agent '{agent_config.agent_id}' with: "
        f"memory={'enabled' if memory else 'disabled'}, "
        f"harness={agent_config.harness is not None}, "
        f"skills={agent_config.skills or 'none'}"
    )

    return agent


def create_agents_from_config(
    config: MultiAgentConfig,
    workspace_base: Path | None = None,
) -> dict[str, "Agent"]:
    """Create all agents from a multi-agent configuration.

    Args:
        config: Multi-agent configuration
        workspace_base: Base directory for agent workspaces

    Returns:
        Dictionary mapping agent IDs to Agent instances
    """
    # Create shared provider
    provider = create_provider(config.provider)

    agents = {}
    for agent_id in config.agent_ids:
        agent_config = config.get_agent(agent_id)
        if agent_config:
            # Determine workspace
            workspace_dir = None
            if workspace_base:
                workspace_dir = workspace_base / agent_id

            agents[agent_id] = create_agent_from_config(
                agent_config,
                provider,
                workspace_dir=workspace_dir,
            )

    return agents


def create_agent_from_yaml(
    config_path: str | Path,
    agent_id: str | None = None,
) -> "Agent":
    """Convenience function to create a single agent from YAML file.

    Args:
        config_path: Path to YAML configuration file
        agent_id: Optional agent ID (uses first agent if not specified)

    Returns:
        Configured Agent instance

    Example:
        ```python
        agent = create_agent_from_yaml("config.yaml")
        response = await agent.run("Hello!")
        ```
    """
    config = load_multi_agent_config(config_path)
    provider = create_provider(config.provider)

    # Get agent config
    if agent_id:
        agent_config = config.get_agent(agent_id)
        if not agent_config:
            raise ValueError(f"Agent '{agent_id}' not found in config")
    else:
        # Use first agent
        agent_id = config.agent_ids[0]
        agent_config = config.get_agent(agent_id)

    return create_agent_from_config(agent_config, provider)

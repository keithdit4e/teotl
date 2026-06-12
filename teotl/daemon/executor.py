"""Agent executor bridge for daemon.

This module bridges the HeartbeatDaemon with the Agent loop, enabling
autonomous task and mission execution.

The executor:
- Loads or creates agent instances
- Loads workspace files (PERSONALITY.md, INSTRUCTIONS.md, etc.)
- Executes tasks/missions via agent.run()
- Handles timeouts and errors
- Returns results in expected format
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from teotl.core.agent import Agent

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from teotl.core.provider import Provider

logger = logging.getLogger(__name__)


def load_workspace_files(workspace_dir: Path) -> str:
    """Load workspace files and combine into system prompt.

    Loads in this order:
    1. PERSONALITY.md - Agent identity, voice, values
    2. USER.md - User preferences and context
    3. INSTRUCTIONS.md - Operating procedures and rules
    4. SKILLS.md - Available capabilities

    Args:
        workspace_dir: Path to agent workspace directory

    Returns:
        Combined system prompt from all files, or empty string if no files exist
    """
    if not workspace_dir.exists():
        logger.debug(f"Workspace directory not found: {workspace_dir}")
        return ""

    files_to_load = [
        "PERSONALITY.md",
        "USER.md",
        "INSTRUCTIONS.md",
        "SKILLS.md",
    ]

    sections = []

    for filename in files_to_load:
        file_path = workspace_dir / filename
        if file_path.exists():
            try:
                with open(file_path) as f:
                    content = f.read().strip()
                if content:
                    sections.append(content)
                    logger.debug(f"Loaded workspace file: {filename}")
            except Exception as e:
                logger.warning(f"Failed to load {filename}: {e}")

    if sections:
        combined = "\n\n---\n\n".join(sections)
        logger.info(f"Loaded {len(sections)} workspace files from {workspace_dir}")
        return combined

    logger.debug(f"No workspace files found in {workspace_dir}")
    return ""


class AgentExecutor:
    """Executor that runs agent instances for daemon.

    This bridges autonomous execution (tasks/missions) with the agent loop.
    Each daemon instance has one executor that manages agent lifecycle.

    Usage:
        executor = AgentExecutor(
            agent_factory=lambda: Agent(provider=..., instructions=...)
        )
        result = await executor.execute("Write hello.txt", {"filename": "hello.txt"})
    """

    def __init__(
        self,
        agent_factory: Callable[[], Agent] | None = None,
        agent: Agent | None = None,
        timeout: int = 300,  # 5 minutes default
        auto_approve: bool = True,  # For headless execution
    ):
        """Initialize executor.

        Args:
            agent_factory: Factory function to create agent instances
            agent: Pre-configured agent instance (alternative to factory)
            timeout: Maximum execution time in seconds
            auto_approve: Auto-approve tool confirmations (headless mode)

        Either agent_factory OR agent must be provided.
        """
        if not agent_factory and not agent:
            raise ValueError("Must provide either agent_factory or agent")

        self.agent_factory = agent_factory
        self._agent = agent
        self.timeout = timeout
        self.auto_approve = auto_approve

    @property
    def agent(self) -> Agent:
        """Get or create agent instance.

        Uses factory if provided, otherwise returns pre-configured agent.
        Factory allows creating fresh instances per execution.
        """
        if self.agent_factory:
            return self.agent_factory()
        return self._agent

    async def execute(
        self,
        description: str,
        context: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> Any:
        """Execute a task or mission description.

        Args:
            description: Natural language task/mission description
            context: Additional context for execution (variables, params, etc.)
            timeout: Override default timeout for this execution

        Returns:
            Execution result (typically agent's final response text)

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
            Exception: Any error during agent execution
        """
        timeout = timeout or self.timeout
        context = context or {}

        logger.info(f"Executing: {description[:100]}...")
        logger.debug(f"Context: {context}")

        try:
            # Execute with timeout
            result = await asyncio.wait_for(self._run_agent(description, context), timeout=timeout)

            logger.info("Execution completed successfully")
            return result

        except TimeoutError:
            logger.error(f"Execution timed out after {timeout}s")
            raise

        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            raise

    async def _run_agent(self, description: str, context: dict[str, Any]) -> Any:
        """Run agent with description and context.

        This is where we bridge to the agent loop.

        Args:
            description: Task/mission description
            context: Execution context

        Returns:
            Agent's response (typically final message text)
        """
        # Get agent instance
        agent = self.agent

        # Create headless UI for autonomous execution
        from teotl.core.agent import _HeadlessUI

        ui = _HeadlessUI(auto_approve=self.auto_approve)

        # Build prompt with context
        if context:
            # Inject context as additional instructions
            prompt = self._build_prompt(description, context)
        else:
            prompt = description

        # Run agent
        try:
            response = await agent.run(prompt, ui=ui)

            # Extract result
            if hasattr(response, "text"):
                return response.text
            return str(response)

        except Exception as e:
            logger.error(f"Agent execution error: {e}", exc_info=True)
            raise

    def _build_prompt(self, description: str, context: dict[str, Any]) -> str:
        """Build prompt with context injection.

        Args:
            description: Base task description
            context: Context variables to inject

        Returns:
            Enhanced prompt with context
        """
        # Format context as key-value pairs
        context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])

        prompt = f"""{description}

Context:
{context_str}

Please complete the task using the provided context."""

        return prompt


class AgentExecutorFactory:
    """Factory for creating agent executors with different configurations.

    This simplifies creating executors for different agent types and use cases.

    Usage:
        factory = AgentExecutorFactory(
            provider=AnthropicProvider(),
            workspace_dir=Path("~/.forge/agents/my-agent")
        )

        # Create executor - automatically loads workspace files
        executor = factory.create(
            instructions="You are an email assistant",  # Combined with workspace files
            skills=["gmail"]
        )
    """

    def __init__(
        self,
        provider: Provider,
        policy: str = "standard",
        timeout: int = 300,
        auto_approve: bool = True,
        session_dir: Path | None = None,
        workspace_dir: Path | None = None,
        # Harness components (optional, for production safety)
        enable_cost_tracking: bool = False,
        enable_audit: bool = False,
        enable_checkpoints: bool = False,
        enable_heartbeat: bool = False,
        enable_state: bool = False,
    ):
        """Initialize factory.

        Args:
            provider: LLM provider for all agents
            policy: Default guardrail policy
            timeout: Default execution timeout
            auto_approve: Auto-approve confirmations
            session_dir: Directory for session storage
            workspace_dir: Agent workspace directory (for loading PERSONALITY.md, etc.)
        """
        self.provider = provider
        self.policy = policy
        self.timeout = timeout
        self.auto_approve = auto_approve
        self.session_dir = session_dir
        self.workspace_dir = workspace_dir

        # Harness flags
        self.enable_cost_tracking = enable_cost_tracking
        self.enable_audit = enable_audit
        self.enable_checkpoints = enable_checkpoints
        self.enable_heartbeat = enable_heartbeat
        self.enable_state = enable_state

        # Initialize harness components if enabled
        self.cost_tracker = None
        self.audit_logger = None
        self.checkpoint_manager = None
        self.heartbeat_monitor = None
        self.state_manager = None

        if workspace_dir and any(
            [enable_cost_tracking, enable_audit, enable_checkpoints, enable_heartbeat, enable_state]
        ):
            self._init_harness_components()

    def _init_harness_components(self):
        """Initialize harness components based on enabled flags."""
        agent_id = self.workspace_dir.name if self.workspace_dir else "agent"

        if self.enable_cost_tracking:
            try:
                from teotl.core.security.policy import CostLimits
                from teotl.primitives.harness.cost_tracker import CostTracker

                limits = CostLimits(
                    max_per_hour=10.0,
                    max_per_day=100.0,
                    max_per_month=1000.0,
                )
                self.cost_tracker = CostTracker(limits=limits, workspace_dir=self.workspace_dir)
                logger.info("Cost tracking enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize cost tracker: {e}")

        if self.enable_audit:
            try:
                from teotl.primitives.harness.audit import AuditLogger

                self.audit_logger = AuditLogger(
                    workspace_dir=self.workspace_dir,
                    agent_id=agent_id,
                    redact_pii=True,
                )
                logger.info("Audit logging enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize audit logger: {e}")

        if self.enable_checkpoints:
            try:
                from teotl.primitives.harness.checkpoint import CheckpointManager

                self.checkpoint_manager = CheckpointManager(
                    workspace_dir=self.workspace_dir,
                    auto_checkpoint_enabled=True,
                )
                logger.info("Checkpoints enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize checkpoint manager: {e}")

        if self.enable_heartbeat:
            try:
                from teotl.primitives.harness.heartbeat import (
                    CleanupPolicy,
                    ErrorThresholdCheck,
                    EscalationPolicy,
                    HeartbeatMonitor,
                    StuckDetectionCheck,
                )

                self.heartbeat_monitor = HeartbeatMonitor(
                    agent_id=agent_id,
                    workspace_dir=self.workspace_dir,
                    checks=[
                        StuckDetectionCheck(max_turns_without_progress=10),
                        ErrorThresholdCheck(max_consecutive_errors=5),
                    ],
                    escalation_policy=EscalationPolicy(
                        notify_on_critical=True,
                        notify_on_warning=False,
                    ),
                    cleanup_policy=CleanupPolicy(
                        archive_logs_older_than_days=7,
                        max_archived_plans=10,
                    ),
                )
                logger.info("Heartbeat monitoring enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize heartbeat monitor: {e}")

        if self.enable_state:
            try:
                from teotl.primitives.harness.state import StateManager

                self.state_manager = StateManager(
                    agent_id=agent_id,
                    workspace_dir=self.workspace_dir,
                    enable_validation=True,
                )
                logger.info("State management enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize state manager: {e}")

    def create(
        self,
        instructions: str = "",
        skills: list[str] | None = None,
        policy: str | None = None,
        memory: Any | None = None,
        extensions: list[Any] | None = None,
        timeout: int | None = None,
        auto_approve: bool | None = None,
        # Janitor / context management
        enable_auto_compact: bool | None = None,
        compact_every: int = 15,
        max_context_tokens: int | None = None,
    ) -> AgentExecutor:
        """Create an executor with specific configuration.

        Args:
            instructions: Agent instructions (combined with workspace files if they exist)
            skills: Skills to load
            policy: Override default policy
            memory: Memory instance
            extensions: Agent extensions
            timeout: Override default timeout
            auto_approve: Override auto-approve setting

        Returns:
            Configured AgentExecutor
        """
        # Load workspace files and combine with instructions
        combined_instructions = self._build_instructions(instructions)

        def agent_factory() -> Agent:
            return Agent(
                provider=self.provider,
                instructions=combined_instructions,
                skills=skills,
                policy=policy or self.policy,
                memory=memory,
                extensions=extensions,
                session_dir=self.session_dir,
                # Janitor / context management
                enable_auto_compact=enable_auto_compact,
                compact_every=compact_every,
                max_context_tokens=max_context_tokens,
                # Pass harness components if enabled
                cost_tracker=self.cost_tracker,
                audit_logger=self.audit_logger,
                checkpoint_manager=self.checkpoint_manager,
                heartbeat_monitor=self.heartbeat_monitor,
                state_manager=self.state_manager,
            )

        return AgentExecutor(
            agent_factory=agent_factory,
            timeout=timeout or self.timeout,
            auto_approve=auto_approve if auto_approve is not None else self.auto_approve,
        )

    def _build_instructions(self, config_instructions: str) -> str:
        """Build complete instructions from workspace files + config.

        Priority order:
        1. Load workspace files (PERSONALITY.md, USER.md, INSTRUCTIONS.md, SKILLS.md)
        2. If workspace files exist, use them (config instructions are ignored)
        3. If no workspace files, fall back to config instructions

        Args:
            config_instructions: Instructions from config.yaml

        Returns:
            Complete instructions for agent
        """
        if not self.workspace_dir:
            # No workspace directory, use config instructions
            return config_instructions

        # Try to load workspace files
        workspace_content = load_workspace_files(self.workspace_dir)

        if workspace_content:
            # Workspace files exist - use them
            logger.info("Using workspace files for agent instructions")
            return workspace_content
        else:
            # No workspace files found - fall back to config
            logger.info("No workspace files found, using config instructions")
            return config_instructions


def create_simple_executor(
    provider: Provider,
    instructions: str = "",
    skills: list[str] | None = None,
    workspace_dir: Path | None = None,
    # Memory and context management
    memory: Any | None = None,
    enable_auto_compact: bool | None = None,
    compact_every: int = 15,
    max_context_tokens: int | None = None,
    # Harness features (optional)
    enable_cost_tracking: bool = False,
    enable_audit: bool = False,
    enable_checkpoints: bool = False,
    enable_heartbeat: bool = False,
    enable_state: bool = False,
    **kwargs,
) -> Callable[[str, dict[str, Any]], Any]:
    """Create a simple executor function for HeartbeatDaemon.

    This is a convenience function for creating the agent_executor
    callback required by HeartbeatDaemon.

    If workspace_dir is provided and contains workspace files (PERSONALITY.md,
    INSTRUCTIONS.md, USER.md, SKILLS.md), those files will be loaded and used
    as the agent's instructions. Otherwise, falls back to the instructions parameter.

    Args:
        provider: LLM provider
        instructions: Agent instructions (fallback if no workspace files)
        skills: Skills to load
        workspace_dir: Agent workspace directory (for loading workspace files)
        memory: Memory instance (enables persistent memory across sessions)
        enable_auto_compact: Enable automatic context compaction (None = auto-enable with memory)
        compact_every: Compact context every N turns (default: 15)
        max_context_tokens: Max tokens before compaction (None = auto-detect from model)
        enable_cost_tracking: Enable LLM cost tracking with budget limits
        enable_audit: Enable audit logging
        enable_checkpoints: Enable automatic checkpoints for recovery
        enable_heartbeat: Enable heartbeat monitoring for stuck detection
        enable_state: Enable persistent state management
        **kwargs: Additional AgentExecutor options

    Returns:
        Async function that executes tasks/missions

    Usage:
        from teotl.daemon.executor import create_simple_executor
        from teotl.core.provider import AnthropicProvider
        from pathlib import Path

        # With workspace files
        executor = create_simple_executor(
            provider=AnthropicProvider(),
            workspace_dir=Path("~/.forge/agents/my-agent"),
            skills=["filesystem"]
        )

        # Without workspace files (backward compatible)
        executor = create_simple_executor(
            provider=AnthropicProvider(),
            instructions="You are a helpful assistant",
            skills=["filesystem"]
        )

        daemon = HeartbeatDaemon(
            agent_id="my-agent",
            agent_executor=executor
        )
    """
    factory = AgentExecutorFactory(
        provider=provider,
        workspace_dir=workspace_dir,
        enable_cost_tracking=enable_cost_tracking,
        enable_audit=enable_audit,
        enable_checkpoints=enable_checkpoints,
        enable_heartbeat=enable_heartbeat,
        enable_state=enable_state,
    )
    executor = factory.create(
        instructions=instructions,
        skills=skills,
        memory=memory,
        enable_auto_compact=enable_auto_compact,
        compact_every=compact_every,
        max_context_tokens=max_context_tokens,
        **kwargs,
    )

    async def execute(description: str, context: dict[str, Any]) -> Any:
        return await executor.execute(description, context)

    return execute

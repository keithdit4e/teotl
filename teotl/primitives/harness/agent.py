"""Harness-enabled agent wrapper.

Wraps the core Agent with harness engineering capabilities:
- Progress tracking via PROGRESS.md
- State persistence via STATE.json
- Context compaction via DECISION_LOG.md
- Artifact-driven execution (reads state from files, not just conversation)
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from teotl.core.agent import Agent
from teotl.core.provider import Provider
from teotl.core.types import UI, Extension, Response, ToolDefinition
from teotl.primitives.harness.janitor import ContextJanitor
from teotl.primitives.harness.progress import ProgressTracker
from teotl.primitives.harness.state import StateManager

logger = logging.getLogger(__name__)


class HarnessAgent:
    """Agent wrapper with harness engineering primitives.

    Adds durable state management on top of the core Agent:
    - PROGRESS.md tracking
    - STATE.json persistence
    - DECISION_LOG.md compaction
    - Artifact loading before each turn

    Usage:
        agent = HarnessAgent(
            agent_id="coding-assistant",
            provider=AnthropicProvider(...),
            instructions="You are a helpful assistant",
            enable_progress=True,
            enable_state=True,
            enable_janitor=True,
            compact_every=10
        )

        # Use like normal Agent
        response = await agent.run("Improve code quality")

        # Access harness primitives
        agent.progress.update(current="Adding type hints", completed=[], remaining=[...])
        agent.state.save(phase="testing", tests_passed=4)
    """

    def __init__(
        self,
        agent_id: str,
        provider: Provider,
        instructions: str | Callable[..., str] = "",
        workspace_dir: Path | None = None,
        skills: list[str] | None = None,
        policy: str | Any = "standard",
        memory: Any | None = None,
        extensions: list[Extension] | None = None,
        tools: list[ToolDefinition] | None = None,
        session_dir: Path | None = None,
        max_turns: int = 50,
        enable_injection_defense: bool = True,
        # Harness options
        enable_progress: bool = True,
        enable_state: bool = True,
        enable_janitor: bool = True,
        compact_every: int = 10,
        load_artifacts_in_prompt: bool = True,
    ):
        """Initialize harness agent.

        Args:
            agent_id: Agent identifier (used for workspace)
            provider: LLM provider
            instructions: Agent instructions (can include {artifacts} placeholder)
            workspace_dir: Workspace directory (defaults to ~/.forge/agents/{agent_id})
            skills: List of skills to enable
            policy: Security policy
            memory: Memory system
            extensions: Agent extensions
            tools: Custom tools
            session_dir: Session storage directory
            max_turns: Maximum turns per run
            enable_injection_defense: Enable prompt injection defense
            enable_progress: Enable PROGRESS.md tracking
            enable_state: Enable STATE.json persistence
            enable_janitor: Enable DECISION_LOG.md compaction
            compact_every: Compact context every N turns
            load_artifacts_in_prompt: Automatically inject artifact content in prompt
        """
        self.agent_id = agent_id
        self.load_artifacts_in_prompt = load_artifacts_in_prompt

        # Determine workspace directory
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path.home() / ".forge" / "agents" / agent_id

        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Use workspace session dir if not specified
        if session_dir is None:
            session_dir = self.workspace_dir / "sessions"
            session_dir.mkdir(exist_ok=True)

        # Initialize harness primitives
        self.progress = ProgressTracker(agent_id, self.workspace_dir) if enable_progress else None
        self.state = StateManager(agent_id, self.workspace_dir) if enable_state else None
        self.janitor = (
            ContextJanitor(agent_id, self.workspace_dir, compact_every) if enable_janitor else None
        )

        # Create underlying agent
        self.agent = Agent(
            provider=provider,
            instructions=instructions,
            skills=skills,
            policy=policy,
            memory=memory,
            extensions=extensions,
            tools=tools,
            session_dir=session_dir,
            max_turns=max_turns,
            enable_injection_defense=enable_injection_defense,
        )

        logger.info(
            f"HarnessAgent initialized: {agent_id} "
            f"(progress={enable_progress}, state={enable_state}, janitor={enable_janitor})"
        )

    async def run(self, message: str, *, ui: UI | None = None) -> Response:
        """Execute agent with harness capabilities.

        Args:
            message: User message
            ui: UI adapter

        Returns:
            Agent response
        """
        # Load artifacts and inject into message if enabled
        if self.load_artifacts_in_prompt:
            message = self._inject_artifacts(message)

        # Run agent
        response = await self.agent.run(message, ui=ui)

        # After turn: update janitor
        if self.janitor:
            self.janitor.after_turn(response.text)

            # Check if we should reset context
            if self.janitor.should_reset_context():
                logger.info(f"Context compaction triggered at turn {self.janitor.get_turn_count()}")
                # Context reset would happen here
                # For now, just log it - actual reset needs agent support

        return response

    def _inject_artifacts(self, message: str) -> str:
        """Inject artifact content into message.

        Loads PROGRESS.md, STATE.json, and DECISION_LOG.md and prepends
        to the user message so agent has full context.

        Args:
            message: Original user message

        Returns:
            Message with artifacts prepended
        """
        artifact_parts = []

        # Load PROGRESS.md
        if self.progress and self.progress.exists():
            progress_content = self.progress.path.read_text()
            artifact_parts.append(f"# Your Progress\n\n{progress_content}")

        # Load STATE.json
        if self.state and self.state.exists():
            state_content = self.state.path.read_text()
            artifact_parts.append(f"# Your State\n\n```json\n{state_content}\n```")

        # Load DECISION_LOG.md (last 100 lines to avoid bloat)
        if self.janitor and self.janitor.decision_log_path.exists():
            decision_content = self.janitor.decision_log_path.read_text()
            lines = decision_content.split("\n")
            if len(lines) > 100:
                # Keep header + last 100 lines
                decision_content = "\n".join(lines[:10] + ["...\n"] + lines[-90:])
            artifact_parts.append(f"# Recent Decisions\n\n{decision_content}")

        # Combine artifacts with message
        if artifact_parts:
            artifacts = "\n\n---\n\n".join(artifact_parts)
            return f"{artifacts}\n\n---\n\n# Current Request\n\n{message}"

        return message

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable,
    ) -> None:
        """Register a tool (delegates to underlying agent)."""
        self.agent.register_tool(name, description, parameters, handler)

    def register_extension(self, extension: Extension) -> None:
        """Register an extension (delegates to underlying agent)."""
        self.agent.register_extension(extension)

    @property
    def events(self):
        """Access event bus."""
        return self.agent.events

    @property
    def session(self):
        """Access session."""
        return self.agent.session

    @property
    def skills_registry(self):
        """Access skills registry."""
        return self.agent.skills if hasattr(self.agent, "skills") else None

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"HarnessAgent(agent_id='{self.agent_id}', "
            f"progress={self.progress is not None}, "
            f"state={self.state is not None}, "
            f"janitor={self.janitor is not None})"
        )

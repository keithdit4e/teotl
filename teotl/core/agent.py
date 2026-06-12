"""The agent loop. Thin by design."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import ulid

from teotl.core.events import EventBus
from teotl.core.session import Session
from teotl.core.types import (
    UI,
    Extension,
    Response,
    ToolCall,
    ToolDefinition,
    ToolResult,
)
from teotl.primitives.guardrails.prompt_injection import (
    build_injection_resistant_prompt,
    detect_injection,
    validate_instructions,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from teotl.core.provider import Provider

logger = logging.getLogger(__name__)


class _HeadlessUI:
    """Default UI that auto-approves everything. For programmatic use."""

    def __init__(self, auto_approve: bool = True) -> None:
        self.auto_approve = auto_approve

    async def confirm(self, message: str, *, title: str = "") -> bool:
        return self.auto_approve

    async def display(self, message: str) -> None:
        pass

    async def input(self, prompt: str = "") -> str:
        return ""

    async def error(self, message: str) -> None:
        logger.error(message)


class Agent:
    """
    The Forge agent loop.

    Thin by design — the loop coordinates between:
    - Provider (LLM API)
    - Session (conversation history)
    - EventBus (hooks for guardrails, memory, etc.)
    - Skills (progressive disclosure)
    - Memory (cross-session persistence)

    Everything else is an extension.
    """

    def __init__(
        self,
        provider: Provider,
        instructions: str | Callable[..., str] = "",
        skills: list[str] | None = None,
        policy: str | Any = "standard",
        memory: Any | None = None,
        extensions: list[Extension] | None = None,
        tools: list[ToolDefinition] | None = None,
        session_dir: Path | None = None,
        max_turns: int = 50,
        enable_injection_defense: bool = True,
        # Harness components (optional)
        cost_tracker: Any | None = None,
        audit_logger: Any | None = None,
        checkpoint_manager: Any | None = None,
        heartbeat_monitor: Any | None = None,
        state_manager: Any | None = None,
        # Context management (auto-enabled with memory)
        enable_auto_compact: bool | None = None,  # Auto-enabled when memory enabled
        compact_every: int = 15,  # Compact every N turns
        max_context_tokens: int | None = None,  # Auto-detected from model if None
    ) -> None:
        self.provider = provider
        self.instructions = instructions
        self.max_turns = max_turns
        self.enable_injection_defense = enable_injection_defense

        # Validate instructions for security issues
        if enable_injection_defense and instructions:
            inst_str = instructions if isinstance(instructions, str) else ""
            is_safe, reason = validate_instructions(inst_str)
            if not is_safe:
                logger.warning(f"Instructions validation warning: {reason}")

        # Core systems
        self.events = EventBus()
        self.session = Session(
            path=session_dir / f"{ulid.new().str}.jsonl" if session_dir else None
        )
        self._tools: list[ToolDefinition] = tools or []
        self._tool_handlers: dict[str, Callable] = {}
        self._commands: dict[str, Callable] = {}

        # Core primitives (lazy-loaded to avoid circular imports)
        self._init_guardrails(policy)
        self._init_memory(memory)
        self._init_skills(skills)

        # Harness components (optional, for production safety)
        self.cost_tracker = cost_tracker
        self.audit_logger = audit_logger
        self.checkpoint_manager = checkpoint_manager
        self.heartbeat = heartbeat_monitor
        self.state_manager = state_manager

        # Context management (auto-enabled with memory)
        self._init_janitor(
            enable_auto_compact=enable_auto_compact,
            compact_every=compact_every,
            max_context_tokens=max_context_tokens,
        )

        # Activate extensions
        for ext in extensions or []:
            self.register_extension(ext)

    def _init_guardrails(self, policy: str | Any) -> None:
        """Initialize guardrails if available."""
        try:
            from teotl.primitives.guardrails.engine import GuardrailEngine

            self.guardrails = GuardrailEngine(policy)
            self.events.on("tool_call", self.guardrails.evaluate, priority=-100)
            logger.debug(f"Guardrails initialized with policy: {policy}")
        except Exception as e:
            logger.debug(f"Guardrails not initialized: {e}")
            self.guardrails = None

    def _init_memory(self, memory: Any | None) -> None:
        """Initialize memory system if available."""
        try:
            # Only auto-create memory if explicitly enabled
            # Store whether memory was user-provided
            self._memory_user_provided = memory is not None

            if memory is None:
                # Don't auto-create memory - let user opt-in
                self.memory = None
                logger.debug("Memory system not initialized (opt-in required)")
            else:
                self.memory = memory
                logger.debug("Memory system initialized")
        except Exception as e:
            logger.debug(f"Memory not initialized: {e}")
            self.memory = None
            self._memory_user_provided = False

    def _init_skills(self, skills: list[str] | None) -> None:
        """Initialize skills registry if available."""
        try:
            from teotl.primitives.skills.registry import SkillRegistry

            self.skills = SkillRegistry(skills)
            logger.debug(f"Skills initialized: {skills}")

            # Auto-register bash tool for skill execution
            self._register_bash_tool()
        except Exception as e:
            logger.debug(f"Skills not initialized: {e}")
            self.skills = None

    def _init_janitor(
        self,
        enable_auto_compact: bool | None,
        compact_every: int,
        max_context_tokens: int | None,
    ) -> None:
        """Initialize context janitor if memory is enabled.

        The janitor automatically manages context size by:
        1. Extracting key decisions from agent responses
        2. Storing decisions as memories (not just logs)
        3. Compacting context when thresholds are reached
        4. Preserving important information while resetting context

        Args:
            enable_auto_compact: Enable automatic compaction (default: True if memory enabled)
            compact_every: Compact every N turns (default: 15)
            max_context_tokens: Max tokens before forced compaction (default: auto-detect from model)
        """
        # Auto-enable if memory is enabled and not explicitly disabled
        if enable_auto_compact is None:
            enable_auto_compact = self.memory is not None

        if not enable_auto_compact:
            self.janitor = None
            logger.debug("Context janitor disabled")
            return

        if not self.memory:
            logger.warning("Context janitor requires memory system - disabling janitor")
            self.janitor = None
            return

        try:
            from teotl.primitives.harness.janitor import ContextJanitor

            # Auto-detect max_context_tokens from model if not specified
            if max_context_tokens is None:
                max_context_tokens = self._detect_context_limit()

            # Create janitor with memory integration
            self.janitor = ContextJanitor(
                agent_id=getattr(self, "agent_id", "agent"),
                workspace_dir=self.session.path.parent if self.session.path else None,
                compact_every=compact_every,
                decision_extractor=None,  # Use default keyword extraction
            )

            # Store config
            self.janitor.max_context_tokens = max_context_tokens
            self.janitor.compact_every = compact_every
            self.janitor._memory = self.memory  # Link to memory system

            logger.info(
                f"Context janitor initialized: compact_every={compact_every}, "
                f"max_tokens={max_context_tokens}"
            )
        except Exception as e:
            logger.debug(f"Janitor not initialized: {e}")
            self.janitor = None

    def _detect_context_limit(self) -> int:
        """Auto-detect context window limit from model name.

        Returns:
            Recommended max context tokens before compaction
        """
        model = self.provider.model.lower()

        # Claude models (200K context)
        if "claude-3" in model or "claude-opus" in model or "claude-sonnet" in model:
            # Use 50% of context window for safety (100K tokens)
            return 100_000

        # GPT-4 Turbo (128K context)
        if "gpt-4-turbo" in model or "gpt-4-1106" in model:
            return 64_000

        # GPT-4 (8K or 32K context)
        if "gpt-4-32k" in model:
            return 16_000
        if "gpt-4" in model:
            return 4_000

        # GPT-3.5 (16K context)
        if "gpt-3.5" in model or "gpt-35" in model:
            return 8_000

        # Default: conservative 10K tokens
        logger.warning(f"Unknown model '{model}' - using default context limit of 10,000 tokens")
        return 10_000

    def _register_bash_tool(self) -> None:
        """Register bash tool for executing skill commands."""
        try:
            from teotl.core.tools.bash import create_bash_tool

            bash_tool = create_bash_tool(self)
            tool_def = bash_tool.get_tool_definition()

            self.register_tool(
                name=tool_def["name"],
                description=tool_def["description"],
                parameters=tool_def["parameters"],
                handler=bash_tool.execute,
            )

            logger.info("Bash tool registered for skill execution")
        except Exception as e:
            logger.warning(f"Failed to register bash tool: {e}")

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    async def run(self, message: str, *, ui: UI | None = None) -> Response:
        """
        Execute a single user turn through the agent loop.

        This may result in multiple LLM calls if the agent uses tools.

        Args:
            message: User's input message.
            ui: UI adapter for confirmations and display. Defaults to headless.

        Returns:
            Response with the agent's final text and metadata.
        """
        ui = ui or _HeadlessUI()

        # Emit session start on first message
        if self.session.message_count == 0:
            await self.events.emit("session_start", self.session)

        # Emit turn start
        await self.events.emit("turn_start", {"message": message}, ui=ui)

        # Check for prompt injection if defense is enabled
        if self.enable_injection_defense:
            is_suspicious, reason = detect_injection(message, strict=False)
            if is_suspicious:
                logger.warning(f"Potential prompt injection detected: {reason}")
                # Log the event but don't block - use defenses instead
                await self.events.emit(
                    "injection_detected", {"message": message, "reason": reason}, ui=ui
                )

        # Retrieve relevant memories if memory system is enabled
        memory_context = ""
        if self.memory:
            try:
                memories = await self.memory.recall(message, limit=10)
                if memories:
                    memory_context = self.memory.format_for_context(memories, token_budget=500)
            except Exception as e:
                logger.warning(f"Failed to recall memories: {e}")

        # Build context with injection defenses
        system_prompt = self._build_system_prompt(memory_context=memory_context)

        # Apply injection-resistant formatting if enabled
        if self.enable_injection_defense:
            system_prompt, formatted_message = build_injection_resistant_prompt(
                system_prompt, message, delimiter_style="xml"
            )
            # Store the formatted message for context
            self.session.add_user(formatted_message)
        else:
            self.session.add_user(message)

        messages = self.session.get_context_messages()

        # Agent loop — may iterate if tool calls are made
        all_tool_calls: list[ToolCall] = []
        turns = 0

        while turns < self.max_turns:
            turns += 1

            # Cost tracking: Check budget before LLM call
            if self.cost_tracker:
                # Estimate cost based on input tokens (rough estimate)
                estimated_cost = 0.01  # Simple estimate, real impl would count tokens
                if not self.cost_tracker.can_spend(estimated_cost):
                    logger.error("Budget exceeded, halting execution")
                    break

            result = await self.provider.complete(
                system=system_prompt,
                messages=messages,
                tools=self._tools if self._tools else None,
            )

            # Cost tracking: Record actual cost
            cost = 0.0
            if self.cost_tracker and hasattr(result, "usage"):
                # Calculate cost from usage (model-dependent)
                input_tokens = result.usage.get("input_tokens", 0)
                output_tokens = result.usage.get("output_tokens", 0)
                # Simple cost calculation (would be model-specific in real impl)
                cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)
                self.cost_tracker.record(cost, f"turn_{turns}")

            # Audit logging: Log LLM interaction
            if self.audit_logger:
                self.audit_logger.log_agent_turn(
                    turn=turns,
                    prompt=message if turns == 1 else "continuation",
                    response=result.content,
                    model=self.provider.model,
                    cost=cost,
                    tool_calls=[{"name": tc.name, "args": tc.args} for tc in result.tool_calls]
                    if result.tool_calls
                    else [],
                    success=True,
                )

            if result.done:
                # No tool calls — final response
                self.session.add_assistant(result.content)

                # Auto-activate skills mentioned in response
                await self._auto_activate_skills(result.content)
                break

            # Add assistant message with tool use
            assistant_content = []
            if result.content:
                assistant_content.append({"type": "text", "text": result.content})

            for tool_call in result.tool_calls:
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "input": tool_call.args,
                    }
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_content,
                }
            )

            # Process tool calls and collect results
            tool_result_content = []
            for tool_call in result.tool_calls:
                all_tool_calls.append(tool_call)
                tool_result = await self._handle_tool_call(tool_call, ui=ui)

                tool_result_content.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": tool_result.output
                        if not tool_result.is_error
                        else tool_result.error,
                        "is_error": tool_result.is_error,
                    }
                )

            # Add user message with tool results
            messages.append(
                {
                    "role": "user",
                    "content": tool_result_content,
                }
            )

            # Auto-activate skills mentioned in assistant response
            await self._auto_activate_skills(result.content)

        else:
            logger.warning(f"Agent hit max turns ({self.max_turns})")

        # Emit turn end
        await self.events.emit("turn_end", {"message": message, "response": result}, ui=ui)

        # Heartbeat monitoring: Check agent health
        if self.heartbeat:
            try:
                # Update heartbeat state
                state = {
                    "current_turn": turns,
                    "last_progress_turn": turns,
                    "consecutive_errors": 0,
                }
                escalations = await self.heartbeat.check(state)
                if escalations:
                    for escalation in escalations:
                        logger.warning(
                            f"Heartbeat escalation: {escalation.title} - {escalation.message}"
                        )
            except Exception as e:
                logger.warning(f"Heartbeat monitoring failed: {e}")

        # State management: Update persistent state
        if self.state_manager:
            try:
                self.state_manager.save(
                    current_turn=turns,
                    last_response=result.content[:100] if result.content else "",
                    phase="executing",
                )
            except Exception as e:
                logger.warning(f"State update failed: {e}")

        # Extract memories from this turn if memory system is enabled
        # This is lightweight - full extraction happens at session end
        if self.memory:
            await self._extract_turn_memories(message, result.content)

        # Context management: Track decisions and compact if needed
        if self.janitor:
            try:
                # Estimate context size from messages
                context_snapshot = str(messages)  # Rough estimate

                # Process turn (extracts decisions, stores as memories) - await async method
                await self.janitor.after_turn(result.content, context_snapshot)

                # Check if context should be compacted
                if self.janitor.should_compact():
                    logger.info(
                        f"Context compaction triggered at turn {turns} "
                        f"(~{self.janitor._estimated_tokens} tokens)"
                    )
                    # Compact context (logs decisions to DECISION_LOG.md and stores as memories)
                    self.janitor.compact()

                    # Note: We DON'T clear the session.messages list because:
                    # 1. Session is append-only by design (audit trail)
                    # 2. Next turn will use memory.recall() to retrieve important decisions
                    # 3. Token budget in get_context_messages() limits what goes to LLM
                    # 4. This preserves full history while managing context window

                    # Reset token estimate (next turn starts fresh)
                    self.janitor._estimated_tokens = 2000  # Roughly: system + recent messages

                    logger.info(
                        "Context compaction complete - important decisions stored as memories"
                    )
            except Exception as e:
                logger.warning(f"Context compaction failed: {e}")

        return Response(
            text=result.content,
            tool_calls_made=all_tool_calls,
            tokens_used=result.usage.get("input_tokens", 0) + result.usage.get("output_tokens", 0),
        )

    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Register a tool the agent can use."""
        self._tools.append(
            ToolDefinition(
                name=name,
                description=description,
                parameters=parameters or {"type": "object", "properties": {}},
            )
        )
        self._tool_handlers[name] = handler

    def register_command(self, name: str, handler: Callable) -> None:
        """Register a slash command (e.g., /undo, /memory)."""
        self._commands[name] = handler

    def register_extension(self, extension: Extension) -> None:
        """Activate an extension on this agent."""
        extension.activate(self)
        logger.info(f"Extension activated: {extension.name} v{extension.version}")

    async def activate_skill(self, skill_name: str) -> str:
        """
        Manually activate a skill by name.

        Args:
            skill_name: Name of the skill to activate

        Returns:
            The full skill instructions loaded into context

        Raises:
            ValueError: If skills system is not initialized
            SkillNotFound: If skill_name is not registered
        """
        if not self.skills:
            raise ValueError("Skills system not initialized")

        instructions = await self.skills.activate(skill_name)
        logger.info(f"Manually activated skill: {skill_name}")
        return instructions

    def deactivate_skill(self, skill_name: str) -> None:
        """
        Manually deactivate a skill by name.

        Args:
            skill_name: Name of the skill to deactivate
        """
        if not self.skills:
            return

        self.skills.deactivate(skill_name)
        logger.info(f"Manually deactivated skill: {skill_name}")

    def list_skills(self) -> dict[str, str]:
        """
        List all registered skills with their descriptions.

        Returns:
            Dict mapping skill names to descriptions
        """
        if not self.skills:
            return {}

        return {name: meta.description for name, meta in self.skills.skills.items()}

    def list_active_skills(self) -> list[str]:
        """
        List all currently active skills.

        Returns:
            List of active skill names
        """
        if not self.skills:
            return []

        return list(self.skills.active.keys())

    async def remember(
        self,
        content: str,
        *,
        importance: int = 5,
        tags: list[str] | None = None,
        ttl_days: int | None = None,
    ) -> str:
        """
        Manually store a memory.

        Args:
            content: The content to remember
            importance: Importance rating 1-10 (default: 5)
            tags: Optional list of tags for categorization
            ttl_days: Time-to-live in days (None = use importance-based default)

        Returns:
            Memory ID

        Raises:
            ValueError: If memory system is not initialized
        """
        if not self.memory:
            raise ValueError("Memory system not initialized")

        from teotl.core.types import MemoryMeta

        memory_id = await self.memory.remember(
            content,
            MemoryMeta(
                source="manual",
                importance=importance,
                tags=tags or [],
                session_id=self.session.id if hasattr(self.session, "id") else None,
            ),
            ttl_days=ttl_days,
        )
        logger.info(f"Manually stored memory: {content[:50]}...")
        return memory_id

    async def recall(self, query: str, *, limit: int = 10) -> list:
        """
        Manually retrieve memories.

        Args:
            query: Search query
            limit: Maximum number of memories to return

        Returns:
            List of Memory objects

        Raises:
            ValueError: If memory system is not initialized
        """
        if not self.memory:
            raise ValueError("Memory system not initialized")

        memories = await self.memory.recall(query, limit=limit)
        logger.info(f"Retrieved {len(memories)} memories for query: {query}")
        return memories

    async def forget(self, memory_id: str) -> bool:
        """
        Delete a specific memory.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If memory system is not initialized
        """
        if not self.memory:
            raise ValueError("Memory system not initialized")

        deleted = await self.memory.forget(memory_id)
        if deleted:
            logger.info(f"Deleted memory: {memory_id}")
        return deleted

    async def list_memories(self, *, limit: int = 100, offset: int = 0) -> list:
        """
        List all memories with pagination.

        Args:
            limit: Maximum number of memories to return
            offset: Number of memories to skip

        Returns:
            List of Memory objects

        Raises:
            ValueError: If memory system is not initialized
        """
        if not self.memory:
            raise ValueError("Memory system not initialized")

        return await self.memory.list_all(limit=limit, offset=offset)

    # -------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------

    def _build_system_prompt(self, *, memory_context: str = "") -> str:
        """Assemble the full system prompt.

        Includes:
        1. Base instructions (who the agent is, what it does)
        2. Workspace context (where it is, what it's working on)
        3. State context (what phase, what progress)
        4. Skill descriptions (what tools are available)
        5. Memory context (what it remembers from previous turns)
        """
        parts: list[str] = []

        # Base instructions (identity and capabilities)
        instructions = self.instructions
        if callable(instructions):
            instructions = instructions()
        if instructions:
            parts.append(instructions)

        # Workspace and state context (mission, phase, progress)
        # This is CRITICAL after compaction - agent needs to know where it is!
        workspace_context = self._build_workspace_context()
        if workspace_context:
            parts.append(workspace_context)

        # Skill descriptions (always in context, ~50 tokens each)
        if self.skills:
            descriptions = self.skills.get_descriptions()
            if descriptions:
                parts.append(descriptions)

            # Active skill instructions (loaded on-demand, ~500-2000 tokens each)
            active_instructions = self.skills.get_active_instructions()
            if active_instructions:
                parts.append("## Active Skills\n\n" + active_instructions)

        # Memory context (relevant memories, budget-aware)
        if memory_context:
            parts.append("## Relevant Context from Memory\n\n" + memory_context)

        return "\n\n".join(parts)

    def _build_workspace_context(self) -> str:
        """Build workspace and state context for system prompt.

        This provides critical situational awareness, especially after compaction.

        Returns:
            Formatted workspace context string
        """
        context_parts: list[str] = []

        # State manager provides execution state
        if self.state_manager:
            try:
                state = self.state_manager.load()

                context_parts.append("## Current Execution Context")
                context_parts.append("")

                # Phase information
                if state.get("phase"):
                    context_parts.append(f"**Phase:** {state.get('phase')}")

                # Step/turn information
                if state.get("current_step"):
                    context_parts.append(f"**Current Step:** {state.get('current_step')}")
                if state.get("current_turn"):
                    context_parts.append(f"**Turn:** {state.get('current_turn')}")

                # Progress information
                if state.get("last_progress_turn"):
                    context_parts.append(
                        f"**Last Progress:** Turn {state.get('last_progress_turn')}"
                    )

                # Error/health information
                if state.get("consecutive_errors", 0) > 0:
                    context_parts.append(
                        f"**⚠️ Consecutive Errors:** {state.get('consecutive_errors')}"
                    )
                    if state.get("last_error"):
                        context_parts.append(f"**Last Error:** {state.get('last_error')}")

                # Halt status
                if state.get("halted"):
                    context_parts.append(
                        f"**⚠️ HALTED:** {state.get('halt_reason', 'Unknown reason')}"
                    )

                context_parts.append("")

            except Exception as e:
                logger.debug(f"Could not load state for context: {e}")

        # Janitor provides decision log context (high-level summary)
        if self.janitor:
            try:
                # Read recent decisions from decision log
                if self.janitor.decision_log_path.exists():
                    log_content = self.janitor.decision_log_path.read_text()

                    # Extract last 5 decisions for context
                    import re

                    decisions = re.findall(r"\*\*Turn \d+\*\*[^:]*: (.+)", log_content)

                    if decisions:
                        context_parts.append("## Recent Decisions (from Decision Log)")
                        context_parts.append("")

                        # Show last 5 decisions for quick context
                        for decision in decisions[-5:]:
                            context_parts.append(f"- {decision}")

                        context_parts.append("")

            except Exception as e:
                logger.debug(f"Could not load decision log for context: {e}")

        if not context_parts:
            return ""

        return "\n".join(context_parts)

    async def _extract_turn_memories(self, user_message: str, assistant_response: str) -> None:
        """
        Extract memorable facts from turn using lightweight pattern matching.

        Looks for explicit memory patterns like:
        - "Remember that..."
        - "My name is..."
        - "I prefer..."
        - "Note that..."

        Full LLM-based extraction happens at session end for better accuracy.
        """
        import re

        from teotl.core.types import MemoryMeta

        # Pattern definitions: (pattern, store_full_match)
        # If store_full_match=True, store entire matched statement (for short extracts like names)
        # If store_full_match=False, store only the captured group
        patterns = [
            (r"(?i)remember (?:that )?(.+?)(?:[.!?]|$)", False),
            (
                r"(?i)((?:my|the|our) name is [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)(?:[.!?]|$)",
                True,
            ),  # "My name is Alice"
            (r"(?i)(i (?:prefer|like|want|need|use) .+?)(?:[.!?]|$)", True),  # "I prefer dark mode"
            (r"(?i)note (?:that )?(.+?)(?:[.!?]|$)", False),
            (r"(?i)(?:please )?keep in mind (?:that )?(.+?)(?:[.!?]|$)", False),
        ]

        # Check user message for explicit memory requests
        for pattern, store_full in patterns:
            matches = re.finditer(pattern, user_message)
            for match in matches:
                content = match.group(1).strip()

                # For patterns where we store the full match (like "My name is Alice"),
                # use the entire captured statement even if short
                if store_full or (len(content) > 10 and len(content) < 500):
                    try:
                        await self.memory.remember(
                            content,
                            MemoryMeta(
                                source="explicit",
                                importance=8,  # User explicitly asked to remember
                                session_id=self.session.id if hasattr(self.session, "id") else None,
                            ),
                        )
                        logger.info(f"Stored explicit memory: {content[:50]}...")
                    except Exception as e:
                        logger.warning(f"Failed to store memory: {e}")

    async def _auto_activate_skills(self, content: str) -> None:
        """
        Automatically activate skills mentioned in the LLM's response.

        Scans the response for skill names and trigger keywords. If a skill
        is mentioned but not yet active, loads its full instructions for the
        next turn.
        """
        if not self.skills:
            return

        content_lower = content.lower()

        # Check all registered skills
        for skill_name, skill_meta in self.skills.skills.items():
            # Skip if already active
            if self.skills.is_active(skill_name):
                continue

            # Check if skill name or any trigger appears in response
            should_activate = False

            # Check skill name
            if skill_name.lower() in content_lower:
                should_activate = True

            # Check triggers
            for trigger in skill_meta.triggers:
                if trigger.lower() in content_lower:
                    should_activate = True
                    break

            # Activate skill if matched
            if should_activate:
                try:
                    await self.skills.activate(skill_name)
                    logger.info(f"Auto-activated skill: {skill_name}")
                except Exception as e:
                    logger.warning(f"Failed to auto-activate skill {skill_name}: {e}")

    async def _handle_tool_call(self, tool_call: ToolCall, *, ui: UI) -> ToolResult:
        """Process a single tool call through the event system."""

        # 1. Emit tool_call event (guardrails hook here)
        event_result = await self.events.emit("tool_call", tool_call, ui=ui)

        if event_result.blocked:
            return ToolResult(
                call_id=tool_call.id,
                error=f"Blocked: {event_result.reason}",
                is_error=True,
            )

        # 2. Execute the tool
        handler = self._tool_handlers.get(tool_call.name)
        if handler is None:
            return ToolResult(
                call_id=tool_call.id,
                error=f"Unknown tool: {tool_call.name}",
                is_error=True,
            )

        try:
            output = await handler(**tool_call.args)
            result = ToolResult(call_id=tool_call.id, output=str(output))
        except Exception as e:
            logger.error(f"Tool {tool_call.name} failed: {e}")
            result = ToolResult(
                call_id=tool_call.id,
                error=str(e),
                is_error=True,
            )

        # 3. Emit tool_result event (output filtering hook)
        post_event = await self.events.emit("tool_result", result, ui=ui)
        if post_event.data is not None:
            result = post_event.data

        return result

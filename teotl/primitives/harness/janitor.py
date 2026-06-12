"""Context compaction via turn-based janitor.

Prevents context bloat by extracting key decisions to DECISION_LOG.md
and enabling context resets while preserving important information.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """A key decision made by the agent."""

    turn: int
    timestamp: datetime
    decision: str
    context: str | None = None


class ContextJanitor:
    """Manages context compaction via turn-based decision logging.

    Prevents context bloat by:
    1. Tracking turn count
    2. Extracting key decisions from agent responses
    3. Every N turns: append to DECISION_LOG.md and signal context reset

    Usage:
        janitor = ContextJanitor(
            agent_id="coding-assistant",
            compact_every=10  # Compact every 10 turns
        )

        # After each agent turn
        await janitor.after_turn(agent_response)

        # Check if context should be reset
        if janitor.should_reset_context():
            # Reset agent context, reload from artifacts
            agent.reset_context(preserve_artifacts=True)
            janitor.reset_turn_count()
    """

    def __init__(
        self,
        agent_id: str,
        workspace_dir: Path | None = None,
        compact_every: int = 10,
        decision_extractor: Callable[[str], str | None] | None = None,
    ):
        """Initialize context janitor.

        Args:
            agent_id: Agent identifier
            workspace_dir: Optional workspace directory (defaults to ~/.forge/agents/{agent_id})
            compact_every: Compact context every N turns (default: 10)
            decision_extractor: Optional custom function to extract decisions from text
        """
        self.agent_id = agent_id
        self.compact_every = compact_every
        self.turn_count = 0
        self.decision_buffer: list[Decision] = []

        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path.home() / ".forge" / "agents" / agent_id

        self.decision_log_path = self.workspace_dir / "DECISION_LOG.md"

        # Use custom extractor or default
        self._extract_decision_fn = decision_extractor or self._default_extract_decision

        # Memory integration (set by Agent during initialization)
        self._memory = None
        self.max_context_tokens = 10000  # Default, overridden by Agent
        self._estimated_tokens = 0

        # Ensure workspace directory exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize decision log if it doesn't exist
        if not self.decision_log_path.exists():
            self._init_decision_log()

    def _init_decision_log(self) -> None:
        """Initialize DECISION_LOG.md file."""
        content = f"""# Decision Log

Agent: {self.agent_id}
Created: {datetime.now().isoformat()}

This log tracks key decisions made by the agent across turns.
Context is compacted every {self.compact_every} turns to keep the agent focused.

---

"""
        self.decision_log_path.write_text(content)

    async def after_turn(self, agent_response: str, context_snapshot: str | None = None) -> None:
        """Process agent response after a turn (async).

        Args:
            agent_response: The agent's text response
            context_snapshot: Optional full context for token estimation
        """
        self.turn_count += 1

        # Update context size estimate
        if context_snapshot:
            # Rough estimation: 1 token ≈ 4 characters
            self._estimated_tokens = len(context_snapshot) // 4
        else:
            # Accumulate from response
            self._estimated_tokens += len(agent_response) // 4

        # Extract decision
        decision_text = self._extract_decision_fn(agent_response)

        if decision_text:
            decision = Decision(
                turn=self.turn_count,
                timestamp=datetime.now(),
                decision=decision_text,
            )
            self.decision_buffer.append(decision)

            # Store decision as memory if memory system available (await)
            if self._memory:
                await self._store_decision_as_memory(decision)

        # Check if we should compact
        if self.should_compact():
            self.compact()

    def _default_extract_decision(self, text: str) -> str | None:
        """Default decision extraction logic.

        Looks for lines containing decision markers like:
        - "decided to"
        - "because"
        - "chose to"
        - "changed"
        - "fixed"
        - "added"
        - "removed"
        - "refactored"

        Args:
            text: Agent response text

        Returns:
            Extracted decision or None
        """
        decision_markers = [
            "decided to",
            "because",
            "chose to",
            "changed",
            "fixed",
            "added",
            "removed",
            "refactored",
            "updated",
            "implemented",
            "committed",
        ]

        for line in text.split("\n"):
            line_lower = line.lower().strip()

            # Skip empty lines
            if not line_lower:
                continue

            # Check for decision markers
            for marker in decision_markers:
                if marker in line_lower:
                    # Return the original line (preserving case)
                    return line.strip()

        return None

    async def _store_decision_as_memory(self, decision: Decision) -> None:
        """Store a decision as a memory (async).

        Args:
            decision: Decision to store
        """
        if not self._memory:
            return

        try:
            # Import here to avoid circular dependency
            from teotl.core.types import MemoryMeta

            # Create memory metadata
            meta = MemoryMeta(
                source="janitor",
                importance=7,  # High importance for decisions
                tags=["decision", f"turn_{decision.turn}"],
                session_id=None,
            )

            # Store as memory (await properly)
            await self._memory.remember(decision.decision, meta)

            logger.debug(f"Stored decision as memory: {decision.decision[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to store decision as memory: {e}")

    def should_compact(self) -> bool:
        """Check if context should be compacted now.

        Compaction is triggered by:
        1. Turn count threshold (every N turns)
        2. Token size threshold (context too large)
        """
        # Compact by turns
        if self.turn_count % self.compact_every == 0:
            return True

        # Compact by size
        if self._estimated_tokens > self.max_context_tokens:
            logger.info(
                f"Context size threshold reached: {self._estimated_tokens} > {self.max_context_tokens} tokens"
            )
            return True

        return False

    def should_reset_context(self) -> bool:
        """Alias for should_compact() - more semantic for context reset."""
        return self.should_compact()

    def compact(self) -> None:
        """Compact context by logging decisions and signaling reset."""
        if not self.decision_buffer:
            # No decisions to log, but still compact
            return

        # Append decisions to DECISION_LOG.md
        with open(self.decision_log_path, "a") as f:
            start_turn = self.turn_count - self.compact_every + 1
            end_turn = self.turn_count

            f.write(f"\n## Turns {start_turn}-{end_turn}\n\n")
            f.write(f"Compacted: {datetime.now().isoformat()}\n\n")

            for decision in self.decision_buffer:
                timestamp_str = decision.timestamp.strftime("%H:%M:%S")
                f.write(f"**Turn {decision.turn}** ({timestamp_str}): {decision.decision}\n\n")

            f.write("---\n\n")

        # Clear decision buffer
        self.decision_buffer = []

    def reset_turn_count(self) -> None:
        """Reset turn count after context has been reset.

        Call this after you've actually reset the agent's context.
        """
        # Note: We don't reset turn_count to 0, we keep it incrementing
        # This helps track absolute progress across context resets
        pass

    def get_turn_count(self) -> int:
        """Get current turn count."""
        return self.turn_count

    def get_pending_decisions(self) -> list[Decision]:
        """Get decisions waiting to be logged."""
        return self.decision_buffer.copy()

    def force_compact(self) -> None:
        """Force compaction regardless of turn count."""
        self.compact()

    def read_decision_log(self) -> str:
        """Read the full decision log.

        Returns:
            Content of DECISION_LOG.md
        """
        if not self.decision_log_path.exists():
            return ""

        return self.decision_log_path.read_text()

    def clear_decision_log(self) -> None:
        """Clear the decision log (creates new empty log)."""
        self.decision_log_path.unlink(missing_ok=True)
        self._init_decision_log()

    def archive_decision_log(self, suffix: str | None = None) -> Path:
        """Archive current decision log to timestamped file.

        Args:
            suffix: Optional suffix for archive filename

        Returns:
            Path to archived log file
        """
        if not self.decision_log_path.exists():
            raise FileNotFoundError("No decision log to archive")

        if suffix:
            archive_name = f"DECISION_LOG_{suffix}.md"
        else:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            archive_name = f"DECISION_LOG_{timestamp}.md"

        archive_path = self.workspace_dir / archive_name
        archive_path.write_text(self.decision_log_path.read_text())

        return archive_path

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ContextJanitor(agent_id='{self.agent_id}', "
            f"turn={self.turn_count}, "
            f"pending_decisions={len(self.decision_buffer)})"
        )

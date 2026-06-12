"""Advanced Context Janitor with LLM-powered decision extraction.

Phase 4 enhancement of the basic ContextJanitor:
- LLM-powered decision extraction (smarter than keyword matching)
- Context size tracking and limits
- Smart compaction (preserve important context, discard noise)
- Integration with supervisor cycles

The janitor prevents context bloat by:
1. Tracking context size across turns
2. Extracting key decisions using LLM (not just keywords)
3. Compacting context when size exceeds thresholds
4. Preserving important information while discarding noise
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from teotl.core.agent import Agent
from teotl.core.provider import Provider
from teotl.primitives.harness.janitor import ContextJanitor, Decision

logger = logging.getLogger(__name__)


@dataclass
class ContextMetrics:
    """Metrics about context usage."""

    turn_count: int
    estimated_tokens: int
    decisions_extracted: int
    compactions_performed: int
    last_compaction_turn: int | None = None

    @property
    def turns_since_compaction(self) -> int:
        """Turns since last compaction."""
        if self.last_compaction_turn is None:
            return self.turn_count
        return self.turn_count - self.last_compaction_turn

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "turn_count": self.turn_count,
            "estimated_tokens": self.estimated_tokens,
            "decisions_extracted": self.decisions_extracted,
            "compactions_performed": self.compactions_performed,
            "last_compaction_turn": self.last_compaction_turn,
            "turns_since_compaction": self.turns_since_compaction,
        }


class AdvancedContextJanitor(ContextJanitor):
    """Enhanced context janitor with LLM-powered decision extraction.

    Extends the basic ContextJanitor with:
    - LLM-powered decision extraction
    - Context size tracking
    - Smart compaction strategies
    - Integration with supervisor cycles

    Usage:
        janitor = AdvancedContextJanitor(
            agent_id="coding-assistant",
            provider=AnthropicProvider(model="claude-3-haiku-20240307"),
            compact_every=10,
            max_context_tokens=10000
        )

        # After each turn
        await janitor.after_turn_async(
            agent_response=response.text,
            context_snapshot=full_context  # Optional
        )

        # Check if compaction recommended
        if janitor.should_compact():
            await janitor.compact_smart()
    """

    def __init__(
        self,
        agent_id: str,
        provider: Provider | None = None,
        workspace_dir: Path | None = None,
        compact_every: int = 10,
        max_context_tokens: int = 10000,
        use_llm_extraction: bool = True,
    ):
        """Initialize advanced janitor.

        Args:
            agent_id: Agent identifier
            provider: Provider for LLM-powered extraction (cheap model like Haiku)
            workspace_dir: Workspace directory
            compact_every: Compact every N turns
            max_context_tokens: Max context size before forced compaction
            use_llm_extraction: Use LLM for decision extraction (vs keywords)
        """
        # Initialize base janitor
        super().__init__(
            agent_id=agent_id,
            workspace_dir=workspace_dir,
            compact_every=compact_every,
        )

        self.provider = provider
        self.max_context_tokens = max_context_tokens
        self.use_llm_extraction = use_llm_extraction

        # Context metrics
        self.metrics = ContextMetrics(
            turn_count=0,
            estimated_tokens=0,
            decisions_extracted=0,
            compactions_performed=0,
        )

        # Create extraction agent if provider given
        self.extraction_agent = None
        if provider and use_llm_extraction:
            self.extraction_agent = Agent(
                provider=provider,
                instructions=self._extraction_instructions(),
                session_dir=self.workspace_dir / "sessions" / "janitor",
            )
            logger.info(f"AdvancedContextJanitor using LLM extraction: {provider.model}")
        else:
            logger.info("AdvancedContextJanitor using keyword extraction")

    def _extraction_instructions(self) -> str:
        """Instructions for LLM-based decision extraction."""
        return """You are a decision extraction assistant.

Your job is to extract the key technical decisions from agent responses.

## What to Extract

Focus on:
- **Decisions made**: "I decided to...", "I chose to..."
- **Changes made**: "I changed X to Y", "I refactored..."
- **Bugs fixed**: "Fixed the bug in...", "Corrected the error..."
- **Why decisions were made**: "because", "to improve", "since"

## What to Ignore

Skip:
- Tool output (test results, file contents, diffs)
- Process descriptions ("I'm reading...", "Now I'll...")
- Confirmations ("Done", "Complete")
- Noise and debugging details

## Output Format

Extract 1-3 key decisions per response.

Each decision should be:
- One sentence
- Technical (specific file, function, or action)
- Include the "why" if mentioned

Examples:

INPUT:
"I read utils.py and found the parse_config function is missing type hints. I decided to add type hints because it will improve code quality and help catch bugs. I changed the signature from `def parse_config(data)` to `def parse_config(data: dict[str, Any]) -> Config`. Tests pass."

OUTPUT:
- Added type hints to parse_config() in utils.py to improve code quality and catch bugs

INPUT:
"I'm now reading the file... The file contains... I'll edit it... Done! Changed the null check."

OUTPUT:
- Fixed null check in error handling

Respond with ONLY the extracted decisions, one per line starting with "-".
If no key decisions, respond with "No key decisions."
"""

    async def after_turn_async(
        self,
        agent_response: str,
        context_snapshot: str | None = None,
    ) -> None:
        """Process turn with async LLM extraction.

        Args:
            agent_response: Agent's text response
            context_snapshot: Optional full context snapshot for size estimation
        """
        self.turn_count += 1
        self.metrics.turn_count = self.turn_count

        # Estimate context size
        if context_snapshot:
            # Rough estimation: 1 token ≈ 4 characters
            self.metrics.estimated_tokens = len(context_snapshot) // 4
        else:
            # Accumulate from response
            self.metrics.estimated_tokens += len(agent_response) // 4

        # Extract decisions
        if self.use_llm_extraction and self.extraction_agent:
            decisions_text = await self._extract_decisions_llm(agent_response)
        else:
            # Fall back to keyword extraction
            decisions_text = self._extract_decision(agent_response)

        # Parse and store decisions
        if decisions_text and decisions_text != "No key decisions.":
            for line in decisions_text.split("\n"):
                line = line.strip()
                if line and (line.startswith("-") or line.startswith("*")):
                    decision_text = line.lstrip("-*").strip()
                    decision = Decision(
                        turn=self.turn_count,
                        timestamp=datetime.now(),
                        decision=decision_text,
                    )
                    self.decision_buffer.append(decision)
                    self.metrics.decisions_extracted += 1

        # Check if compaction needed
        if self.should_compact() or self._context_too_large():
            await self.compact_smart()

    async def _extract_decisions_llm(self, agent_response: str) -> str | None:
        """Extract decisions using LLM.

        Args:
            agent_response: Agent response text

        Returns:
            Extracted decisions or None
        """
        if not self.extraction_agent:
            return None

        prompt = f"""Extract key technical decisions from this agent response:

{agent_response}

Respond with extracted decisions, one per line starting with "-".
"""

        try:
            response = await self.extraction_agent.run(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"LLM decision extraction failed: {e}")
            # Fall back to keyword extraction
            return self._extract_decision(agent_response)

    def _context_too_large(self) -> bool:
        """Check if context exceeds size limit.

        Returns:
            True if context should be compacted due to size
        """
        return self.metrics.estimated_tokens > self.max_context_tokens

    async def compact_smart(self) -> dict:
        """Smart compaction that preserves important context.

        Returns:
            Compaction metrics
        """
        logger.info(
            f"Smart compaction at turn {self.turn_count} (~{self.metrics.estimated_tokens} tokens)"
        )

        # Log decisions
        decisions_logged = len(self.decision_buffer)
        self.compact()  # Use base compact to log decisions

        # Update metrics
        self.metrics.compactions_performed += 1
        self.metrics.last_compaction_turn = self.turn_count

        # Reset context size estimate (after compaction)
        # Keep only recent context (last 2000 tokens worth)
        self.metrics.estimated_tokens = 2000

        compaction_metrics = {
            "turn": self.turn_count,
            "decisions_logged": decisions_logged,
            "tokens_before": self.metrics.estimated_tokens + (decisions_logged * 100),
            "tokens_after": self.metrics.estimated_tokens,
            "compaction_number": self.metrics.compactions_performed,
        }

        logger.info(f"Compaction complete: {compaction_metrics}")

        return compaction_metrics

    def get_metrics(self) -> ContextMetrics:
        """Get current context metrics.

        Returns:
            ContextMetrics
        """
        return self.metrics

    def should_compact_by_size(self) -> bool:
        """Check if compaction recommended by size.

        Returns:
            True if context size exceeds threshold
        """
        return self._context_too_large()

    def should_compact(self) -> bool:
        """Override to include size-based compaction.

        Returns:
            True if compaction recommended (by turns or size)
        """
        # Compact by turns
        if super().should_compact():
            return True

        # Compact by size
        if self.should_compact_by_size():
            logger.info(
                f"Compaction recommended by size: "
                f"{self.metrics.estimated_tokens} > {self.max_context_tokens}"
            )
            return True

        return False

    def reset_context(self) -> None:
        """Reset context tracking (call after actual context reset).

        This should be called after the agent's conversation context
        has been cleared and artifacts reloaded.
        """
        logger.info("Context reset acknowledged")

        # Don't reset turn count (tracks absolute progress)
        # Just reset size estimate
        self.metrics.estimated_tokens = 0

    def get_compaction_summary(self) -> str:
        """Get human-readable compaction summary.

        Returns:
            Summary string
        """
        return (
            f"Context Janitor Status:\n"
            f"  Turns: {self.metrics.turn_count}\n"
            f"  Estimated tokens: {self.metrics.estimated_tokens}\n"
            f"  Decisions extracted: {self.metrics.decisions_extracted}\n"
            f"  Compactions: {self.metrics.compactions_performed}\n"
            f"  Turns since compaction: {self.metrics.turns_since_compaction}\n"
            f"  Next compaction: {'now!' if self.should_compact() else f'in {self.compact_every - self.metrics.turns_since_compaction} turns'}"
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AdvancedContextJanitor("
            f"agent_id='{self.agent_id}', "
            f"turn={self.turn_count}, "
            f"tokens~{self.metrics.estimated_tokens}, "
            f"llm_extraction={self.use_llm_extraction})"
        )

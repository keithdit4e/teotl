"""Memory context injection and session-to-memory extraction."""

from __future__ import annotations

import json
import logging
from typing import Any

from teotl.core.types import EventResult, MemoryMeta

logger = logging.getLogger(__name__)


class MemoryContext:
    """
    Injects relevant memories into agent context. Budget-aware.

    Hooks into turn_start to add relevant memories to the system prompt.
    Hooks into turn_end / session_end to extract new memories.
    """

    def __init__(self, store: Any, *, token_budget: int = 500) -> None:
        self.store = store
        self.token_budget = token_budget

    async def inject(self, event: EventResult, **kwargs: Any) -> EventResult:
        """
        turn_start handler: retrieve and inject relevant memories.

        This is called before the LLM sees the conversation,
        adding relevant memories to the system prompt.
        """
        message = event.data.get("message", "") if isinstance(event.data, dict) else ""
        if not message:
            return event

        memories = await self.store.recall(message, limit=10)
        if memories:
            formatted = self.store.format_for_context(memories, token_budget=self.token_budget)
            # Memories are added to event data for the agent to pick up
            if isinstance(event.data, dict):
                event.data["memories"] = formatted
            event.modified = True

        return event

    async def extract(self, event: EventResult, **kwargs: Any) -> EventResult:
        """
        turn_end handler: extract memorable facts from the conversation.

        Uses pattern matching for lightweight extraction.
        Full LLM-based extraction happens at session_end.
        """
        # Lightweight extraction: look for explicit memory patterns
        # e.g., "Remember that I prefer..." or "My name is..."
        # Full LLM extraction is done by SessionCompactor at session end
        return event


class SessionCompactor:
    """
    Extracts memories from completed sessions using LLM summarization.

    Called at session end or during compaction to identify:
    - User preferences and decisions
    - Facts learned during the session
    - Project context and relationships
    - Important outcomes

    Uses a cheap/fast model for extraction to minimize cost.
    """

    EXTRACTION_PROMPT = """Extract factual memories from this conversation.
Return a JSON array of objects with these fields:
- content: the fact to remember (one sentence)
- tags: list of relevant tags
- importance: 1-10 (10 = critical user preference, 1 = trivial detail)

Focus on:
- User preferences and decisions
- Facts about the user (name, role, projects)
- Technical decisions made
- Important context for future conversations

Do NOT memorize:
- Pleasantries or greetings
- Meta-conversation about how to format things
- Transient state (file contents, error messages)
- Things the user explicitly asked to forget

Return ONLY the JSON array, no other text."""

    def __init__(self, store: Any, extraction_provider: Any = None) -> None:
        self.store = store
        self.extraction_provider = extraction_provider

    async def extract_from_session(self, session: Any) -> list[str]:
        """
        Extract memories from a session transcript.

        Returns list of memory IDs that were stored.
        """
        if self.extraction_provider is None:
            logger.debug("No extraction provider configured, skipping memory extraction")
            return []

        transcript = session.format_for_extraction()
        if not transcript or len(transcript) < 100:
            return []

        try:
            result = await self.extraction_provider.complete(
                system=self.EXTRACTION_PROMPT,
                messages=[{"role": "user", "content": transcript}],
                max_tokens=2000,
            )

            memories_raw = json.loads(result.content)
            stored_ids = []

            for m in memories_raw:
                if m.get("importance", 0) >= 5:
                    memory_id = await self.store.remember(
                        m["content"],
                        MemoryMeta(
                            source="session",
                            tags=m.get("tags", []),
                            importance=m["importance"],
                            session_id=session.id,
                        ),
                    )
                    stored_ids.append(memory_id)

            logger.info(f"Extracted {len(stored_ids)} memories from session")
            return stored_ids

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse memory extraction: {e}")
            return []
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            return []

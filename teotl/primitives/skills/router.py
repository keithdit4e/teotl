"""Skill router: matches user messages to relevant skills."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from teotl.core.types import SkillMeta


class SkillRouter:
    """
    Routes user messages to relevant skills based on descriptions and triggers.

    The primary routing is done by the LLM itself — it reads skill descriptions
    and decides which ones are relevant. This router provides an optional
    pre-filter for cases where programmatic matching is preferred.
    """

    @staticmethod
    def match(message: str, skills: dict[str, SkillMeta]) -> list[str]:
        """
        Find skills that might be relevant to a message.

        Uses trigger keywords for fast matching. This is a hint —
        the LLM makes the final decision.
        """
        message_lower = message.lower()
        matches = []

        for name, meta in skills.items():
            # Check trigger keywords
            for trigger in meta.triggers:
                if trigger.lower() in message_lower:
                    matches.append(name)
                    break

        return matches

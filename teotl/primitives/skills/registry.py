"""Skill registry: discovery, loading, and progressive disclosure."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from teotl.core.paths import teotl_home
from teotl.primitives.skills.loader import SkillLoader

if TYPE_CHECKING:
    from teotl.core.types import SkillFull, SkillMeta

logger = logging.getLogger(__name__)


class SkillNotFound(Exception):
    """Raised when a requested skill is not in the registry."""

    pass


class SkillRegistry:
    """
    Progressive disclosure for integrations and capabilities.

    Cost model:
    - 10 skills registered = ~500 tokens (descriptions only, always in context)
    - 1 skill activated = ~500-2000 tokens (full SKILL.md, temporary)
    - MCP equivalent = ~30,000+ tokens (all tool schemas, permanent)

    Usage:
        registry = SkillRegistry(["filesystem", "git", "gmail"])
        descriptions = registry.get_descriptions()  # Always in context
        instructions = await registry.activate("gmail")  # On-demand
    """

    def __init__(self, enabled: list[str] | None = None) -> None:
        self.skills: dict[str, SkillMeta] = {}
        self.active: dict[str, SkillFull] = {}
        self._discover(enabled)

    def _discover(self, enabled: list[str] | None) -> None:
        """Scan skill directories for SKILL.md files."""
        search_paths = [
            teotl_home() / "skills",  # User skills (~/.teotl/skills, or legacy ~/.forge/skills)
            Path(__file__).parent.parent.parent / "skills",  # Bundled skills (teotl/skills/)
        ]

        # Also check TEOTL_SKILLS_PATH (and legacy FORGE_SKILLS_PATH) env vars
        import os

        for env_var in ("TEOTL_SKILLS_PATH", "FORGE_SKILLS_PATH"):
            extra_paths = os.environ.get(env_var, "")
            if extra_paths:
                for p in extra_paths.split(":"):
                    search_paths.append(Path(p))

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for skill_dir in sorted(search_path.iterdir()):
                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    continue

                try:
                    meta = SkillLoader.parse_frontmatter(skill_file)

                    # If enabled list is provided, only register those skills
                    if enabled is not None and meta.name not in enabled:
                        continue

                    self.skills[meta.name] = meta
                    logger.debug(f"Discovered skill: {meta.name}")

                except Exception as e:
                    logger.warning(f"Failed to load skill from {skill_dir}: {e}")

        logger.info(f"Registered {len(self.skills)} skills: {list(self.skills.keys())}")

    def get_descriptions(self) -> str:
        """
        Returns compact descriptions for ALL registered skills.

        This is always in context. ~50 tokens per skill.
        The LLM reads these to decide which skills are relevant.
        """
        if not self.skills:
            return ""

        lines = ["## Available capabilities"]
        for name, meta in self.skills.items():
            active_marker = " [active]" if name in self.active else ""
            lines.append(f"- **{name}**: {meta.description}{active_marker}")
        lines.append("")
        lines.append(
            "Before doing a task one of these covers, call the `load_skill` tool with its "
            "name to load its full instructions."
        )
        return "\n".join(lines)

    async def activate(self, skill_name: str) -> str:
        """
        Load full SKILL.md into context.

        Called when the agent decides it needs a skill based on the description.
        Returns the full instructions for injection into the conversation.
        """
        if skill_name in self.active:
            return self._render(self.active[skill_name])

        meta = self.skills.get(skill_name)
        if not meta:
            raise SkillNotFound(
                f"Skill '{skill_name}' not found. Available: {list(self.skills.keys())}"
            )

        skill_file = meta.path / "SKILL.md"
        full = SkillLoader.parse_full(skill_file)
        self.active[skill_name] = full

        logger.info(f"Activated skill: {skill_name} ({len(full.instructions)} chars)")
        return self._render(full)

    @staticmethod
    def _render(skill: SkillFull) -> str:
        """Skill instructions plus its directory, so bundled scripts and files can be found."""
        return f"Skill directory: {skill.meta.path}\n\n{skill.instructions}"

    def deactivate(self, skill_name: str) -> None:
        """Remove skill instructions from active context."""
        if skill_name in self.active:
            del self.active[skill_name]
            logger.debug(f"Deactivated skill: {skill_name}")

    def deactivate_all(self) -> None:
        """Deactivate all skills (e.g., during compaction)."""
        self.active.clear()

    def is_active(self, skill_name: str) -> bool:
        """Check if a skill is currently loaded."""
        return skill_name in self.active

    def get_active_instructions(self) -> str:
        """Get combined instructions for all active skills."""
        if not self.active:
            return ""

        parts = []
        for name, skill in self.active.items():
            parts.append(f"## Skill: {name}\n\n{self._render(skill)}")
        return "\n\n---\n\n".join(parts)

    @property
    def registered_count(self) -> int:
        return len(self.skills)

    @property
    def active_count(self) -> int:
        return len(self.active)

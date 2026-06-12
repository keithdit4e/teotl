"""SKILL.md parser. Handles frontmatter and body extraction."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import yaml

from teotl.core.types import SkillFull, SkillMeta

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Parses SKILL.md files with YAML frontmatter.

    Format:
        ---
        name: gmail
        description: "Send, read, and search email"
        version: 1.0.0
        auth: oauth2
        triggers:
          - email
          - mail
        ---

        # Gmail Integration
        ## Commands
        ...
    """

    @staticmethod
    def parse_frontmatter(path: Path) -> SkillMeta:
        """
        Parse only the frontmatter from a SKILL.md file.

        This is cheap (~50 tokens for the description) and is loaded
        at startup for all enabled skills.
        """
        content = path.read_text()
        fm = SkillLoader._extract_frontmatter(content)

        return SkillMeta(
            name=fm.get("name", path.parent.name),
            description=fm.get("description", ""),
            path=path.parent,
            version=fm.get("version", "0.1.0"),
            auth=fm.get("auth", "none"),
            triggers=fm.get("triggers", []),
        )

    @staticmethod
    def parse_full(path: Path) -> SkillFull:
        """
        Parse the complete SKILL.md file including body.

        This is loaded on-demand when the agent decides it needs the skill.
        Typically 500-2000 tokens.
        """
        content = path.read_text()
        fm = SkillLoader._extract_frontmatter(content)
        body = SkillLoader._extract_body(content)

        meta = SkillMeta(
            name=fm.get("name", path.parent.name),
            description=fm.get("description", ""),
            path=path.parent,
            version=fm.get("version", "0.1.0"),
            auth=fm.get("auth", "none"),
            triggers=fm.get("triggers", []),
        )

        return SkillFull(meta=meta, instructions=body)

    @staticmethod
    def _extract_frontmatter(content: str) -> dict:
        """Extract YAML frontmatter from markdown content."""
        if not content.startswith("---"):
            return {}

        # Find closing ---
        end = content.find("---", 3)
        if end == -1:
            return {}

        fm_text = content[3:end].strip()
        try:
            return yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse SKILL.md frontmatter: {e}")
            return {}

    @staticmethod
    def _extract_body(content: str) -> str:
        """Extract the body (everything after frontmatter)."""
        if not content.startswith("---"):
            return content

        end = content.find("---", 3)
        if end == -1:
            return content

        return content[end + 3 :].strip()

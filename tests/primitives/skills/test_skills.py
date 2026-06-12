"""Tests for the skills system."""

import pytest

from teotl.primitives.skills.loader import SkillLoader
from teotl.primitives.skills.registry import SkillNotFound, SkillRegistry


@pytest.fixture
def skill_dir(tmp_path):
    """Create a temporary skill directory with test skills."""
    # Create test skill
    test_skill = tmp_path / "test_skill"
    test_skill.mkdir()
    (test_skill / "SKILL.md").write_text("""---
name: test_skill
description: "A test skill for unit tests"
version: 1.0.0
auth: none
triggers:
  - test
  - testing
---

# Test Skill

## Commands

### Run tests
```bash
pytest
```

### Run specific test
```bash
pytest <path> -k <pattern>
```
""")

    # Create another skill
    other_skill = tmp_path / "other_skill"
    other_skill.mkdir()
    (other_skill / "SKILL.md").write_text("""---
name: other_skill
description: "Another test skill"
---

# Other Skill

This is the body of the other skill.
""")

    return tmp_path


class TestSkillLoader:
    def test_parse_frontmatter(self, skill_dir):
        meta = SkillLoader.parse_frontmatter(skill_dir / "test_skill" / "SKILL.md")
        assert meta.name == "test_skill"
        assert meta.description == "A test skill for unit tests"
        assert meta.version == "1.0.0"
        assert meta.auth == "none"
        assert "test" in meta.triggers

    def test_parse_full(self, skill_dir):
        full = SkillLoader.parse_full(skill_dir / "test_skill" / "SKILL.md")
        assert full.meta.name == "test_skill"
        assert "pytest" in full.instructions
        assert "## Commands" in full.instructions

    def test_parse_no_frontmatter(self, tmp_path):
        skill = tmp_path / "plain"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# Just a plain markdown file\n\nNo frontmatter here.")
        meta = SkillLoader.parse_frontmatter(skill / "SKILL.md")
        assert meta.name == "plain"  # Falls back to directory name

    def test_parse_frontmatter_defaults(self, skill_dir):
        meta = SkillLoader.parse_frontmatter(skill_dir / "other_skill" / "SKILL.md")
        assert meta.auth == "none"  # Default
        assert meta.version == "0.1.0"  # Default
        assert meta.triggers == []  # Default


class TestSkillRegistry:
    def test_discover_skills(self, skill_dir, monkeypatch):
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))
        registry = SkillRegistry()
        assert registry.registered_count >= 2
        assert "test_skill" in registry.skills
        assert "other_skill" in registry.skills

    def test_discover_with_filter(self, skill_dir, monkeypatch):
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))
        registry = SkillRegistry(enabled=["test_skill"])
        assert "test_skill" in registry.skills
        assert "other_skill" not in registry.skills

    def test_get_descriptions(self, skill_dir, monkeypatch):
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))
        registry = SkillRegistry()
        desc = registry.get_descriptions()
        assert "test_skill" in desc
        assert "A test skill for unit tests" in desc
        assert "Available capabilities" in desc

    def test_get_descriptions_empty(self):
        registry = SkillRegistry(enabled=[])
        assert registry.get_descriptions() == ""

    async def test_activate(self, skill_dir, monkeypatch):
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))
        registry = SkillRegistry()
        instructions = await registry.activate("test_skill")
        assert "pytest" in instructions
        assert registry.is_active("test_skill")

    async def test_activate_not_found(self, skill_dir, monkeypatch):
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))
        registry = SkillRegistry()
        with pytest.raises(SkillNotFound):
            await registry.activate("nonexistent")

    async def test_deactivate(self, skill_dir, monkeypatch):
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))
        registry = SkillRegistry()
        await registry.activate("test_skill")
        assert registry.is_active("test_skill")

        registry.deactivate("test_skill")
        assert not registry.is_active("test_skill")

    async def test_activate_idempotent(self, skill_dir, monkeypatch):
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))
        registry = SkillRegistry()
        inst1 = await registry.activate("test_skill")
        inst2 = await registry.activate("test_skill")
        assert inst1 == inst2  # Returns cached version

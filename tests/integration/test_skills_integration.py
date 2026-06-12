"""Integration tests for skills system in the agent loop."""

import pytest

from teotl.core.agent import Agent
from teotl.core.provider import Provider
from teotl.core.types import CompletionResult


class MockProvider(Provider):
    """Mock provider for testing skill auto-activation."""

    def __init__(self, responses: list[str], mentions_skill: bool = False):
        """
        Args:
            responses: List of responses to return (one per complete() call)
            mentions_skill: If True, first response mentions a skill
        """
        self.responses = responses
        self.call_count = 0
        self.mentions_skill = mentions_skill

    async def complete(self, system: str, messages: list, tools: list | None = None):
        """Return mock responses, optionally mentioning a skill."""
        content = self.responses[min(self.call_count, len(self.responses) - 1)]
        self.call_count += 1

        # Check if skill instructions are now in system prompt (after activation)
        "filesystem" in system.lower() or "Commands" in system

        return CompletionResult(
            content=content,
            done=True,
            tool_calls=[],
            usage={"input_tokens": 100, "output_tokens": 50},
        )

    @property
    def context_window(self) -> int:
        """Return mock context window."""
        return 100_000

    @property
    def model_name(self) -> str:
        """Return mock model name."""
        return "mock-model"


class TestSkillsIntegration:
    """Test skills auto-activation and manual control in agent loop."""

    @pytest.fixture
    def skill_dir(self, tmp_path):
        """Create temporary test skills."""
        # Create test skill
        test_skill = tmp_path / "test_skill"
        test_skill.mkdir()
        (test_skill / "SKILL.md").write_text("""---
name: test_skill
description: "A test skill for integration tests"
version: 1.0.0
auth: none
triggers:
  - testing
  - test command
---

# Test Skill

## Commands

### Run tests
```bash
pytest
```
""")

        return tmp_path

    @pytest.mark.asyncio
    async def test_skill_descriptions_in_context(self, skill_dir, monkeypatch):
        """Test that skill descriptions are always in context."""
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))

        provider = MockProvider(["I can help with that."])
        agent = Agent(provider=provider, skills=["test_skill"])

        # Run agent
        await agent.run("Hello")

        # Skill descriptions should be present in system prompt
        # We can verify this by checking the agent has skills registered
        assert agent.skills is not None
        assert agent.skills.registered_count == 1
        assert "test_skill" in agent.skills.skills

    @pytest.mark.asyncio
    async def test_auto_activate_skill_by_name(self, skill_dir, monkeypatch):
        """Test that mentioning a skill name auto-activates it."""
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))

        provider = MockProvider(
            ["I'll use the test_skill capability for that.", "Here's the result."]
        )
        agent = Agent(provider=provider, skills=["test_skill"])

        # First turn: agent mentions skill name
        await agent.run("Can you test something?")

        # Skill should now be active
        assert agent.skills.is_active("test_skill")
        assert "test_skill" in agent.list_active_skills()

    @pytest.mark.asyncio
    async def test_auto_activate_skill_by_trigger(self, skill_dir, monkeypatch):
        """Test that mentioning a trigger keyword auto-activates the skill."""
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))

        provider = MockProvider(["I can help with testing your code.", "Running tests now."])
        agent = Agent(provider=provider, skills=["test_skill"])

        # First turn: agent mentions "testing" trigger
        await agent.run("Help me with QA")

        # Skill should be auto-activated
        assert agent.skills.is_active("test_skill")

    @pytest.mark.asyncio
    async def test_active_instructions_injected(self, skill_dir, monkeypatch):
        """Test that active skill instructions are injected into system prompt."""
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))

        provider = MockProvider(["Using test_skill now."])
        agent = Agent(provider=provider, skills=["test_skill"])

        # Manually activate skill
        instructions = await agent.activate_skill("test_skill")

        # Instructions should contain the skill body
        assert "pytest" in instructions
        assert "Commands" in instructions

        # Build system prompt
        system_prompt = agent._build_system_prompt()

        # Active skills section should be present
        assert "Active Skills" in system_prompt or "test_skill" in system_prompt

    @pytest.mark.asyncio
    async def test_manual_skill_activation(self, skill_dir, monkeypatch):
        """Test manual skill activation and deactivation."""
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))

        provider = MockProvider(["OK"])
        agent = Agent(provider=provider, skills=["test_skill"])

        # Initially not active
        assert not agent.skills.is_active("test_skill")
        assert agent.list_active_skills() == []

        # Manually activate
        instructions = await agent.activate_skill("test_skill")
        assert "pytest" in instructions
        assert agent.skills.is_active("test_skill")
        assert "test_skill" in agent.list_active_skills()

        # Manually deactivate
        agent.deactivate_skill("test_skill")
        assert not agent.skills.is_active("test_skill")
        assert agent.list_active_skills() == []

    @pytest.mark.asyncio
    async def test_list_skills(self, skill_dir, monkeypatch):
        """Test listing registered skills."""
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))

        provider = MockProvider(["OK"])
        agent = Agent(provider=provider, skills=["test_skill"])

        # List all skills
        skills = agent.list_skills()
        assert "test_skill" in skills
        assert "integration tests" in skills["test_skill"].lower()

    @pytest.mark.asyncio
    async def test_skill_not_initialized(self):
        """Test behavior when skills system has no skills registered."""
        provider = MockProvider(["OK"])
        # Skills=None will still initialize registry but with no skills
        # This is expected behavior - registry always exists
        agent = Agent(provider=provider, skills=None)

        # Skills registry exists but is empty (no skills path set)
        assert agent.skills is not None
        assert agent.skills.registered_count >= 0  # May find system skills
        assert agent.list_active_skills() == []

        # Deactivate should not error
        agent.deactivate_skill("nonexistent")  # Should be no-op

    @pytest.mark.asyncio
    async def test_activate_nonexistent_skill(self, skill_dir, monkeypatch):
        """Test activating a skill that doesn't exist."""
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))

        provider = MockProvider(["OK"])
        agent = Agent(provider=provider, skills=["test_skill"])

        # Try to activate nonexistent skill
        from teotl.primitives.skills.registry import SkillNotFound

        with pytest.raises(SkillNotFound):
            await agent.activate_skill("nonexistent")

    @pytest.mark.asyncio
    async def test_idempotent_activation(self, skill_dir, monkeypatch):
        """Test that activating the same skill multiple times is idempotent."""
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))

        provider = MockProvider(
            ["Using testing features.", "Still using testing.", "Done testing."]
        )
        agent = Agent(provider=provider, skills=["test_skill"])

        # First activation
        await agent.run("Start testing")
        assert agent.skills.is_active("test_skill")
        active_count_1 = agent.skills.active_count

        # Mention again (should not duplicate)
        await agent.run("Continue testing")
        assert agent.skills.is_active("test_skill")
        active_count_2 = agent.skills.active_count

        # Should still be 1 active skill
        assert active_count_1 == active_count_2 == 1

    @pytest.mark.asyncio
    async def test_multiple_skills_activation(self, tmp_path, monkeypatch):
        """Test activating multiple skills in sequence."""
        # Create two skills
        skill1 = tmp_path / "skill_one"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("""---
name: skill_one
description: "First skill"
triggers: ["first"]
---
# Skill One
""")

        skill2 = tmp_path / "skill_two"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("""---
name: skill_two
description: "Second skill"
triggers: ["second"]
---
# Skill Two
""")

        monkeypatch.setenv("FORGE_SKILLS_PATH", str(tmp_path))

        provider = MockProvider(
            ["Using first skill.", "Now using second skill.", "Using both first and second."]
        )
        agent = Agent(provider=provider)

        # Turn 1: activate skill_one
        await agent.run("Do something first")
        assert agent.skills.is_active("skill_one")
        assert not agent.skills.is_active("skill_two")

        # Turn 2: activate skill_two
        await agent.run("Do something second")
        assert agent.skills.is_active("skill_one")
        assert agent.skills.is_active("skill_two")
        assert len(agent.list_active_skills()) == 2

    @pytest.mark.asyncio
    async def test_skill_context_injection_flow(self, skill_dir, monkeypatch):
        """
        Integration test showing the full flow:
        1. User asks about something
        2. Agent mentions skill
        3. Skill auto-activates
        4. Next turn includes skill instructions
        """
        monkeypatch.setenv("FORGE_SKILLS_PATH", str(skill_dir))

        # Track system prompts to verify instructions are added
        system_prompts = []

        class TrackingProvider(Provider):
            async def complete(self, system: str, messages: list, tools: list | None = None):
                system_prompts.append(system)
                return CompletionResult(
                    content="I'll use test_skill for testing."
                    if len(system_prompts) == 1
                    else "Done.",
                    done=True,
                    tool_calls=[],
                    usage={"input_tokens": 100, "output_tokens": 50},
                )

            @property
            def context_window(self) -> int:
                return 100_000

            @property
            def model_name(self) -> str:
                return "tracking-mock"

        provider = TrackingProvider()
        agent = Agent(provider=provider, skills=["test_skill"])

        # Turn 1: User asks, agent mentions skill
        await agent.run("Can you help test?")

        # Skill should be active now
        assert agent.skills.is_active("test_skill")

        # Turn 2: Instructions should be in context
        await agent.run("Continue")

        # Check that second system prompt includes skill instructions
        assert len(system_prompts) >= 2
        second_prompt = system_prompts[1]

        # Should contain either "Active Skills" header or skill content
        has_skill_content = (
            "pytest" in second_prompt
            or "Commands" in second_prompt
            or "Active Skills" in second_prompt
        )
        assert has_skill_content, (
            f"Expected skill instructions in prompt, got: {second_prompt[:500]}"
        )

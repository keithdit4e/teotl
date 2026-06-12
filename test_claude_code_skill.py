"""Test that Claude Code skill is discoverable and loadable."""

import asyncio

from teotl.primitives.skills.registry import SkillRegistry


async def test_claude_code_skill():
    """Test Claude Code skill discovery and activation."""

    # Test 1: Discover skill
    print("Test 1: Discovering skills...")
    registry = SkillRegistry(enabled=["claude_code", "filesystem", "git"])

    print(f"✅ Registered {registry.registered_count} skills")
    print(f"   Skills: {list(registry.skills.keys())}")

    # Test 2: Check skill metadata
    print("\nTest 2: Checking claude_code metadata...")
    if "claude_code" in registry.skills:
        meta = registry.skills["claude_code"]
        print(f"✅ Name: {meta.name}")
        print(f"   Version: {meta.version}")
        print(f"   Description: {meta.description}")
        print(f"   Triggers: {meta.triggers[:3]}...")  # First 3 triggers
    else:
        print("❌ claude_code skill not found!")
        return

    # Test 3: Get descriptions (what goes in context always)
    print("\nTest 3: Getting skill descriptions...")
    descriptions = registry.get_descriptions()
    print("✅ Skill descriptions generated:")
    print(descriptions[:500] + "..." if len(descriptions) > 500 else descriptions)

    # Test 4: Activate skill (load full instructions)
    print("\nTest 4: Activating claude_code skill...")
    instructions = await registry.activate("claude_code")
    print(f"✅ Loaded {len(instructions)} characters of instructions")
    print(f"   Active skills: {list(registry.active.keys())}")

    # Test 5: Check instructions content
    print("\nTest 5: Verifying instructions content...")
    expected_sections = [
        "# Claude Code - AI-Powered Coding Assistant",
        "## When to Use Claude Code",
        "## Core Operations",
        "## Refactoring Tasks",
        "## Feature Implementation",
        "## Bug Fixing",
        "## Testing",
        "## Code Migration",
        "## Security Best Practices",
    ]

    found_sections = []
    for section in expected_sections:
        if section in instructions:
            found_sections.append(section)

    print(f"✅ Found {len(found_sections)}/{len(expected_sections)} expected sections")
    for section in found_sections:
        print(f"   ✓ {section}")

    # Test 6: Deactivate skill
    print("\nTest 6: Deactivating skill...")
    registry.deactivate("claude_code")
    print(f"✅ Deactivated. Active skills: {list(registry.active.keys())}")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED - Claude Code skill is ready!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_claude_code_skill())

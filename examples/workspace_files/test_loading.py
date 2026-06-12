"""
Test script to verify workspace files are loaded correctly.

This script demonstrates that workspace files (PERSONALITY.md, USER.md,
INSTRUCTIONS.md, SKILLS.md) are actually loaded at runtime.

Usage:
    python examples/workspace_files/test_loading.py
"""

import asyncio
from pathlib import Path

from teotl.daemon.executor import load_workspace_files


def test_load_workspace_files():
    """Test that workspace files are loaded correctly."""
    print("=" * 60)
    print("Testing Workspace File Loading")
    print("=" * 60)
    print()

    # Test with a workspace that has files
    workspace_dir = Path("~/.forge/agents/").expanduser()

    # Find first agent workspace
    if not workspace_dir.exists():
        print(f"❌ No workspace directory found at {workspace_dir}")
        print("   Run 'forge onboard' first to create an agent")
        return False

    # Find first agent subdirectory
    agent_dirs = [d for d in workspace_dir.iterdir() if d.is_dir()]

    if not agent_dirs:
        print(f"❌ No agent directories found in {workspace_dir}")
        print("   Run 'forge onboard' first to create an agent")
        return False

    test_dir = agent_dirs[0]
    print(f"Testing workspace: {test_dir}")
    print()

    # Load workspace files
    content = load_workspace_files(test_dir)

    if not content:
        print(f"❌ No workspace files loaded from {test_dir}")
        print()
        print("Expected files:")
        print("  - PERSONALITY.md")
        print("  - USER.md")
        print("  - INSTRUCTIONS.md")
        print("  - SKILLS.md")
        print()

        # Check which files exist
        print("Checking for files:")
        for filename in ["PERSONALITY.md", "USER.md", "INSTRUCTIONS.md", "SKILLS.md"]:
            file_path = test_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  ✓ {filename} exists ({size} bytes)")
            else:
                print(f"  ✗ {filename} missing")

        return False

    # Success!
    print("✅ Loaded workspace files successfully!")
    print()

    # Count sections (separated by ---)
    sections = [s.strip() for s in content.split("---") if s.strip()]
    print(f"Sections loaded: {len(sections)}")
    print(f"Total characters: {len(content)}")
    print()

    # Show preview of each section
    print("=" * 60)
    print("Preview of Loaded Content:")
    print("=" * 60)
    print()

    for i, section in enumerate(sections, 1):
        # Get first line (usually a heading)
        first_line = section.split("\n")[0].strip()
        preview = section[:150].replace("\n", " ")

        print(f"Section {i}: {first_line}")
        print(f"  Preview: {preview}...")
        print()

    print("=" * 60)
    print("Full Combined Content (first 500 chars):")
    print("=" * 60)
    print(content[:500])
    print("...")
    print()

    return True


async def test_agent_executor_factory():
    """Test that AgentExecutorFactory loads workspace files."""
    print("=" * 60)
    print("Testing AgentExecutorFactory")
    print("=" * 60)
    print()

    # Find workspace
    workspace_dir = Path("~/.forge/agents/").expanduser()
    agent_dirs = [d for d in workspace_dir.iterdir() if d.is_dir()]

    if not agent_dirs:
        print("❌ No agent directories found")
        return False

    test_dir = agent_dirs[0]
    print(f"Using workspace: {test_dir}")
    print()

    # Create factory (need to mock provider or use real one)
    # For testing, we'll just verify the _build_instructions method

    try:
        # This would normally require a real API key
        # provider = AnthropicProvider()

        # Instead, let's directly test the instruction building
        from unittest.mock import Mock

        from teotl.daemon.executor import AgentExecutorFactory

        mock_provider = Mock()

        factory = AgentExecutorFactory(
            provider=mock_provider,
            workspace_dir=test_dir,
        )

        # Test instruction building
        config_instructions = "This is from config.yaml"
        combined = factory._build_instructions(config_instructions)

        if "This is from config.yaml" in combined:
            print("❌ Using config instructions (workspace files not loaded)")
            print(f"   Content: {combined[:100]}")
            return False

        if len(combined) < 100:
            print("❌ Instructions too short (workspace files may not be loaded)")
            print(f"   Length: {len(combined)} characters")
            return False

        print("✅ AgentExecutorFactory loaded workspace files!")
        print(f"   Instructions length: {len(combined)} characters")
        print()
        print("   Preview (first 200 chars):")
        print(f"   {combined[:200]}...")
        print()

        return True

    except Exception as e:
        print(f"❌ Error testing factory: {e}")
        return False


def main():
    """Run all tests."""
    print()
    print("🧪 Workspace Files Loading Test Suite")
    print()

    # Test 1: Direct file loading
    test1 = test_load_workspace_files()
    print()

    # Test 2: Factory integration
    test2 = asyncio.run(test_agent_executor_factory())
    print()

    # Summary
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Test 1 (load_workspace_files): {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Test 2 (AgentExecutorFactory):  {'✅ PASS' if test2 else '❌ FAIL'}")
    print()

    if test1 and test2:
        print("🎉 All tests passed! Workspace files are loading correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

    print()


if __name__ == "__main__":
    main()

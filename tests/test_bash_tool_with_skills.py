"""Test bash tool integration with skills system.

This test verifies that:
1. Bash tool is auto-registered when skills are enabled
2. Bash commands execute correctly
3. Skills can use bash commands through the tool
"""

import asyncio
import tempfile
from pathlib import Path

from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider


async def test_bash_tool_registration():
    """Test that bash tool is registered when skills are enabled."""
    print("\n=== Test 1: Bash Tool Registration ===")

    agent = Agent(
        provider=AnthropicProvider(),
        skills=["filesystem", "git"],
    )

    # Check bash tool is registered
    bash_tool_names = [tool.name for tool in agent._tools if tool.name == "bash"]
    assert bash_tool_names, "Bash tool should be auto-registered"
    print("✅ Bash tool registered successfully")

    # Check bash handler exists
    assert "bash" in agent._tool_handlers, "Bash handler should be registered"
    print("✅ Bash handler found")


async def test_simple_bash_command():
    """Test executing a simple bash command."""
    print("\n=== Test 2: Simple Bash Command ===")

    agent = Agent(
        provider=AnthropicProvider(),
        skills=["filesystem"],
    )

    # Get bash handler
    bash_handler = agent._tool_handlers.get("bash")
    assert bash_handler, "Bash handler should be available"

    # Execute simple command
    result = await bash_handler(command="echo 'Hello from bash tool'")
    print(f"Result: {result}")

    assert "Hello from bash tool" in result, "Output should contain echo text"
    print("✅ Simple bash command executed successfully")


async def test_filesystem_skill_commands():
    """Test filesystem skill commands through bash tool."""
    print("\n=== Test 3: Filesystem Skill Commands ===")

    agent = Agent(
        provider=AnthropicProvider(),
        skills=["filesystem"],
    )

    bash_handler = agent._tool_handlers.get("bash")

    # Test 1: Create a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"

        # Create file
        result = await bash_handler(command=f"echo 'test content' > {test_file}")
        print(f"Create file result: {result[:200]}")

        # List files
        result = await bash_handler(command=f"ls -la {tmpdir}")
        print(f"List files result: {result[:200]}")
        assert "test.txt" in result, "Created file should appear in listing"

        # Read file
        result = await bash_handler(command=f"cat {test_file}")
        print(f"Read file result: {result[:200]}")
        assert "test content" in result, "File should contain our content"

    print("✅ Filesystem skill commands work correctly")


async def test_git_skill_commands():
    """Test git skill commands through bash tool."""
    print("\n=== Test 4: Git Skill Commands ===")

    agent = Agent(
        provider=AnthropicProvider(),
        skills=["git"],
    )

    bash_handler = agent._tool_handlers.get("bash")

    # Test git commands (in current directory)
    result = await bash_handler(command="git --version")
    print(f"Git version result: {result[:200]}")
    assert "git version" in result or "Error" in result, "Should get git version or error"

    result = await bash_handler(command="git status")
    print(f"Git status result: {result[:200]}")
    # Either we're in a git repo or we get "not a git repository" error
    assert "On branch" in result or "not a git repository" in result or "Error" in result, (
        "Should get git status or appropriate error"
    )

    print("✅ Git skill commands execute correctly")


async def test_dangerous_command_blocked():
    """Test that dangerous commands are blocked."""
    print("\n=== Test 5: Dangerous Command Protection ===")

    agent = Agent(
        provider=AnthropicProvider(),
        skills=["filesystem"],
    )

    bash_handler = agent._tool_handlers.get("bash")

    # Try dangerous command
    result = await bash_handler(command="rm -rf /")
    print(f"Dangerous command result: {result[:200]}")

    assert "Error" in result or "blocked" in result.lower(), "Dangerous command should be blocked"

    print("✅ Dangerous commands are properly blocked")


async def test_timeout_enforcement():
    """Test that timeout is enforced."""
    print("\n=== Test 6: Timeout Enforcement ===")

    agent = Agent(
        provider=AnthropicProvider(),
        skills=["filesystem"],
    )

    bash_handler = agent._tool_handlers.get("bash")

    # Command that takes too long (with short timeout)
    result = await bash_handler(command="sleep 5", timeout=1)
    print(f"Timeout result: {result[:200]}")

    assert "timeout" in result.lower() or "timed out" in result.lower(), (
        "Long-running command should timeout"
    )

    print("✅ Timeout is enforced correctly")


async def test_skills_activation_with_bash():
    """Test that skills are activated and can use bash."""
    print("\n=== Test 7: Skills Activation with Bash ===")

    agent = Agent(
        provider=AnthropicProvider(),
        skills=["filesystem", "git", "web"],
    )

    # Verify skills are registered
    assert agent.skills, "Skills registry should be initialized"
    print(f"✅ Skills registered: {list(agent.skills.skills.keys())}")

    # Verify bash tool is available
    assert "bash" in agent._tool_handlers, "Bash tool should be available"
    print("✅ Bash tool is available for skill execution")

    # Get skill descriptions (always in context)
    descriptions = agent.skills.get_descriptions()
    print(f"Skill descriptions (first 200 chars): {descriptions[:200]}...")
    assert "filesystem" in descriptions.lower(), "Filesystem skill should be described"
    assert "git" in descriptions.lower(), "Git skill should be described"

    print("✅ Skills system integrated with bash tool")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Bash Tool Integration with Skills")
    print("=" * 60)

    tests = [
        test_bash_tool_registration,
        test_simple_bash_command,
        test_filesystem_skill_commands,
        test_git_skill_commands,
        test_dangerous_command_blocked,
        test_timeout_enforcement,
        test_skills_activation_with_bash,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

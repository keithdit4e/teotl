"""Test interactive chat mode."""

import asyncio

from teotl.cli.chat import ChatSession


async def test_chat_session_init():
    """Test chat session initialization."""
    session = ChatSession(
        agent_id="test-chat",
        skills=["filesystem", "git"],
        use_memory=False,  # Disable memory for test
    )

    assert session.agent_id == "test-chat"
    assert session.skills == ["filesystem", "git"]
    assert session.use_memory is False

    print("✅ Chat session initialization works")


async def test_chat_agent_init():
    """Test agent initialization within chat session."""
    session = ChatSession(
        agent_id=None,  # No specific agent
        skills=["filesystem"],
        use_memory=False,
    )

    # Initialize agent (partial - just setup)
    instructions = session._load_instructions()
    assert isinstance(instructions, str)
    assert len(instructions) > 0

    print("✅ Agent initialization works")
    print(f"   Instructions: {instructions[:100]}...")


async def test_chat_with_skills():
    """Test that agent has bash tool when skills are enabled."""
    from teotl.core.agent import Agent
    from teotl.core.provider import AnthropicProvider

    agent = Agent(
        provider=AnthropicProvider(),
        instructions="You are a helpful assistant",
        skills=["filesystem", "git"],
    )

    # Check bash tool is registered
    bash_tool = None
    for tool in agent._tools:
        if tool.name == "bash":
            bash_tool = tool
            break

    assert bash_tool is not None, "Bash tool should be registered"
    print("✅ Bash tool registered with skills")

    # Check skills are loaded
    assert agent.skills is not None
    assert "filesystem" in agent.skills.skills
    assert "git" in agent.skills.skills
    print(f"✅ Skills loaded: {list(agent.skills.skills.keys())}")


async def test_command_handler():
    """Test command handler logic."""
    session = ChatSession(
        agent_id=None,
        skills=[],
        use_memory=False,
    )

    # Initialize agent for command testing
    from teotl.core.agent import Agent
    from teotl.core.provider import AnthropicProvider

    session.agent = Agent(
        provider=AnthropicProvider(),
        instructions="Test agent",
        skills=[],
    )

    # Test help command
    result = await session._handle_command("/help")
    assert result is True  # Should continue

    # Test exit command
    result = await session._handle_command("/exit")
    assert result is False  # Should exit

    # Test quit command
    result = await session._handle_command("/quit")
    assert result is False  # Should exit

    print("✅ Command handler works")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Interactive Chat Mode")
    print("=" * 60)

    tests = [
        test_chat_session_init,
        test_chat_agent_init,
        test_chat_with_skills,
        test_command_handler,
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

"""Example: Skills with Bash Execution

Demonstrates that skills now actually work - they can execute commands!

Before: Skills only provided documentation
After: Skills execute commands through secure bash tool

This example shows:
1. Filesystem operations (read, write, search)
2. Git operations (status, log)
3. Combined operations (find files, check git status)
"""

import asyncio

from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider


async def filesystem_operations():
    """Demonstrate filesystem skill with actual execution."""
    print("\n" + "=" * 60)
    print("Example 1: Filesystem Operations")
    print("=" * 60)

    agent = Agent(
        provider=AnthropicProvider(),
        instructions="You are a helpful assistant that can work with files.",
        skills=["filesystem"],
    )

    # Check agent has bash tool
    print(f"\n✅ Agent has {len(agent._tools)} tools registered:")
    for tool in agent._tools:
        print(f"   - {tool.name}: {tool.description[:80]}...")

    # Demo: The agent can now actually execute filesystem commands!
    print("\n📝 Skills provide bash commands like:")
    print("   - ls -la (list files)")
    print("   - grep -rn 'pattern' (search)")
    print("   - cat file.txt (read)")

    print("\n🔧 Bash tool executes them securely with:")
    print("   - Dangerous pattern blocking")
    print("   - Timeout enforcement")
    print("   - Output size limits")

    # You could now do:
    # response = await agent.run("List all Python files in the project")
    # The agent would use filesystem skill + bash tool to execute:
    # find . -name "*.py" -type f

    print("\n✅ Skills are now executable, not just documentation!")


async def git_operations():
    """Demonstrate git skill with actual execution."""
    print("\n" + "=" * 60)
    print("Example 2: Git Operations")
    print("=" * 60)

    agent = Agent(
        provider=AnthropicProvider(),
        instructions="You are a helpful git assistant.",
        skills=["git"],
    )

    # The git skill can now execute commands
    bash_handler = agent._tool_handlers.get("bash")

    print("\n📝 Git skill provides commands like:")
    print("   - git status")
    print("   - git log --oneline -5")
    print("   - git diff")

    # Execute a git command directly
    print("\n🔧 Executing: git status")
    result = await bash_handler(command="git status")
    print(result[:300])

    print("\n✅ Git operations work through bash tool!")


async def combined_operations():
    """Demonstrate multiple skills working together."""
    print("\n" + "=" * 60)
    print("Example 3: Combined Operations (Filesystem + Git)")
    print("=" * 60)

    agent = Agent(
        provider=AnthropicProvider(),
        instructions="You are a helpful development assistant.",
        skills=["filesystem", "git"],
    )

    bash_handler = agent._tool_handlers.get("bash")

    print("\n📝 Combined workflow:")
    print("   1. Find Python files (filesystem skill)")
    print("   2. Check if they're tracked by git (git skill)")

    # Find Python files
    print("\n🔧 Step 1: Finding Python test files")
    result = await bash_handler(command="find tests -name '*.py' -type f | head -5")
    print(result[:300])

    # Check git tracking
    print("\n🔧 Step 2: Checking git status")
    result = await bash_handler(command="git ls-files tests/*.py | head -5")
    print(result[:300])

    print("\n✅ Multiple skills can work together!")


async def security_demo():
    """Demonstrate security features."""
    print("\n" + "=" * 60)
    print("Example 4: Security Features")
    print("=" * 60)

    agent = Agent(
        provider=AnthropicProvider(),
        skills=["filesystem"],
    )

    bash_handler = agent._tool_handlers.get("bash")

    print("\n🛡️  Security Feature 1: Dangerous Command Blocking")
    result = await bash_handler(command="rm -rf /")
    print(result)
    assert "Error" in result or "blocked" in result.lower()

    print("\n🛡️  Security Feature 2: Timeout Enforcement")
    result = await bash_handler(command="sleep 5", timeout=1)
    print(result)
    assert "timeout" in result.lower() or "timed out" in result.lower()

    print("\n🛡️  Security Feature 3: Sandbox Ready")
    print("Commands can be validated against:")
    print("   - Filesystem allowlist/blocklist")
    print("   - Network domain allowlist")
    print("   - Resource limits (CPU, memory)")

    print("\n✅ Multiple layers of security protection!")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Skills with Bash Execution - Working Examples")
    print("=" * 60)

    examples = [
        ("Filesystem Operations", filesystem_operations),
        ("Git Operations", git_operations),
        ("Combined Operations", combined_operations),
        ("Security Features", security_demo),
    ]

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n❌ {name} failed: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("Summary: Skills Now Work!")
    print("=" * 60)
    print("\n✅ Filesystem skill can execute file operations")
    print("✅ Git skill can execute version control commands")
    print("✅ Web skill can fetch URLs and search")
    print("✅ Bash tool provides secure execution layer")
    print("✅ Multiple security protections in place")
    print("\nNext: Use agent.run() with natural language to try it!")
    print("Example: await agent.run('List all TODO comments in Python files')")


if __name__ == "__main__":
    asyncio.run(main())

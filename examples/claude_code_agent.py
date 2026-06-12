"""Example: Using Claude Code skill with Forge agent.

This demonstrates how to create an agent that can use Claude Code
for complex coding tasks like refactoring, features, and bug fixes.

Usage:
    python3 examples/claude_code_agent.py
"""

import asyncio

from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider


async def main():
    """Run coding agent with Claude Code skill."""

    # Create agent with Claude Code skill
    Agent(
        provider=AnthropicProvider(model="claude-haiku-4"),
        instructions="""You are an expert software development assistant.

When you encounter coding tasks (refactoring, features, bug fixes, tests),
use your claude_code skill to delegate to the Claude Code CLI.

Always:
1. Review changes with git diff before committing
2. Run tests to verify functionality
3. Commit with clear, descriptive messages
4. Report what you did and why
""",
        skills=["filesystem", "git", "claude_code"],  # ← Claude Code enabled
    )

    # Example 1: Refactoring task
    print("=" * 70)
    print("Example 1: Refactoring with Claude Code")
    print("=" * 70)
    print()

    refactoring_task = """Refactor the authentication module to use JWT tokens.

Current state: Using session-based authentication
Requirements:
- Implement JWT token generation with RS256
- Add token refresh mechanism (7-day expiry)
- Update all protected routes to validate JWT
- Include comprehensive tests
- Update API documentation

Project directory: ~/projects/my-app
"""

    print(f"Task: {refactoring_task[:100]}...")
    print()
    print("Agent will:")
    print("  1. Detect 'refactor' keyword → activate claude_code skill")
    print("  2. Read Claude Code instructions (19K chars)")
    print("  3. Execute: claude-code 'Refactor auth to use JWT...'")
    print("  4. Review changes: git diff")
    print("  5. Run tests: npm test")
    print("  6. Commit if successful")
    print()

    # In production, you would:
    # response = await agent.run(refactoring_task)
    # print(response.text)

    # Example 2: Bug fix task
    print("=" * 70)
    print("Example 2: Bug Fix with Claude Code")
    print("=" * 70)
    print()

    bug_fix_task = """Fix the race condition in the payment processing flow.

Error: Users getting charged twice when clicking submit rapidly
File: src/api/payments.py, line 234
Stack trace:
  File "payments.py", line 234, in process_payment
    charge = create_charge(amount)
  Exception: Duplicate charge detected

Requirements:
- Add idempotency key to prevent duplicates
- Add request locking mechanism
- Write test to reproduce race condition
- Write test to verify fix
"""

    print(f"Task: {bug_fix_task[:100]}...")
    print()
    print("Agent will:")
    print("  1. Detect 'fix' keyword → activate claude_code skill")
    print("  2. Read bug fixing section of instructions")
    print("  3. Execute: claude-code 'Fix race condition in payments...'")
    print("  4. Verify fix: Run new tests")
    print("  5. Commit with 'fix:' prefix")
    print()

    # Example 3: Feature implementation
    print("=" * 70)
    print("Example 3: Feature Implementation with Claude Code")
    print("=" * 70)
    print()

    feature_task = """Implement email verification for user signup.

Requirements:
- Generate verification token (UUID4)
- Store token with 1-hour expiry
- Send verification email with link
- Create /verify endpoint to check token
- Auto-login user after verification
- Add rate limiting (max 3 emails/hour)
- Include tests:
  * Token generation
  * Email sending
  * Verification flow
  * Expiry handling
  * Rate limiting
"""

    print(f"Task: {feature_task[:100]}...")
    print()
    print("Agent will:")
    print("  1. Detect 'implement' keyword → activate claude_code skill")
    print("  2. Read feature implementation section")
    print("  3. Execute: claude-code 'Implement email verification...'")
    print("  4. Verify: Run all new tests")
    print("  5. Commit with 'feat:' prefix")
    print()

    # Example 4: Test generation
    print("=" * 70)
    print("Example 4: Test Generation with Claude Code")
    print("=" * 70)
    print()

    test_task = """Write comprehensive tests for the UserService class.

File: src/services/UserService.ts

Test coverage needed:
- createUser: valid data, duplicate email, invalid email format
- updateUser: valid update, user not found, permission denied
- deleteUser: successful delete, user not found, cascade deletion
- getUserById: found, not found, malformed ID
- listUsers: pagination, filtering, sorting

Requirements:
- Use Jest framework
- Mock database calls
- Test edge cases
- Aim for 90% code coverage
"""

    print(f"Task: {test_task[:100]}...")
    print()
    print("Agent will:")
    print("  1. Detect 'write tests' keyword → activate claude_code skill")
    print("  2. Read testing section of instructions")
    print("  3. Execute: claude-code 'Write tests for UserService...'")
    print("  4. Run tests to verify they pass")
    print("  5. Check coverage: jest --coverage")
    print("  6. Commit with 'test:' prefix")
    print()

    # Example 5: Using in Planner-Worker pattern
    print("=" * 70)
    print("Example 5: Planner-Worker with Claude Code")
    print("=" * 70)
    print()

    print("For complex multi-step coding projects, use Planner-Worker:")
    print()
    print("1. PLANNER (Sonnet, expensive) creates detailed plan:")
    print("   'Migrate from REST to GraphQL'")
    print("   → Plan with 12 steps")
    print()
    print("2. WORKER (Haiku, cheap) executes each step:")
    print("   Step 1: Research current API endpoints")
    print("     → Worker executes directly")
    print()
    print("   Step 2: Design GraphQL schema")
    print("     → Worker executes directly")
    print()
    print("   Step 3: Implement GraphQL resolvers")
    print("     → Worker detects 'implement' keyword")
    print("     → Activates claude_code skill")
    print("     → Delegates to Claude Code")
    print("     ✅ Claude Code generates resolvers")
    print()
    print("   Step 4: Write resolver tests")
    print("     → Worker detects 'write tests' keyword")
    print("     → Delegates to Claude Code")
    print("     ✅ Claude Code generates tests")
    print()
    print("   Step 5: Migrate client code to use GraphQL")
    print("     → Worker detects 'migrate' keyword")
    print("     → Delegates to Claude Code")
    print("     ✅ Claude Code performs migration")
    print()
    print("   ... 7 more steps ...")
    print()
    print("Cost: Planner $0.10 + Worker $0.06 + Claude Code $0.08 = $0.24")
    print("vs Full Sonnet: 12 steps × $0.10 = $1.20")
    print("Savings: $0.96 (80% reduction) 💰")
    print()

    # Skill activation details
    print("=" * 70)
    print("How Skill Activation Works")
    print("=" * 70)
    print()
    print("When agent is created with skills=['claude_code']:")
    print()
    print("1. SkillRegistry discovers claude_code skill from:")
    print("   - skills/claude_code/SKILL.md")
    print("   - ~/.forge/skills/claude_code/SKILL.md")
    print("   - $FORGE_SKILLS_PATH/claude_code/SKILL.md")
    print()
    print("2. Agent receives skill DESCRIPTION in system prompt:")
    print("   '- claude_code: AI-powered coding assistant for refactoring, features, bug fixes'")
    print("   Cost: ~50 tokens (always in context)")
    print()
    print("3. When agent sees coding task with triggers:")
    print("   Triggers: refactor, implement, fix bug, write tests, migrate")
    print("   → Agent activates skill")
    print()
    print("4. Agent receives FULL INSTRUCTIONS:")
    print("   19,049 characters of comprehensive guidance")
    print("   Cost: ~2,000 tokens (loaded on-demand)")
    print()
    print("5. Agent uses instructions to execute:")
    print("   claude-code 'Detailed task description'")
    print()

    # Configuration example
    print("=" * 70)
    print("Configuration")
    print("=" * 70)
    print()
    print("config.yaml:")
    print("""
agent:
  agent_id: coding-assistant
  instructions: "You are an expert software development assistant"
  skills:
    - filesystem
    - git
    - claude_code  # ← Enable Claude Code skill

  memory:
    enabled: true

  harness:
    cost_tracking: true
    state: true

daemon:
  poll_interval: 30
""")
    print()
    print("Or use the wizard:")
    print("  $ python3 -m forge.cli.wizard")
    print("  Step 4: Select 'Claude_Code' in skills")
    print()

    print("=" * 70)
    print("✅ Claude Code skill ready to use!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

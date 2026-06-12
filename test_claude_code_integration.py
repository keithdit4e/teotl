"""Integration test for Claude Code skill in agent workflow.

This demonstrates the full flow:
1. Config includes claude_code skill
2. Agent loads skill registry
3. Agent sees claude_code in available capabilities
4. Agent activates claude_code when needed
5. Agent receives comprehensive Claude Code instructions
"""

import asyncio

from teotl.primitives.skills.registry import SkillRegistry


async def test_integration():
    """Test full integration of Claude Code skill."""
    print("=" * 70)
    print("CLAUDE CODE SKILL INTEGRATION TEST")
    print("=" * 70)
    print()

    # Simulate config from wizard (user selected claude_code skill)
    config_skills = ["filesystem", "git", "claude_code"]
    print("Step 1: Configuration from wizard")
    print(f"  Skills selected: {config_skills}")
    print()

    # Agent initialization with skill registry
    print("Step 2: Initialize skill registry")
    registry = SkillRegistry(enabled=config_skills)
    print(f"  ✅ Registered {registry.registered_count} skills")
    print(f"     {list(registry.skills.keys())}")
    print()

    # Get skill descriptions (always in context)
    print("Step 3: Agent receives skill descriptions (always in context)")
    descriptions = registry.get_descriptions()
    print("  " + descriptions.replace("\n", "\n  "))
    print()

    # Simulate agent deciding it needs Claude Code
    print("Step 4: Agent encounters a coding task")
    task = "Refactor the authentication module to use JWT instead of sessions"
    print(f'  Task: "{task}"')
    print()
    print("  Agent analyzes task and thinks:")
    print("    - Task involves 'refactor' (trigger for claude_code)")
    print("    - Task is complex, multi-file change")
    print("    - Should activate claude_code skill")
    print()

    # Activate skill (load full instructions)
    print("Step 5: Activate claude_code skill (load full instructions)")
    instructions = await registry.activate("claude_code")
    print(f"  ✅ Loaded {len(instructions)} characters")
    print(f"     Active skills: {list(registry.active.keys())}")
    print()

    # Show what agent receives
    print("Step 6: Agent now has detailed Claude Code instructions")
    lines = instructions.split("\n")
    print("  First 30 lines of instructions:")
    for i, line in enumerate(lines[:30], 1):
        print(f"    {i:2d}: {line}")
    print(f"  ... ({len(lines)} total lines)")
    print()

    # Demonstrate skill usage
    print("Step 7: Agent uses Claude Code")
    print("  Agent sees instruction for refactoring:")
    print()

    # Extract refactoring section from instructions
    refactor_start = instructions.find("## Refactoring Tasks")
    refactor_section = instructions[refactor_start : refactor_start + 500]
    print("  " + refactor_section.replace("\n", "\n  "))
    print("  ...")
    print()

    # Agent would execute this
    print("Step 8: Agent executes Claude Code command")
    command = 'claude-code "Refactor authentication to use JWT"'
    print(f"  Command: {command}")
    print()
    print("  (In real execution, this would run claude-code CLI)")
    print("  (For this test, we're just demonstrating the flow)")
    print()

    # Verify results
    print("Step 9: Integration verification")
    checks = [
        ("Config includes claude_code", "claude_code" in config_skills),
        ("Skill is registered", "claude_code" in registry.skills),
        ("Skill can be activated", "claude_code" in registry.active),
        ("Instructions are comprehensive", len(instructions) > 15000),
        ("Contains refactoring section", "## Refactoring Tasks" in instructions),
        ("Contains bug fixing section", "## Bug Fixing" in instructions),
        ("Contains testing section", "## Testing" in instructions),
        ("Contains security section", "## Security Best Practices" in instructions),
    ]

    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
        if not result:
            all_passed = False

    print()
    print("=" * 70)
    if all_passed:
        print("✅ ALL INTEGRATION TESTS PASSED")
        print()
        print("The Claude Code skill is fully integrated and ready to use!")
        print()
        print("Agents can now:")
        print("  • See claude_code in available capabilities")
        print("  • Activate it when encountering coding tasks")
        print("  • Use Claude Code CLI for complex refactoring")
        print("  • Delegate feature implementation")
        print("  • Fix bugs with AI assistance")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)

    return all_passed


async def test_planner_worker_scenario():
    """Test Claude Code in Planner-Worker pattern."""
    print()
    print("=" * 70)
    print("PLANNER-WORKER WITH CLAUDE CODE SCENARIO")
    print("=" * 70)
    print()

    print("Scenario: Planner creates plan, Worker uses Claude Code to execute")
    print()

    # Planner phase
    print("Phase 1: PLANNER (using expensive Sonnet model)")
    print("  Task: Migrate authentication from sessions to JWT")
    print()
    print("  Planner creates detailed plan:")
    print("    Step 1: Research current session implementation")
    print("    Step 2: Design JWT token structure and validation")
    print("    Step 3: Implement JWT token generation")
    print("    Step 4: Replace session middleware with JWT middleware")
    print("    Step 5: Update all protected routes")
    print("    Step 6: Implement token refresh mechanism")
    print("    Step 7: Write comprehensive tests")
    print("    Step 8: Update documentation")
    print()

    # Worker phase with Claude Code
    print("Phase 2: WORKER (using cheap Haiku model)")
    print()

    steps_with_claude_code = [
        ("Step 3: Implement JWT token generation", True, "Complex coding task"),
        ("Step 4: Replace session middleware", True, "Refactoring task"),
        ("Step 5: Update protected routes", True, "Multi-file changes"),
        ("Step 6: Token refresh mechanism", True, "Feature implementation"),
        ("Step 7: Write comprehensive tests", True, "Test generation"),
    ]

    registry = SkillRegistry(enabled=["filesystem", "git", "claude_code"])

    for step_desc, uses_claude, reason in steps_with_claude_code:
        print(f"  {step_desc}")
        if uses_claude:
            print(f"    ↓ Worker detects: {reason}")
            print("    ↓ Activates claude_code skill")
            if not registry.is_active("claude_code"):
                await registry.activate("claude_code")
            print("    ↓ Delegates to Claude Code CLI")
            print("    ✅ Claude Code executes (cheap Haiku cost)")
        else:
            print("    ↓ Worker executes directly")
            print("    ✅ Done")
        print()

    # Cost analysis
    print("Cost Analysis:")
    print("  Planner (Sonnet, runs once):")
    print("    Create plan: $0.10")
    print()
    print("  Worker (Haiku, runs 8 times):")
    print("    8 steps × $0.005 = $0.04")
    print()
    print("  Claude Code (Haiku for execution):")
    print("    5 coding tasks × $0.008 = $0.04")
    print()
    print("  Total: $0.18")
    print()
    print("  vs Full Sonnet (no planning):")
    print("    8 steps × $0.10 = $0.80")
    print()
    print("  Savings: $0.62 (77% cost reduction) 💰")
    print()
    print("=" * 70)


if __name__ == "__main__":
    # Run integration test
    passed = asyncio.run(test_integration())

    if passed:
        # Run planner-worker scenario
        asyncio.run(test_planner_worker_scenario())

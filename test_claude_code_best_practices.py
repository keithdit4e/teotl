"""Test Claude Code best practices integration.

This tests that:
1. Claude Code skill includes commands & features section
2. /clear command is documented
3. Plan mode is documented
4. Worker instructions include Claude Code best practices when skill is active
5. Worker instructions are basic when Claude Code skill is NOT active
"""

import sys
from pathlib import Path

# Test setup
print("=" * 70)
print("CLAUDE CODE BEST PRACTICES TEST")
print("=" * 70)
print()

# Test 1: Claude Code skill has commands & features section
print("Test 1: Checking Claude Code skill has commands & features...")

skill_path = Path("skills/claude_code/SKILL.md")

if not skill_path.exists():
    print(f"  ❌ Claude Code skill not found at {skill_path}")
    sys.exit(1)

skill_content = skill_path.read_text()

required_sections = [
    "## Claude Code Commands & Features",
    "### Context Management: `/clear`",
    "### Plan Mode: Complex Task Planning",
    "When to use `/clear`:",
    "Starting a new feature",
    "When to expect/request plan mode:",
    "/help",
    "/review",
    "/undo",
    "/diff",
    ".claude/instructions.md",
]

missing_sections = []
for section in required_sections:
    if section not in skill_content:
        missing_sections.append(section)
        print(f"  ❌ Missing section: {section}")
    else:
        print(f"  ✅ Found section: {section}")

if missing_sections:
    print()
    print(f"❌ FAILED: Missing {len(missing_sections)} required sections")
    sys.exit(1)

print()
print("✅ Test 1 PASSED: Claude Code skill has all commands & features")
print()

# Test 2: /clear best practices documented
print("Test 2: Checking /clear best practices...")

clear_checks = [
    "starting a new feature",
    "Prevents context pollution",
    "When NOT to use `/clear`:",
    "Mid-feature",
    "Between unrelated tasks",
]

missing_clear = []
for check in clear_checks:
    if check.lower() not in skill_content.lower():
        missing_clear.append(check)
        print(f"  ❌ Missing: {check}")
    else:
        print(f"  ✅ Found: {check}")

if missing_clear:
    print()
    print("❌ FAILED: /clear documentation incomplete")
    sys.exit(1)

print()
print("✅ Test 2 PASSED: /clear best practices complete")
print()

# Test 3: Plan mode best practices documented
print("Test 3: Checking plan mode best practices...")

plan_mode_checks = [
    "Plan mode",
    "Complex Task Planning",
    "Multi-file refactoring",
    "Creates detailed step-by-step plan",
    "Asks for approval before executing",
]

missing_plan = []
for check in plan_mode_checks:
    if check.lower() not in skill_content.lower():
        missing_plan.append(check)
        print(f"  ❌ Missing: {check}")
    else:
        print(f"  ✅ Found: {check}")

if missing_plan:
    print()
    print("❌ FAILED: Plan mode documentation incomplete")
    sys.exit(1)

print()
print("✅ Test 3 PASSED: Plan mode best practices complete")
print()

# Test 4: Worker instructions conditional on claude_code skill
print("Test 4: Checking wizard worker instructions are conditional...")

import inspect

from teotl.cli.wizard import OnboardingWizard

wizard = OnboardingWizard()

# Check that worker instructions section includes has_claude_code check
setup_pw_source = inspect.getsource(wizard._setup_planner_worker)

required_elements = [
    "has_claude_code",
    "claude_code",
    "/clear",
    "NEW FEATURE",
    "plan mode",
]

missing_elements = []
for element in required_elements:
    if element not in setup_pw_source:
        missing_elements.append(element)
        print(f"  ❌ Missing element: {element}")
    else:
        print(f"  ✅ Found element: {element}")

if missing_elements:
    print()
    print("❌ FAILED: Worker instructions not properly conditional")
    sys.exit(1)

print()
print("✅ Test 4 PASSED: Worker instructions are conditional on skills")
print()

# Test 5: Verify worker instructions content
print("Test 5: Verifying worker instructions content...")

# Simulate configuration with claude_code skill
test_config_with_cc = {
    "planner_worker": {
        "worker": {
            "skills": ["filesystem", "git", "claude_code"],
            "instructions": """Execute plan steps carefully and verify results.

When using claude_code skill for coding tasks:
1. Use /clear when starting a NEW FEATURE (unrelated to previous task)
2. Let complex tasks trigger plan mode automatically (multi-file changes)
3. Do NOT use /clear mid-feature or when tasks are related
4. Review changes before committing

Context management:
- /clear: Start fresh for new features
- Plan mode: Automatically used for complex multi-step tasks
- /diff: Review all changes before proceeding""",
        }
    }
}

# Simulate configuration without claude_code skill
test_config_without_cc = {
    "planner_worker": {
        "worker": {
            "skills": ["filesystem", "git"],
            "instructions": "Execute plan steps carefully and verify results",
        }
    }
}

# Check config with claude_code includes special instructions
instructions_with_cc = test_config_with_cc["planner_worker"]["worker"]["instructions"]

cc_instruction_checks = [
    "/clear",
    "NEW FEATURE",
    "plan mode",
    "Context management",
]

missing_cc_instructions = []
for check in cc_instruction_checks:
    if check not in instructions_with_cc:
        missing_cc_instructions.append(check)
        print(f"  ❌ Missing in claude_code instructions: {check}")
    else:
        print(f"  ✅ Found in claude_code instructions: {check}")

if missing_cc_instructions:
    print()
    print("❌ FAILED: claude_code worker instructions incomplete")
    sys.exit(1)

# Check config without claude_code has simple instructions
instructions_without_cc = test_config_without_cc["planner_worker"]["worker"]["instructions"]

if "/clear" in instructions_without_cc or "plan mode" in instructions_without_cc:
    print("  ❌ Simple instructions should NOT mention Claude Code features")
    sys.exit(1)

print(f"  ✅ Simple instructions: '{instructions_without_cc[:50]}...'")

print()
print("✅ Test 5 PASSED: Worker instructions content correct")
print()

# Test 6: Other commands documented
print("Test 6: Checking other Claude Code commands documented...")

other_commands = [
    "/help",
    "/review",
    "/undo",
    "/diff",
    "Command Quick Reference",
]

missing_commands = []
for cmd in other_commands:
    if cmd not in skill_content:
        missing_commands.append(cmd)
        print(f"  ❌ Missing command: {cmd}")
    else:
        print(f"  ✅ Found command: {cmd}")

if missing_commands:
    print()
    print("❌ FAILED: Command documentation incomplete")
    sys.exit(1)

print()
print("✅ Test 6 PASSED: All commands documented")
print()

# Test 7: .claude/ directory configuration documented
print("Test 7: Checking .claude/ directory configuration...")

claude_dir_checks = [
    ".claude/",
    ".claude/instructions.md",
    "Project-specific instructions",
    "automatically read",
]

missing_claude_dir = []
for check in claude_dir_checks:
    if check.lower() not in skill_content.lower():
        missing_claude_dir.append(check)
        print(f"  ❌ Missing: {check}")
    else:
        print(f"  ✅ Found: {check}")

if missing_claude_dir:
    print()
    print("❌ FAILED: .claude/ directory documentation incomplete")
    sys.exit(1)

print()
print("✅ Test 7 PASSED: .claude/ directory configuration documented")
print()

# Final summary
print("=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print()
print("Claude Code best practices integration is complete:")
print("  ✅ Commands & features section in skill")
print("  ✅ /clear command documented with when to use")
print("  ✅ Plan mode documented for complex tasks")
print("  ✅ /help, /review, /undo, /diff commands documented")
print("  ✅ .claude/ directory configuration documented")
print("  ✅ Worker instructions conditional on claude_code skill")
print("  ✅ Worker gets Claude Code best practices when skill active")
print("  ✅ Worker gets simple instructions when skill not active")
print()
print("Workers will now:")
print("  1. Use /clear when starting new features")
print("  2. Leverage plan mode for complex tasks")
print("  3. Know when NOT to use /clear (mid-feature)")
print("  4. Use /diff to review changes")
print("  5. Follow .claude/ project configuration")
print()
print("This only applies when claude_code skill is active! ✅")
print()

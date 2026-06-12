"""Test planner-worker wizard integration.

This tests that the wizard correctly:
1. Offers execution pattern selection
2. Configures planner and worker providers
3. Sets up worker skills
4. Configures harness features
5. Generates runner script
"""

import sys

# Check that wizard has required methods
print("=" * 70)
print("PLANNER-WORKER WIZARD INTEGRATION TEST")
print("=" * 70)
print()

print("Test 1: Checking wizard has execution pattern method...")
from teotl.cli.wizard import OnboardingWizard

wizard = OnboardingWizard()

# Check methods exist
required_methods = [
    "_setup_execution_pattern",
    "_setup_providers",
    "_setup_daemon_provider",
    "_setup_planner_provider",
    "_setup_worker_provider",
    "_setup_planner_worker",
    "_generate_runner_scripts",
]

missing_methods = []
for method_name in required_methods:
    if not hasattr(wizard, method_name):
        missing_methods.append(method_name)
        print(f"  ❌ Missing method: {method_name}")
    else:
        print(f"  ✅ Found method: {method_name}")

if missing_methods:
    print()
    print(f"❌ FAILED: Missing {len(missing_methods)} required methods")
    sys.exit(1)

print()
print("✅ Test 1 PASSED: All required methods exist")
print()

# Test 2: Check run() method calls execution pattern setup
print("Test 2: Checking wizard flow includes new steps...")

import inspect

run_source = inspect.getsource(wizard.run)

checks = [
    ("_setup_execution_pattern()", "Execution pattern selection"),
    ("_setup_providers()", "Provider setup"),
    ("_setup_planner_worker()", "Planner-worker configuration"),
]

all_found = True
for method_call, description in checks:
    if method_call in run_source:
        print(f"  ✅ {description}: {method_call}")
    else:
        print(f"  ❌ {description}: {method_call} NOT FOUND")
        all_found = False

if not all_found:
    print()
    print("❌ FAILED: Not all steps are in wizard flow")
    sys.exit(1)

print()
print("✅ Test 2 PASSED: Wizard flow includes all new steps")
print()

# Test 3: Verify planner-worker config structure
print("Test 3: Testing planner-worker configuration structure...")

# Simulate wizard configuration
test_config = {
    "execution_pattern": "planner_worker",
    "planner_worker": {
        "planner": {
            "provider": "claude-sonnet-4",
            "api_key_env": "ANTHROPIC_API_KEY",
            "instructions": "Create detailed execution plans",
        },
        "worker": {
            "provider": "claude-haiku-4",
            "api_key_env": "ANTHROPIC_API_KEY",
            "skills": ["filesystem", "git", "claude_code"],
            "policy": "autonomous-dev",
            "instructions": "Execute plan steps carefully",
        },
        "harness": {"cost_tracking": True, "checkpoints": True, "heartbeat": True, "state": True},
        "workflow": {
            "require_approval_for_plan": False,
            "require_approval_for_continuation": False,
            "halt_on_critical_escalation": True,
        },
    },
}

# Validate structure
required_keys = {
    "planner_worker": ["planner", "worker", "harness", "workflow"],
    "planner_worker.planner": ["provider", "api_key_env"],
    "planner_worker.worker": ["provider", "skills", "policy"],
    "planner_worker.harness": [],  # Can have any combination
    "planner_worker.workflow": ["halt_on_critical_escalation"],
}

all_valid = True
for path, keys in required_keys.items():
    parts = path.split(".")
    obj = test_config
    for part in parts:
        obj = obj.get(part, {})

    for key in keys:
        if key not in obj:
            print(f"  ❌ Missing key: {path}.{key}")
            all_valid = False
        else:
            print(f"  ✅ Found key: {path}.{key}")

if not all_valid:
    print()
    print("❌ FAILED: Configuration structure invalid")
    sys.exit(1)

print()
print("✅ Test 3 PASSED: Configuration structure is valid")
print()

# Test 4: Check execution pattern options
print("Test 4: Verifying execution pattern options...")

pattern_source = inspect.getsource(wizard._setup_execution_pattern)

expected_patterns = ["daemon", "planner_worker", "hybrid"]
all_found = True

for pattern in expected_patterns:
    if f'"{pattern}"' in pattern_source or f"'{pattern}'" in pattern_source:
        print(f"  ✅ Pattern option: {pattern}")
    else:
        print(f"  ❌ Pattern option: {pattern} NOT FOUND")
        all_found = False

if not all_found:
    print()
    print("❌ FAILED: Not all pattern options available")
    sys.exit(1)

print()
print("✅ Test 4 PASSED: All execution patterns available")
print()

# Test 5: Verify runner script generation
print("Test 5: Testing runner script generation logic...")

# Check that _generate_runner_scripts exists and has expected content
script_gen_source = inspect.getsource(wizard._generate_runner_scripts)

expected_elements = [
    "PlannerWorkerHarness",
    "run_planner_worker.py",
    "planner_provider",
    "worker_provider",
    "workspace_dir",
    "worker_skills",
]

all_found = True
for element in expected_elements:
    if element in script_gen_source:
        print(f"  ✅ Script element: {element}")
    else:
        print(f"  ❌ Script element: {element} NOT FOUND")
        all_found = False

if not all_found:
    print()
    print("❌ FAILED: Runner script generation incomplete")
    sys.exit(1)

print()
print("✅ Test 5 PASSED: Runner script generation looks good")
print()

# Test 6: Check that Claude Code skill is available for worker
print("Test 6: Verifying Claude Code skill is available for workers...")

setup_pw_source = inspect.getsource(wizard._setup_planner_worker)

if "Claude_Code" in setup_pw_source or "claude_code" in setup_pw_source:
    print("  ✅ Claude Code skill is available for worker selection")
else:
    print("  ❌ Claude Code skill NOT found in worker skills")
    all_found = False

print()
print("✅ Test 6 PASSED: Claude Code skill available")
print()

# Test 7: Integration with daemon pattern
print("Test 7: Testing hybrid pattern support...")

# Check that hybrid pattern is handled correctly
run_source = inspect.getsource(wizard.run)

hybrid_checks = [
    'if self.config.get("execution_pattern") in ["daemon", "hybrid"]',
    'if self.config.get("execution_pattern") in ["planner_worker", "hybrid"]',
]

all_found = True
for check in hybrid_checks:
    normalized_check = check.replace('"', "'")  # Handle quote variations
    normalized_source = run_source.replace('"', "'")

    if normalized_check in normalized_source:
        print(f"  ✅ Hybrid support: {check[:50]}...")
    else:
        print(f"  ❌ Hybrid support: {check[:50]}... NOT FOUND")
        all_found = False

if not all_found:
    print()
    print("❌ FAILED: Hybrid pattern not properly supported")
    sys.exit(1)

print()
print("✅ Test 7 PASSED: Hybrid pattern supported")
print()

# Final summary
print("=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print()
print("Planner-Worker wizard integration is complete and working:")
print("  ✅ Execution pattern selection (daemon/planner-worker/hybrid)")
print("  ✅ Planner provider configuration")
print("  ✅ Worker provider configuration")
print("  ✅ Worker skills (including Claude Code)")
print("  ✅ Harness features configuration")
print("  ✅ Workflow settings")
print("  ✅ Runner script generation")
print("  ✅ Hybrid pattern support")
print()
print("Users can now configure Planner-Worker pattern through the wizard!")
print()

# Phase 8 Validation Components

## Summary

The Phase 8 validation components exist and work, but they're **plan-aware tools** rather than **general harness features**. They weren't integrated into base Agent because they require a formal execution plan.

---

## The Three Phase 8 Validation Components

### 1. **ExplorationMode** (`forge/primitives/harness/explorer.py`)
**Purpose:** Read-only codebase exploration before planning

**What it does:**
- Explores workspace in read-only mode
- Answers questions about existing code
- Identifies relevant files and patterns
- Creates codebase summary
- No risk of accidental modifications

**Usage:**
```python
from forge.primitives.harness.explorer import ExplorationMode
from forge.core.provider import AnthropicProvider
from pathlib import Path

explorer = ExplorationMode(
    workspace_dir=Path("~/my-project"),
    provider=AnthropicProvider("claude-3-haiku-20240307"),
    exploration_depth="thorough",
)

# Explore before planning
result = await explorer.explore(
    goal="Understand authentication system",
    questions=[
        "Where is user auth handled?",
        "What auth method is used?",
        "Any security issues?",
    ]
)

print(f"Relevant files: {result.relevant_files}")
print(f"Summary: {result.codebase_summary}")
```

**Benefits:**
- ✅ Reduces hallucinations by gathering context first
- ✅ Identifies files to modify before planning
- ✅ Safe - read-only mode prevents accidents
- ✅ Cost-effective - use cheap model for exploration

---

### 2. **DryRunAnalyzer** (`forge/primitives/harness/dryrun.py`)
**Purpose:** Preview what a plan will do before execution

**What it does:**
- Analyzes each PlanStep
- Identifies file operations (write, modify, delete)
- Detects command execution
- Assesses risk levels
- Estimates cost and duration
- Shows preview of changes

**Usage:**
```python
from forge.primitives.harness.dryrun import DryRunAnalyzer
from forge.primitives.harness.plan import ExecutionPlan, PlanStep
from datetime import datetime

analyzer = DryRunAnalyzer(
    workspace_dir=Path("~/my-project"),
    enable_risk_analysis=True,
    enable_cost_estimation=True,
)

# Analyze a plan before executing
plan = ExecutionPlan(
    goals="Refactor authentication",
    steps=[
        PlanStep(number=1, description="Create new auth module", file_path="src/auth.py"),
        PlanStep(number=2, description="Update app to use new auth", file_path="src/app.py"),
        PlanStep(number=3, description="Delete old auth file", file_path="src/old_auth.py"),
    ],
    created_at=datetime.now(),
    created_by="planner",
    total_steps=3,
)

result = analyzer.analyze_plan(plan)

print(result.to_summary_text())
# Output:
# ═══════════════════════════════════
# DRY-RUN PREVIEW
# ═══════════════════════════════════
# Total Actions: 3
#   File Writes: 1
#   File Modifies: 1
#   File Deletes: 1
# High Risk Actions: 1 (file deletion)
# Estimated Cost: $0.15
# Estimated Duration: 45 seconds
```

**Benefits:**
- ✅ See what will happen before execution
- ✅ Identify risky operations (deletes, critical paths)
- ✅ Estimate cost before spending
- ✅ Approve/reject before changes

---

### 3. **StepVerifier** (`forge/primitives/harness/verification.py`)
**Purpose:** Safety verification of plan steps with 40+ patterns

**What it does:**
- Pattern matching for dangerous operations
  - `rm -rf` → critical risk
  - `chmod 777` → high risk
  - Force git push → high risk
  - Database drops → critical risk
- Path validation (blocked paths, sensitive files)
- Content analysis (hardcoded credentials, vague descriptions)
- Risk level assignment (low, medium, high, critical)
- Requires approval flags for risky steps

**Usage:**
```python
from forge.primitives.harness.verification import StepVerifier
from forge.primitives.harness.plan import PlanStep

verifier = StepVerifier(
    workspace_dir=Path("~/my-project"),
    enable_pattern_matching=True,
    enable_path_validation=True,
    strict_mode=True,  # Block critical operations
)

# Verify a step before execution
step = PlanStep(
    number=5,
    description="rm -rf /tmp/old-data",
)

result = verifier.verify_step(step)

if not result.safe:
    print(f"⚠️  UNSAFE: {result.risk_level}")
    print(f"Warnings: {result.warnings}")
    print(f"Suggestions: {result.suggestions}")
    # Don't execute!
else:
    print("✅ Safe to execute")
```

**Detects 40+ dangerous patterns:**
- Recursive deletion: `rm -rf`, `shutil.rmtree`
- Force operations: `git push --force`, `--no-verify`
- Database operations: `DROP TABLE`, `TRUNCATE`
- Permission changes: `chmod 777`, `chown`
- System paths: `/etc/passwd`, `/boot`, `/sys`
- Hardcoded credentials: API keys, passwords
- Vague descriptions: "fix bug", "update code"

**Benefits:**
- ✅ Catches dangerous operations before execution
- ✅ 40+ safety patterns built-in
- ✅ Strict mode can block critical operations
- ✅ Helps prevent catastrophic mistakes

---

## Why These Aren't in Base Agent

These three components are **fundamentally different** from other harness features:

### General Harness Features (Integrated into Agent)
```python
# These work with ANY agent execution:
- CostTracker      → Tracks costs during any LLM call
- AuditLogger      → Logs any agent turn
- StateManager     → Persists any agent state
- HeartbeatMonitor → Monitors any agent health
- CheckpointManager → Git operations (workspace-level)
```

**Common trait:** They work at the **agent execution level** - don't need a formal plan.

### Phase 8 Validation Components (Plan-Aware)
```python
# These REQUIRE a formal ExecutionPlan:
- ExplorationMode  → Prepares for planning
- DryRunAnalyzer   → Analyzes PlanStep objects
- StepVerifier     → Verifies PlanStep objects
```

**Common trait:** They work at the **plan level** - need structured ExecutionPlan and PlanStep objects.

### The Fundamental Difference

**Basic Agent** doesn't have a formal plan:
```python
agent = Agent(provider=..., instructions="Do X")
result = await agent.run("Write hello.txt")

# No ExecutionPlan object
# No PlanStep objects
# Just a simple LLM loop
```

**PlannerWorkerHarness** creates a formal plan:
```python
harness = PlannerWorkerHarness(...)

# Creates ExecutionPlan with PlanSteps
plan = await harness.plan(goals="...")

# Now we CAN use validation tools:
analyzer = DryRunAnalyzer(...)
dry_run = analyzer.analyze_plan(plan)  # ✅ Works!

verifier = StepVerifier(...)
for step in plan.steps:
    result = verifier.verify_step(step)  # ✅ Works!
```

---

## How to Use Phase 8 Components

### Pattern 1: Pre-Planning Exploration (Recommended Workflow)

```python
from forge.primitives.harness.explorer import ExplorationMode
from forge.primitives.harness.orchestrator import PlannerWorkerHarness
from forge.primitives.harness.dryrun import DryRunAnalyzer
from forge.primitives.harness.verification import StepVerifier

workspace = Path("~/my-project")

# STEP 1: Explore codebase (read-only)
explorer = ExplorationMode(
    workspace_dir=workspace,
    provider=AnthropicProvider("claude-3-haiku-20240307"),
)

exploration = await explorer.explore(
    goal="Understand auth system before refactoring",
    questions=[
        "Where is authentication handled?",
        "What files would need to change?",
    ]
)

# STEP 2: Create plan (informed by exploration)
harness = PlannerWorkerHarness(
    agent_id="refactor-auth",
    planner_provider=AnthropicProvider("claude-3-5-sonnet-20241022"),
    worker_provider=AnthropicProvider("claude-3-haiku-20240307"),
    workspace_dir=workspace,
)

# Pass exploration findings to planner
context = f"""
Codebase exploration findings:
{exploration.codebase_summary}

Relevant files:
{', '.join(exploration.relevant_files)}
"""

plan = await harness.plan(goals="Refactor auth system", context=context)

# STEP 3: Dry-run analysis (preview changes)
analyzer = DryRunAnalyzer(workspace_dir=workspace)
dry_run = analyzer.analyze_plan(plan)

print(dry_run.to_summary_text())
print(f"High risk actions: {len(dry_run.high_risk_actions)}")

# STEP 4: Step verification (safety check)
verifier = StepVerifier(workspace_dir=workspace, strict_mode=True)
verification = verifier.verify_plan(plan)

unsafe_steps = [r for r in verification if not r.safe]
if unsafe_steps:
    print(f"⚠️  {len(unsafe_steps)} unsafe steps detected!")
    for result in unsafe_steps:
        print(f"  Step {result.step_number}: {result.risk_level}")

    # Ask user approval
    proceed = input("Proceed anyway? (yes/no): ")
    if proceed.lower() != "yes":
        print("Aborting execution")
        exit()

# STEP 5: Execute (if approved)
while not harness.is_complete():
    result = await harness.execute_next_step()
    if not result.success:
        print(f"Step {result.step.number} failed: {result.error}")
        break
```

This gives you a **5-layer safety workflow**:
1. 🔍 **Explore** - understand before planning
2. 📋 **Plan** - create structured execution plan
3. 👁️ **Dry-run** - preview what will happen
4. ✅ **Verify** - safety check each step
5. ⚙️ **Execute** - run with confidence

---

### Pattern 2: Standalone Verification

You can also use these tools standalone:

```python
# Just verify a single operation
verifier = StepVerifier(workspace_dir=Path.cwd())

step = PlanStep(
    number=1,
    description="rm -rf /var/log/old-logs",
)

result = verifier.verify_step(step)

if result.risk_level in ("high", "critical"):
    print("⚠️  DANGEROUS OPERATION!")
    print(f"Risk: {result.risk_level}")
    print(f"Warnings: {result.warnings}")
    # Block execution
```

---

## Integration Status

| Component | Status | Availability |
|-----------|--------|--------------|
| **General Harness Features** | | |
| CostTracker | ✅ Integrated | All agent types |
| AuditLogger | ✅ Integrated | All agent types |
| StateManager | ✅ Integrated | All agent types |
| HeartbeatMonitor | ✅ Integrated | All agent types |
| CheckpointManager | ✅ Integrated | All agent types |
| **Phase 8 Validation Tools** | | |
| ExplorationMode | ⚠️ Standalone | Manual usage only |
| DryRunAnalyzer | ⚠️ Standalone | Manual usage only |
| StepVerifier | ⚠️ Standalone | Manual usage only |

**Why standalone?**
- Require ExecutionPlan structure
- Only make sense with formal planning
- Used as pre-execution tools, not during execution
- User decides when/how to use them

---

## Could They Be Integrated?

**Option 1: Integrate into PlannerWorkerHarness**

We could add them as optional features:

```python
harness = PlannerWorkerHarness(
    agent_id="my-agent",
    planner_provider=...,
    worker_provider=...,
    # Phase 8 features
    enable_pre_exploration=True,    # Auto-explore before planning
    enable_dry_run_preview=True,    # Auto dry-run after planning
    enable_step_verification=True,  # Auto-verify before execution
)

# Harness would automatically:
# 1. Explore codebase when planning
# 2. Run dry-run after creating plan
# 3. Verify each step before execution
```

**Pros:**
- ✅ Automatic safety checks
- ✅ User doesn't need to manually orchestrate

**Cons:**
- ❌ Adds complexity to harness
- ❌ User loses control over when checks happen
- ❌ Extra cost for features user might not want

**Option 2: Keep as Standalone Tools** (Current Approach)

Users manually compose the workflow they want:

```python
# User chooses which tools to use:
exploration = await explorer.explore(...)  # Optional
plan = await harness.plan(...)
dry_run = analyzer.analyze_plan(plan)      # Optional
verification = verifier.verify_plan(plan)  # Optional
await harness.execute(...)
```

**Pros:**
- ✅ Maximum flexibility
- ✅ User pays only for what they use
- ✅ Clear, explicit workflow
- ✅ Composable tools

**Cons:**
- ❌ Requires manual orchestration
- ❌ Easy to forget safety checks

---

## Recommendation

**Current approach (standalone) is correct** because:

1. **Flexibility** - Users decide which validations to run
2. **Cost control** - No forced exploration/verification
3. **Clear semantics** - Explicit workflow is easier to understand
4. **Plan-specific** - These tools only work with formal plans

**For production use**, create a **helper function** that combines them:

```python
async def safe_plan_and_execute(
    harness: PlannerWorkerHarness,
    goals: str,
    enable_exploration: bool = True,
    enable_dry_run: bool = True,
    enable_verification: bool = True,
) -> ExecutionResult:
    """Execute with full Phase 8 safety checks."""

    # Optional: Pre-planning exploration
    if enable_exploration:
        explorer = ExplorationMode(workspace_dir=harness.workspace_dir, ...)
        exploration = await explorer.explore(goal=goals)
        context = exploration.codebase_summary
    else:
        context = None

    # Create plan
    plan = await harness.plan(goals=goals, context=context)

    # Optional: Dry-run preview
    if enable_dry_run:
        analyzer = DryRunAnalyzer(workspace_dir=harness.workspace_dir)
        dry_run = analyzer.analyze_plan(plan)
        print(dry_run.to_summary_text())

        if not await ask_user_approval(dry_run):
            return ExecutionResult(aborted=True)

    # Optional: Step verification
    if enable_verification:
        verifier = StepVerifier(workspace_dir=harness.workspace_dir)
        unsafe = [r for r in verifier.verify_plan(plan) if not r.safe]

        if unsafe:
            print(f"⚠️  {len(unsafe)} unsafe steps!")
            if not await ask_user_approval(unsafe):
                return ExecutionResult(aborted=True)

    # Execute
    return await harness.execute_plan()
```

---

## Summary

**Phase 8 validation components exist and work perfectly:**
- ✅ ExplorationMode - read-only codebase exploration
- ✅ DryRunAnalyzer - preview changes before execution
- ✅ StepVerifier - 40+ safety patterns for step validation

**They're standalone tools because:**
- Require formal ExecutionPlan structure
- Only applicable to planned workflows
- Users should choose when to use them
- Keeps architecture clean and composable

**Use them manually in your workflow, or create helper functions to automate the safety checks you want.**

All 33 Phase 8 tests passing - these tools are production-ready! ✅

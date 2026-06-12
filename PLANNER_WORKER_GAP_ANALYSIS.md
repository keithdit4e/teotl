# Planner/Worker Pattern: Missing from Wizard

## Executive Summary

The wizard does **NOT** include Planner/Worker pattern configuration. This is a **critical gap** because PlannerWorkerHarness is one of the two primary execution patterns in Forge.

**Current State:**
- Wizard only configures HeartbeatDaemon pattern (autonomous task/mission execution)
- PlannerWorkerHarness pattern completely missing from onboarding
- Users must manually code setup for planner/worker

**Impact:**
- Users don't discover planner/worker pattern
- Miss out on 93-97% cost savings
- Can't easily configure complex, planned workflows

---

## Two Execution Patterns in Forge

### Pattern 1: HeartbeatDaemon (Currently in Wizard ✅)

**Use Case:** Autonomous background execution of tasks and missions

**How it works:**
- Daemon polls for work every N seconds
- Executes tasks by priority
- Executes missions on schedule
- Runs continuously in background

**Configuration:**
```yaml
agent:
  agent_id: email-assistant
  instructions: "Process emails autonomously"
  work_types: [Tasks, Missions]

daemon:
  poll_interval: 30
```

**When to use:**
- Ongoing autonomous work
- Task queue processing
- Scheduled missions (hourly, daily, weekly)
- Background automation

**Examples:**
- Email assistant checking inbox every hour
- Code reviewer processing PRs
- Report generator running daily
- System monitor checking health

**Wizard Support:** ✅ FULL

---

### Pattern 2: PlannerWorkerHarness (NOT in Wizard ❌)

**Use Case:** Complex tasks requiring upfront planning

**How it works:**
1. **Planner Phase** (runs once with expensive model):
   - Analyzes goal/requirements
   - Creates detailed execution plan (PLAN.md)
   - Breaks down into atomic steps
   - Defines verification criteria

2. **Worker Phase** (runs many times with cheap model):
   - Executes each step from plan
   - Updates progress (PROGRESS.md)
   - Verifies completion
   - Reports results

**Configuration:**
```yaml
# NOT CURRENTLY CONFIGURABLE VIA WIZARD!
planner:
  provider: claude-sonnet-4  # Expensive, smart
  instructions: "Create detailed execution plans"

worker:
  provider: claude-haiku-4   # Cheap, fast
  skills: [filesystem, git, web]
  instructions: "Execute plan steps carefully"
  policy: autonomous-dev
```

**Cost Savings:**
- Planner runs once: $0.10
- Worker runs 20 times: 20 × $0.005 = $0.10
- **Total: $0.20** (vs $2.00 if Sonnet ran 20 times)
- **Savings: 90%**

**When to use:**
- Complex refactoring projects
- Multi-step feature implementation
- Large-scale code migrations
- Research projects with multiple phases
- Any task requiring strategic planning

**Examples:**
- "Refactor authentication system to use JWT"
- "Migrate from REST to GraphQL across 50 files"
- "Implement feature X with tests and documentation"
- "Research topic Y and write comprehensive report"

**Wizard Support:** ❌ NONE

---

## What's Missing in the Wizard

### 1. Execution Pattern Selection

**Currently:**
- Wizard assumes HeartbeatDaemon pattern
- No option to choose execution pattern
- No explanation of differences

**Needed:**
```
Which execution pattern for your agent?

1. Autonomous Background Agent (Daemon)
   • Runs continuously in background
   • Processes tasks and missions as they arrive
   • Good for: Email assistant, monitoring, scheduled tasks
   • Cost: Moderate (runs frequently)

2. Planner-Worker for Complex Tasks
   • Creates detailed plan upfront
   • Executes steps systematically
   • Good for: Refactoring, migrations, complex features
   • Cost: Low (90% savings with smart planning)

3. Both (Hybrid)
   • Daemon handles routine work
   • Planner/Worker for complex tasks
   • Best of both worlds
```

### 2. Planner Configuration

**Missing:**
- Planner provider selection (expensive model for planning)
- Planner instructions
- Planning strategy options

**Needed:**
```
Planner Configuration

Which model for planning? (Planner creates execution plans)
  • claude-sonnet-4 (best quality, recommended)
  • claude-opus-4 (most capable, slower)
  • gpt-4-turbo (OpenAI alternative)

Planning instructions (optional):
  [Custom instructions for planner agent]
  Default: "You are an expert planner..."

Planning strategy:
  • Detailed (more steps, safer)
  • Balanced (recommended)
  • High-level (fewer steps, faster)
```

### 3. Worker Configuration

**Missing:**
- Worker provider selection (cheap model for execution)
- Worker skills
- Worker policy
- Worker instructions

**Needed:**
```
Worker Configuration

Which model for execution? (Worker executes plan steps)
  • claude-haiku-4 (fastest, cheapest, recommended)
  • claude-sonnet-4 (more capable, expensive)
  • gpt-3.5-turbo (OpenAI alternative)

Worker skills (select all that apply):
  [✓] Filesystem - Read/write files
  [✓] Git - Version control operations
  [✓] Web - Fetch URLs, search
  [ ] Database - SQL queries
  [ ] Email - Send/receive emails

Worker security policy:
  • autonomous-dev (moderate, recommended for coding)
  • strict (limited access, safe)
  • permissive (full access, powerful)

Worker instructions (optional):
  [Custom instructions for worker agent]
  Default: "You are a careful executor..."
```

### 4. Harness Integration

**Missing:**
- PlannerWorkerHarness-specific settings
- Checkpoint configuration
- Approval workflow options
- Heartbeat monitoring tuning

**Needed:**
```
Planner-Worker Settings

Enable checkpoints?
  • Automatic snapshots after each step
  • Resume from last checkpoint on failure
  [✓] Yes (recommended)

Require approval between cycles?
  • Pause for human approval after plan creation
  • Pause every N steps during execution
  [ ] Yes (safer, interactive)
  [✓] No (fully autonomous)

Heartbeat monitoring:
  • Detect stuck worker
  • Alert on repeated errors
  [✓] Enabled (recommended)
```

---

## How Users Currently Use Planner/Worker

### Manual Setup (Current Approach)

```python
# User must write this code manually!
from forge.primitives.harness import PlannerWorkerHarness
from forge.core.provider import AnthropicProvider

harness = PlannerWorkerHarness(
    agent_id="refactoring-agent",
    planner_provider=AnthropicProvider(model="claude-sonnet-4"),
    worker_provider=AnthropicProvider(model="claude-haiku-4"),
    workspace_dir=Path("~/my-project"),
    worker_skills=["filesystem", "git"],
    worker_policy="autonomous-dev",
    enable_janitor=True,
    enable_heartbeat=True,
    enable_cost_tracking=True,
)

# Phase 1: Create plan
goals = Path("GOALS.md").read_text()
plan = await harness.plan(goals=goals)

# Phase 2: Execute plan
while not harness.is_complete():
    result = await harness.execute_next_step()
    print(f"Step {result.step.number}: {result.success}")
```

**Problems:**
- Requires Python knowledge
- Manual provider setup
- No guidance on model selection
- Easy to misconfigure
- Intimidating for new users

---

## Proposed Wizard Integration

### Option 1: Separate Execution Pattern Step (Recommended)

Add a new step early in wizard flow:

```
Step 2: Execution Pattern

How will your agent work?

1. Background Daemon (Continuous)
   ├─ Processes tasks as they arrive
   ├─ Runs scheduled missions
   └─ Best for: Automation, monitoring, routine work

2. Planner-Worker (On-Demand)
   ├─ Creates detailed plans for complex tasks
   ├─ Executes steps systematically
   └─ Best for: Refactoring, migrations, complex projects

3. Hybrid (Both)
   ├─ Daemon handles routine work
   ├─ Planner-Worker for complex tasks
   └─ Best for: Full-featured assistant

Choose execution pattern: [Hybrid]

[Explain differences] [Show examples]
```

### Option 2: Work Type Determines Pattern

Enhance existing work type selection:

```
Step 2: What will your agent work on?

[✓] Goals - Continuous objectives (requires Daemon)
[✓] Missions - Scheduled tasks (requires Daemon)
[✓] Tasks - One-time work (requires Daemon)
[✓] Complex Projects - Multi-step planned work (requires Planner-Worker)

Based on your selections, we'll configure:
  ✓ Background Daemon (for Goals, Missions, Tasks)
  ✓ Planner-Worker (for Complex Projects)
```

### Option 3: Advanced Users Only

Add planner-worker as an optional advanced section:

```
Step X: Advanced - Planner-Worker Pattern (Optional)

Enable Planner-Worker pattern for complex tasks?
  • Creates detailed plans before execution
  • 90% cost savings vs running expensive model repeatedly
  • Best for refactoring, migrations, multi-step projects

[✓] Yes, configure Planner-Worker
[ ] No, skip (use daemon only)
```

---

## Recommended Approach

**Phase 1: Add to Wizard (Essential)**

1. **Add execution pattern selection** (Step 2, before provider)
2. **Configure planner provider** (if planner-worker selected)
3. **Configure worker provider** (if planner-worker selected)
4. **Configure worker skills** (reuse existing skills step)
5. **Configure harness settings** (planner-worker specific)

**Phase 2: Generate Runner Script (Nice-to-have)**

Since planner-worker requires code, generate a starter script:

```python
# Generated by wizard: run_planner_worker.py
import asyncio
from pathlib import Path
from forge.primitives.harness import PlannerWorkerHarness
from forge.core.provider import AnthropicProvider

async def main():
    harness = PlannerWorkerHarness(
        agent_id="my-agent",
        planner_provider=AnthropicProvider(model="claude-sonnet-4"),
        worker_provider=AnthropicProvider(model="claude-haiku-4"),
        workspace_dir=Path.home() / "workspace",
        worker_skills=["filesystem", "git"],
        # ... all settings from wizard
    )

    # Load goals
    goals = (Path("GOALS.md").read_text()
             if Path("GOALS.md").exists()
             else "Complete the project requirements")

    # Phase 1: Plan
    print("Creating execution plan...")
    plan = await harness.plan(goals=goals)
    print(f"Plan created with {len(plan.steps)} steps")
    print(f"Review plan in: PLAN.md")

    # Phase 2: Execute
    print("\nExecuting plan...")
    while not harness.is_complete():
        result = await harness.execute_next_step()
        status = "✅" if result.success else "❌"
        print(f"{status} Step {result.step.number}: {result.step.description}")

    print("\n🎉 Execution complete!")

if __name__ == "__main__":
    asyncio.run(main())
```

User can then run:
```bash
python3 run_planner_worker.py
```

**Phase 3: CLI Command (Future)**

```bash
teotl plan "Refactor authentication to use JWT"
teotl execute  # Execute current plan
teotl status   # Show plan progress
```

---

## Configuration Schema

### Hybrid Config (Daemon + Planner-Worker)

```yaml
# Provider for daemon operations
provider:
  type: anthropic
  model: claude-sonnet-4

# Primary agent configuration
agent:
  agent_id: hybrid-agent
  instructions: "You are a full-featured assistant"
  work_types: [Goals, Missions, Tasks, Complex Projects]

  memory:
    enabled: true

  skills: [filesystem, web, git]

  harness:
    cost_tracking: true
    state: true

# Daemon configuration (for tasks/missions)
daemon:
  poll_interval: 30
  data_dir: ~/.teotl/hybrid-agent

# Planner-Worker configuration (for complex projects)
planner_worker:
  enabled: true

  planner:
    provider: claude-sonnet-4  # Expensive model
    instructions: "Create detailed, atomic execution plans"
    strategy: balanced

  worker:
    provider: claude-haiku-4   # Cheap model
    skills: [filesystem, git, web]
    policy: autonomous-dev
    instructions: "Execute plan steps carefully and verify results"

  # Harness settings for planner-worker
  harness:
    enable_janitor: true
    janitor_compact_every: 5
    janitor_max_tokens: 10000

    enable_heartbeat: true
    heartbeat_check_every: 5
    heartbeat_stuck_threshold: 10

    enable_checkpoints: true

    enable_cost_tracking: true

  # Workflow settings
  workflow:
    require_approval_for_plan: false
    require_approval_for_continuation: false
    halt_on_critical_escalation: true
```

---

## Implementation Estimate

### Wizard Changes

**Files to modify:**
- `forge/cli/wizard.py` - Add planner-worker configuration step

**New methods needed:**
1. `_setup_execution_pattern()` - Choose daemon/planner-worker/hybrid
2. `_setup_planner()` - Configure planner provider and settings
3. `_setup_worker()` - Configure worker provider and settings
4. `_setup_planner_worker_harness()` - Configure harness for planner-worker

**Estimated:** 200-300 lines

### Runner Generation

**Files to create:**
- Template for `run_planner_worker.py`
- Template for `run_daemon.py` (already exists)
- Template for `run_hybrid.py` (both patterns)

**Estimated:** 150-200 lines

### CLI Commands (Future)

**Files to create:**
- `forge/cli/plan.py` - Create/edit plans
- `forge/cli/execute.py` - Execute plans
- `forge/cli/status.py` - Show progress (works for both patterns)

**Estimated:** 300-400 lines

**Total Estimate:** 650-900 lines

---

## Priority Assessment

### Urgency: HIGH 🔴

**Reasons:**
1. **Feature Parity** - Planner-Worker is a core pattern, should be in wizard
2. **Cost Savings** - 90% savings is a huge value prop, users should know about it
3. **Use Case Coverage** - Many users need planning (refactoring, migrations, etc.)
4. **Discoverability** - Currently hidden, only code-savvy users can find it

### Impact: HIGH 📈

**Benefits:**
- Users discover planner-worker pattern during onboarding
- Massive cost savings (90%) for appropriate use cases
- Better task selection (daemon vs planner-worker)
- More professional onboarding experience

### Complexity: MEDIUM 🟡

**Challenges:**
- Need to explain two patterns clearly
- Configuration is more complex
- Need to generate runner script
- Testing is more involved

**Mitigations:**
- Good UX design with clear explanations
- Sensible defaults
- Examples and templates
- Gradual rollout (wizard first, CLI later)

---

## Recommendation

**Phase 1: Add to Wizard (4-6 hours)**
1. Add execution pattern selection step
2. Add planner configuration (if planner-worker selected)
3. Add worker configuration (if planner-worker selected)
4. Generate appropriate runner script(s)
5. Update config.yaml schema
6. Test end-to-end

**Phase 2: CLI Commands (8-12 hours)**
1. `teotl plan` - Create/edit plans
2. `teotl execute` - Execute plans
3. `teotl status` - Unified status for both patterns
4. Integration tests

**Total Estimate: 12-18 hours**

---

## Summary

**Current State:**
- ❌ Planner-Worker pattern NOT in wizard
- ❌ Users must manually code setup
- ❌ Poor discoverability
- ❌ Missing out on 90% cost savings

**After Implementation:**
- ✅ Planner-Worker pattern fully integrated
- ✅ Clear pattern selection during onboarding
- ✅ Generated runner scripts
- ✅ Users discover cost-saving opportunities
- ✅ Professional, complete onboarding

**ROI:**
- High user value (90% cost savings on appropriate tasks)
- Better feature adoption
- More complete product
- Competitive advantage (few frameworks offer this pattern)

**Next Step:** Implement Phase 1 (wizard integration)

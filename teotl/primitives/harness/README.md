# Harness Engineering Primitives

Framework-level primitives for building reliable, cost-efficient autonomous agents based on Anthropic's Harness Engineering principles.

## Overview

The harness package provides **artifact-driven state management** that makes autonomous agents:
- **More reliable** - Progress tracked outside conversation history
- **More efficient** - Context stays <10K tokens via compaction
- **More observable** - Clear state in PROGRESS.md, STATE.json, DECISION_LOG.md
- **Agent-type agnostic** - Works for coding, inbox monitoring, CRM sync, etc.

## Core Primitives

### 1. ProgressTracker (PROGRESS.md)

Tracks current task, completed tasks, and remaining tasks in a durable markdown file.

**Use for:**
- Multi-step workflows
- Batch processing progress
- Roadmap execution
- Mission completion tracking

**Example:**
```python
from forge.primitives.harness import ProgressTracker

tracker = ProgressTracker(agent_id="coding-assistant")

# Update progress
tracker.update(
    current="Add type hints to utils.py",
    completed=["Fix bug in parser.py", "Add tests"],
    remaining=["Refactor database.py", "Update docs"]
)

# Read progress
state = tracker.read()
print(f"Progress: {state.completion_percentage}%")
print(f"Current: {state.current}")
```

**Generated PROGRESS.md:**
```markdown
# Progress

Last updated: 2024-03-27T10:30:00

## Current Task

Add type hints to utils.py

## Completed (2)

- ✅ Fix bug in parser.py
- ✅ Add tests

## Remaining (2)

- ⏳ Refactor database.py
- ⏳ Update docs

## Progress Summary

- Total tasks: 4
- Completed: 2
- Remaining: 2
- Progress: 50.0%
```

---

### 2. StateManager (STATE.json)

Persists variables, flags, counters, and checkpoints across agent executions.

**Use for:**
- Sync cursors (last processed record ID)
- Phase tracking (initializing → executing → verifying)
- Counters (consecutive_failures, records_processed)
- Flags (credentials_valid, tests_passed)
- Checkpoints (last_successful_commit)

**Example:**
```python
from forge.primitives.harness import StateManager

state = StateManager(agent_id="crm-sync")

# Save state
state.save(
    last_sync_cursor="2024-03-27T10:30:00Z",
    records_processed=147,
    credentials_valid=True,
    phase="syncing_contacts"
)

# Read state
cursor = state.get("last_sync_cursor")
phase = state.get("phase", default="initializing")

# Update specific values
state.update(records_processed=148)

# Counters
state.increment("consecutive_successes")
state.increment("records_processed", by=10)
state.reset_counter("errors")

# Flags
state.set_flag("ready_for_deployment", True)
ready = state.get_flag("ready_for_deployment")
```

**Generated STATE.json:**
```json
{
  "last_sync_cursor": "2024-03-27T10:30:00Z",
  "records_processed": 148,
  "credentials_valid": true,
  "phase": "syncing_contacts",
  "consecutive_successes": 1,
  "ready_for_deployment": true,
  "_updated_at": "2024-03-27T10:32:15",
  "_agent_id": "crm-sync"
}
```

---

### 3. ContextJanitor (DECISION_LOG.md)

Compacts context by extracting key decisions and enabling context resets.

**Use for:**
- Preventing context bloat (keeps context <10K tokens)
- Logging important decisions
- Enabling context resets without losing state
- Debugging agent reasoning

**Example:**
```python
from forge.primitives.harness import ContextJanitor

janitor = ContextJanitor(
    agent_id="coding-assistant",
    compact_every=10  # Compact every 10 turns
)

# After each agent turn
janitor.after_turn(agent_response)

# Check if context should be reset
if janitor.should_reset_context():
    # Reset agent context, reload from artifacts
    agent.reset_context(preserve_artifacts=True)
```

**Generated DECISION_LOG.md:**
```markdown
# Decision Log

Agent: coding-assistant
Created: 2024-03-27T10:00:00

This log tracks key decisions made by the agent across turns.
Context is compacted every 10 turns to keep the agent focused.

---

## Turns 1-10

Compacted: 2024-03-27T10:15:00

**Turn 1** (10:01:23): I decided to add type hints to improve code quality.

**Turn 2** (10:02:45): Fixed the import error because it was blocking tests.

**Turn 5** (10:08:12): I chose to refactor the database module for better maintainability.

**Turn 7** (10:11:34): Committed changes after all tests passed.

---

## Turns 11-20

...
```

---

### 4. HarnessAgent

Wrapper that adds all harness primitives to any Agent.

**Use for:**
- Autonomous agents (continuous code improvement)
- Interactive assistants (inbox monitoring)
- Data sync agents (CRM/ERP integration)
- Any agent that needs durable state

**Example:**
```python
from forge.core.provider import AnthropicProvider
from forge.primitives.harness import HarnessAgent

agent = HarnessAgent(
    agent_id="coding-assistant",
    provider=AnthropicProvider(
        api_key="...",
        model="claude-3-haiku-20240307"
    ),
    instructions="You are a helpful coding assistant",
    skills=["filesystem", "git"],
    # Harness options
    enable_progress=True,
    enable_state=True,
    enable_janitor=True,
    compact_every=10,
    load_artifacts_in_prompt=True  # Auto-inject artifacts
)

# Use like normal Agent
response = await agent.run("Improve code quality")

# Access harness primitives
agent.progress.update(current="Adding type hints", ...)
agent.state.save(phase="testing", tests_passed=4)
```

---

## Architecture

### Artifact-Driven Execution

Instead of relying solely on conversation history, harness agents read state from durable artifacts:

```
┌─────────────────────────────────────────┐
│         Agent Execution Turn            │
├─────────────────────────────────────────┤
│                                         │
│  1. Load Artifacts                      │
│     ├─ PROGRESS.md → Current task       │
│     ├─ STATE.json → Variables/flags     │
│     └─ DECISION_LOG.md → Recent history │
│                                         │
│  2. Agent Decides & Acts                │
│     - Has full context from artifacts   │
│     - Not dependent on conversation     │
│                                         │
│  3. Update Artifacts                    │
│     ├─ Update PROGRESS.md               │
│     ├─ Save STATE.json                  │
│     └─ Log decision                     │
│                                         │
│  4. Context Compaction (every N turns)  │
│     ├─ Append to DECISION_LOG.md        │
│     ├─ Clear conversation history       │
│     └─ Keep only artifacts              │
│                                         │
└─────────────────────────────────────────┘
```

### Why This Works

**Problem:** Conversation history grows unbounded
- Turn 1: User message + response (1K tokens)
- Turn 10: User message + 9 previous turns (15K tokens)
- Turn 50: Context maxed out (>128K tokens)

**Solution:** Artifacts + compaction
- Artifacts contain **signals** (decisions, progress, state)
- Conversation contains **noise** (test output, debugging)
- Every 10 turns: Extract signals → DECISION_LOG.md, discard noise
- Agent reloads from artifacts, context stays <10K tokens

---

## Agent Type Examples

### Autonomous Code Agent

```python
agent = HarnessAgent(
    agent_id="code-improver",
    provider=provider,
    instructions=INSTRUCTIONS_AUTONOMOUS_md,
    enable_progress=True,  # Track improvements
    enable_state=True,     # Remember test results
    enable_janitor=True,   # Prevent context bloat
    compact_every=10
)

# Initialize progress from roadmap
agent.progress.update(
    current="Add type hints to utils.py",
    completed=[],
    remaining=["Fix bug in parser.py", "Add tests", ...]
)

# Run autonomously
while not agent.progress.read().is_complete:
    await agent.run("Work on next improvement from PROGRESS.md")
```

### Interactive Assistant (Inbox Monitoring)

```python
agent = HarnessAgent(
    agent_id="inbox-assistant",
    provider=provider,
    instructions="Monitor user's inbox and help with actions",
    enable_progress=False,  # No roadmap needed
    enable_state=True,      # Remember last_email_checked
    enable_janitor=True,    # Prevent email bloat
    compact_every=5
)

# Save state
agent.state.save(
    last_email_checked="msg-12345",
    emails_processed_today=47
)

# Process inbox
await agent.run("Check for new emails and suggest actions")
```

### CRM Sync Agent

```python
agent = HarnessAgent(
    agent_id="salesforce-sync",
    provider=provider,
    instructions="Sync contacts between Salesforce and PostgreSQL",
    enable_progress=True,  # Track batch progress
    enable_state=True,     # Remember sync cursor
    enable_janitor=True,   # Prevent record data bloat
    compact_every=20
)

# Load state
cursor = agent.state.get("last_sync_cursor", default="0")

# Sync batch
agent.progress.update(
    current="Syncing contacts batch 47/100",
    completed=[f"Batch {i}" for i in range(46)],
    remaining=[f"Batch {i}" for i in range(47, 100)]
)

await agent.run(f"Sync next batch starting from cursor {cursor}")

# Save new cursor
agent.state.save(last_sync_cursor=new_cursor)
```

---

## Configuration Patterns

### Opt-In Per Agent Type

```yaml
# config/agent_types/assistant.yaml
agent_type: assistant
harness:
  state_artifacts: true       # Track conversation state
  context_janitor: true       # Prevent inbox bloat
  planner_worker: false       # Interactive, no planning
  evaluator: true             # Verify actions completed
  heartbeat: true             # Check inbox every 15 min
```

```yaml
# config/agent_types/autonomous_dev.yaml
agent_type: autonomous_dev
harness:
  state_artifacts: true       # Track progress
  context_janitor: true       # Prevent test output bloat
  planner_worker: true        # Sonnet plans, Haiku executes
  evaluator: true             # Verify tests pass
  heartbeat: true             # Continuous operation
```

---

## Testing

Run the harness demo to see all primitives in action:

```bash
python3 examples/harness_demo.py
```

This creates:
- `~/.teotl/agents/demo-agent/PROGRESS.md`
- `~/.teotl/agents/demo-agent/STATE.json`
- `~/.teotl/agents/demo-agent/DECISION_LOG.md`

---

## Phase 2: Planner-Worker Separation ✅ COMPLETE

Coordinates two-phase execution for 93-97% cost savings:

### PlannerWorkerHarness

**Usage:**
```python
from forge.core.provider import AnthropicProvider
from forge.primitives.harness import PlannerWorkerHarness

harness = PlannerWorkerHarness(
    agent_id="coding-assistant",
    # Expensive model for planning (runs ONCE)
    planner_provider=AnthropicProvider(model="claude-sonnet-4"),
    # Cheap model for execution (runs MANY times)
    worker_provider=AnthropicProvider(model="claude-3-haiku-20240307"),
    workspace_dir=agent_dir,
    worker_skills=["filesystem", "git"]
)

# Phase 1: Create plan (Sonnet - $15)
plan = await harness.plan(goals=goals_content)

# Phase 2: Execute plan (Haiku - $0.25 per step)
while not harness.is_complete():
    result = await harness.execute_next_step()
    print(f"Step {result.step.number}: {result.success}")
```

**Cost Comparison (20 improvements):**
- ❌ Sonnet for everything: 20 × $15 = **$300**
- ⚠️ Haiku for everything: 20 × $0.25 = **$5** (unreliable planning)
- ✅ Planner-Worker: $15 + (20 × $0.25) = **$20** (93% savings!)

**Generated Artifacts:**
- `PLAN.md` - Detailed execution plan with atomic steps
- `PROGRESS.md` - Updated after each step completion
- `STATE.json` - Worker phase, retry counts, etc.

**Demo:**
```bash
python3 examples/planner_worker_demo.py
python3 run_planner_worker.py  # Production usage
```

See `forge/primitives/harness/planner.py`, `worker.py`, `orchestrator.py`

---

## Phase 3: Supervisor Pattern (Evaluator + Closed Loop) ✅ COMPLETE

Intelligent closed-loop system where Sonnet plans, Haiku executes, and Sonnet evaluates - repeating until goals achieved.

### Supervised Execution

**Usage:**
```python
from forge.primitives.harness import PlannerWorkerHarness

harness = PlannerWorkerHarness(
    agent_id="coding-assistant",
    planner_provider=AnthropicProvider(model="claude-sonnet-4"),
    worker_provider=AnthropicProvider(model="claude-3-haiku-20240307"),
    workspace_dir=agent_dir,
    worker_skills=["filesystem", "git"]
)

# Run supervised cycle (autonomous until goals achieved)
result = await harness.run_supervised_cycle(
    goals="Improve code quality and fix bugs",
    max_cycles=3
)

if result.complete:
    print(result.completion_report)  # User-facing report
else:
    print(f"Stopped: {result.reason}")
```

**The Cycle:**
```
CYCLE 1:
  Planner (Sonnet):  Creates 10-step plan → PLAN.md
  Worker (Haiku):    Executes all 10 steps → PROGRESS.md
  Evaluator (Sonnet): "Good! But found 3 bugs during review"
                     → Generates continuation goals

CYCLE 2:
  Planner (Sonnet):  Creates 3-step bug fix plan
  Worker (Haiku):    Executes 3 fixes
  Evaluator (Sonnet): "Perfect! Tests pass. COMPLETE ✅"
                     → Generates completion report
```

**Cost Example (2 cycles, 13 total steps):**
- Cycle 1: $15 (plan) + $2.50 (10 steps) + $10 (eval) = $27.50
- Cycle 2: $15 (plan) + $0.75 (3 steps) + $10 (eval) = $25.75
- **Total: $53.25** vs $195 using Sonnet for everything (73% savings!)

**Key Features:**
1. **Autonomous Goal Achievement**
   - User provides goals once
   - System works through multiple cycles automatically
   - Reports when complete

2. **Intelligent Adaptation**
   - Evaluator finds issues during review
   - Planner creates targeted continuation plans
   - Worker executes precisely

3. **Quality Assurance**
   - Evaluator verifies goals met
   - Tests must pass to mark complete
   - High confidence threshold (>0.8)

4. **Observable**
   - Each cycle archived
   - Final completion report
   - All decisions logged

**Generated Artifacts:**
- `PLAN.md` - Latest execution plan
- `PLAN_cycle1.md`, `PLAN_cycle2.md` - Archived plans
- `PROGRESS.md` - Current progress
- `STATE.json` - Cycle info, evaluation results
- `COMPLETION_REPORT.md` - Final user-facing report

**Demo:**
```bash
python3 examples/supervisor_demo.py
python3 run_supervised.py  # Production usage
```

See `forge/primitives/harness/evaluator.py`, `orchestrator.py`

---

## Phase 4: Advanced Context Janitor ✅ COMPLETE

Enhanced context management with LLM-powered decision extraction and smart compaction.

### AdvancedContextJanitor

**Usage:**
```python
from forge.core.provider import AnthropicProvider
from forge.primitives.harness import AdvancedContextJanitor

janitor = AdvancedContextJanitor(
    agent_id="coding-assistant",
    provider=AnthropicProvider(model="claude-3-haiku-20240307"),  # Cheap model for extraction
    compact_every=10,           # Compact every 10 turns
    max_context_tokens=10000,   # Force compact at 10K tokens
    use_llm_extraction=True     # Use LLM instead of keywords
)

# After each turn
await janitor.after_turn_async(
    agent_response=response.text,
    context_snapshot=full_context  # Optional for size estimation
)

# Check metrics
metrics = janitor.get_metrics()
print(f"Tokens: {metrics.estimated_tokens}, Decisions: {metrics.decisions_extracted}")

# Smart compaction when needed
if janitor.should_compact():
    await janitor.compact_smart()
```

**Key Features:**

1. **LLM-Powered Decision Extraction**
   - Uses cheap model (Haiku) to extract decisions
   - Smarter than keyword matching
   - Costs ~$0.01 per extraction
   - Focuses on technical decisions, ignores noise

2. **Context Size Tracking**
   - Token estimation (chars / 4)
   - Compaction based on size OR turns
   - Prevents context overflow

3. **Smart Compaction**
   - Preserves important context
   - Discards tool output and noise
   - Logs decisions to DECISION_LOG.md
   - Resets context size estimates

4. **Integration with Supervisor**
   ```python
   harness = PlannerWorkerHarness(
       agent_id="coding-assistant",
       planner_provider=sonnet_provider,
       worker_provider=haiku_provider,
       enable_janitor=True,        # Enable advanced janitor
       janitor_compact_every=5,    # Compact every 5 worker steps
       janitor_max_tokens=10000,   # Force compact at 10K tokens
   )

   # Janitor automatically tracks worker responses
   result = await harness.run_supervised_cycle(goals=goals)
   ```

**LLM Extraction Instructions:**

The janitor uses a specialized prompt to extract key decisions:
- **Extracts:** "I decided to...", "I changed X to Y", "Fixed bug in..."
- **Ignores:** Tool output, process descriptions, confirmations
- **Output:** 1-3 key decisions per response

**Context Metrics:**

```python
@dataclass
class ContextMetrics:
    turn_count: int
    estimated_tokens: int
    decisions_extracted: int
    compactions_performed: int
    last_compaction_turn: Optional[int]

    @property
    def turns_since_compaction(self) -> int:
        # Returns turns since last compaction
```

**Comparison: Keyword vs LLM Extraction**

| Response Type | Keyword Extraction | LLM Extraction |
|--------------|-------------------|----------------|
| Clear decision ("I decided...") | ✅ Extracted | ✅ Extracted |
| Implicit decision ("Changed X to Y") | ❌ Missed | ✅ Extracted |
| Noisy response with tool output | ⚠️ Extracts noise | ✅ Filters noise |
| Multiple decisions | ⚠️ Partial | ✅ All extracted |
| Bug fix with reasoning | ⚠️ Partial | ✅ Full context |

**Benefits:**

- **Prevents context bloat** in long-running cycles
- **Uses cheap model** (Haiku) for extraction (~$0.01)
- **Smarter extraction** than keyword matching
- **Automatic compaction** based on size and turns
- **Observable** via DECISION_LOG.md

**Demo:**
```bash
python3 examples/advanced_janitor_demo.py
```

See `forge/primitives/harness/advanced_janitor.py`

---

## Phase 5: Heartbeat Monitoring ✅ COMPLETE

Autonomous oversight with health checks, escalation, and auto cleanup.

### HeartbeatMonitor

**Usage:**
```python
from forge.core.provider import AnthropicProvider
from forge.primitives.harness import (
    PlannerWorkerHarness,
    StuckDetectionCheck,
    ErrorThresholdCheck,
    ProgressRateCheck,
)

# Heartbeat is enabled by default in PlannerWorkerHarness
harness = PlannerWorkerHarness(
    agent_id="coding-assistant",
    planner_provider=sonnet_provider,
    worker_provider=haiku_provider,
    enable_heartbeat=True,           # Enable heartbeat monitoring
    heartbeat_check_every=5,         # Check every 5 turns
    heartbeat_stuck_threshold=10,    # Flag if stuck for 10 turns
    heartbeat_error_threshold=5,     # Flag if 5 consecutive errors
)

# Heartbeat runs automatically during supervised execution
result = await harness.run_supervised_cycle(goals=goals)
```

**Standalone Usage:**
```python
from forge.primitives.harness import (
    HeartbeatMonitor,
    StuckDetectionCheck,
    ErrorThresholdCheck,
    ProgressRateCheck,
    EscalationPolicy,
    CleanupPolicy,
)

# Create custom monitor
monitor = HeartbeatMonitor(
    agent_id="coding-assistant",
    workspace_dir=workspace,
    checks=[
        StuckDetectionCheck(max_turns_without_progress=10),
        ErrorThresholdCheck(max_consecutive_errors=5),
        ProgressRateCheck(min_completion_per_hour=5.0),
    ],
    escalation_policy=EscalationPolicy(
        notify_on_critical=True,
        notify_on_warning=False,
        handlers=[email_handler, slack_handler],
    ),
    cleanup_policy=CleanupPolicy(
        archive_logs_older_than_days=7,
        max_archived_plans=10,
    ),
    check_interval_turns=5,
)

# Run heartbeat check
result = monitor.heartbeat(state=state, progress=progress)

if result["escalations"]:
    print("Issues detected!")
```

**Key Features:**

1. **Health Checks**

   Three built-in checks detect common agent issues:

   **StuckDetectionCheck:**
   - Detects when agent is not making progress
   - Tracks turns since last progress update
   - Flags if stuck for more than threshold turns
   ```python
   StuckDetectionCheck(max_turns_without_progress=10)
   ```

   **ErrorThresholdCheck:**
   - Detects excessive consecutive errors
   - Tracks error count in state
   - Flags if errors exceed threshold
   ```python
   ErrorThresholdCheck(max_consecutive_errors=5)
   ```

   **ProgressRateCheck:**
   - Monitors completion rate over time
   - Calculates % completion per hour
   - Flags if rate too low
   ```python
   ProgressRateCheck(min_completion_per_hour=5.0)
   ```

2. **Escalation Policy**

   Configurable escalation when issues detected:

   ```python
   def email_handler(event: EscalationEvent) -> None:
       send_email(
           to="admin@example.com",
           subject=f"Agent Alert: {event.title}",
           body=event.to_markdown(),
       )

   policy = EscalationPolicy(
       notify_on_critical=True,   # Escalate critical issues
       notify_on_warning=False,   # Don't escalate warnings
       handlers=[email_handler],  # Custom handlers
   )
   ```

   **EscalationEvent includes:**
   - Title and severity (warning/critical)
   - Detailed message about the issue
   - Context (turn number, metrics, etc.)
   - Suggested actions for remediation

3. **Cleanup Policy**

   Automatic workspace maintenance:

   ```python
   policy = CleanupPolicy(
       archive_logs_older_than_days=7,  # Archive logs after 7 days
       max_archived_plans=10,            # Keep max 10 archived plans
       enabled=True,
   )
   ```

   Cleanup runs automatically during heartbeat:
   - Removes oldest archived plans when limit exceeded
   - Archives old decision logs
   - Keeps workspace organized

4. **Health Status**

   Each check returns a `HealthStatus`:

   ```python
   @dataclass
   class HealthStatus:
       healthy: bool
       check_name: str
       message: str
       severity: str  # "info", "warning", "critical"
       data: Optional[dict]
       timestamp: datetime
   ```

**Integration with Supervisor:**

Heartbeat is integrated into `PlannerWorkerHarness.execute_next_step()`:

```python
# Every turn:
# 1. Update turn counter
self.state.update(current_turn=current_turn)

# 2. Execute step
result = await self.worker.execute_current_step()

# 3. Update health metrics
if result.success:
    self.state.save(
        consecutive_errors=0,
        last_progress_turn=current_turn,
    )
else:
    consecutive_errors = self.state.get("consecutive_errors", 0) + 1
    self.state.save(
        consecutive_errors=consecutive_errors,
        last_error=result.error,
    )

# 4. Run heartbeat check if interval reached
if self.heartbeat and self.heartbeat.should_run_heartbeat(current_turn):
    heartbeat_result = self.heartbeat.heartbeat(
        state=self.state,
        progress=self.worker.progress,
    )
```

**Escalation Example:**

When stuck agent detected:

```markdown
# ⚠️ Agent Health Issue: stuck_detection

**Severity:** CRITICAL

**Time:** 2024-03-27 14:30:00

## Issue

Agent stuck: 12 turns without progress

## Context

- **agent_id:** coding-assistant
- **check_name:** stuck_detection
- **turns_stuck:** 12
- **max_allowed:** 10
- **last_progress_turn:** 5
- **current_turn:** 17

## Suggested Actions

1. Review PROGRESS.md to see what task the agent is stuck on
2. Check DECISION_LOG.md for repeated patterns
3. Consider providing additional context or breaking down the task
4. Reset agent and start with clearer goals
```

**Benefits:**

- **Early detection** of agent issues before wasting resources
- **Actionable alerts** with context and suggested fixes
- **Autonomous operation** - runs without human intervention
- **Configurable** thresholds per agent type
- **Observable** - all checks logged
- **Automatic cleanup** maintains workspace

**Demo:**
```bash
python3 examples/heartbeat_demo.py
```

See `forge/primitives/harness/heartbeat.py`

---

## References

- **Harness Engineering Analysis:** `/docs/HARNESS_ENGINEERING_ANALYSIS.md`
- **Anthropic Principles:** Based on internal Harness Engineering documentation
- **OpenClaw Influence:** Simple artifact-driven execution (HEARTBEAT.md)

---

## License

Part of the Forge Agent framework.

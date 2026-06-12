# Daemon Architecture Explained

## Summary

**No, Planner and Worker do NOT each have their own daemon.**

There is **ONE AgentDaemon per agent instance**, regardless of whether that agent uses:
- Basic Agent pattern (simple loop)
- PlannerWorkerHarness pattern (two-phase workflow)

Planner and Worker are **internal components** of an execution pattern, not separate agent instances.

---

## The Three Architectural Layers

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: Process Management (Per Agent Instance)           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AgentDaemon (formerly HeartbeatDaemon)                     │
│  - ONE daemon per agent instance                            │
│  - Manages task queue (CRITICAL → LOW priority)            │
│  - Manages mission schedule (HOURLY, DAILY, WEEKLY)        │
│  - Calls agent_executor when work is available             │
│  - Runs continuously in background                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ (invokes)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: Execution Pattern (How Work Gets Done)            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Choose ONE pattern:                                        │
│                                                             │
│  ┌──────────────────────────┐  OR  ┌────────────────────┐ │
│  │ Basic Agent              │      │ PlannerWorkerHarness│ │
│  │ - Simple LLM loop        │      │ - Planner component │ │
│  │ - Direct execution       │      │ - Worker component  │ │
│  │ - Fast & simple          │      │ - Two-phase workflow│ │
│  └──────────────────────────┘      └────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ (uses)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: Safety Features (Shared by All Patterns)          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  - CostTracker (budget enforcement)                         │
│  - AuditLogger (compliance trail)                           │
│  - HeartbeatMonitor (health checks during execution)       │
│  - CheckpointManager (git rollback)                         │
│  - StateManager (persistent state)                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: AgentDaemon (Process Management)

### Purpose
**Orchestrates WHEN and WHAT an agent executes**

### Scope
- ONE daemon per agent instance
- Runs continuously (background process)
- Lives at the OS process level
- PID file, signal handling, graceful shutdown

### Responsibilities
1. **Task Queue Management**
   - Poll task database every N seconds
   - Execute tasks by priority: CRITICAL → HIGH → MEDIUM → LOW
   - Interrupt running missions for CRITICAL tasks

2. **Mission Scheduling**
   - Check if scheduled missions are due (HOURLY, DAILY, WEEKLY)
   - Execute on schedule
   - Track mission state (PENDING → RUNNING → COMPLETED)

3. **Service Registration** (optional)
   - Register with resolution service for agent discovery
   - Announce capabilities
   - Enable cross-agent coordination

4. **Lifecycle Management**
   - Graceful shutdown on SIGTERM
   - PID file management
   - Error recovery

### Example
```python
from forge.daemon import AgentDaemon, create_simple_executor

# Create executor (LAYER 2 - execution pattern)
executor = create_simple_executor(
    provider=AnthropicProvider(),
    workspace_dir=Path("~/.teotl/agents/email-bot"),
)

# Create daemon (LAYER 1 - process management)
daemon = AgentDaemon(
    agent_id="email-bot",
    agent_executor=executor,  # Can use ANY executor pattern
    poll_interval=10,  # Check for work every 10 seconds
)

# Run daemon (blocks until stopped)
await daemon.start()
```

**Key Point:** The daemon doesn't care WHAT execution pattern you use (basic Agent or PlannerWorkerHarness). It just calls `agent_executor(description, context)` when work is available.

---

## Layer 2: Execution Patterns

### Pattern A: Basic Agent (Simple)
```python
┌────────────────────────────┐
│  Basic Agent               │
│  - Single LLM loop         │
│  - Direct tool execution   │
│  - Fast & straightforward  │
└────────────────────────────┘
```

**When to use:**
- Simple tasks
- Quick operations
- Development/testing
- Cost-conscious (one model call)

### Pattern B: PlannerWorkerHarness (Advanced)
```python
┌────────────────────────────────────┐
│  PlannerWorkerHarness              │
│                                    │
│  ┌──────────┐    ┌──────────┐    │
│  │ Planner  │───▶│ Worker   │    │
│  │ (Sonnet) │    │ (Haiku)  │    │
│  └──────────┘    └──────────┘    │
│                                    │
│  Phase 1:         Phase 2:        │
│  Create plan      Execute steps   │
│  (runs ONCE)      (runs MANY)     │
└────────────────────────────────────┘
```

**When to use:**
- Complex multi-step tasks
- Want cost savings (93-97% via Haiku worker)
- Need reliable execution (atomic steps)
- Observable progress (PLAN.md, PROGRESS.md)

**Key Point:** Planner and Worker are NOT separate agent instances. They are internal components that share:
- The same workspace
- The same cost tracker
- The same audit logger
- The same state manager
- The same heartbeat monitor

---

## Layer 3: Safety Features (HeartbeatMonitor)

### Purpose
**Monitors agent health DURING execution**

### Scope
- Runs INSIDE agent execution
- One monitor per agent (shared by Planner and Worker if using harness)
- Activated only during task execution, not continuously

### Responsibilities
1. **Stuck Detection**
   - No progress for N turns → escalate

2. **Error Threshold**
   - N consecutive errors → escalate

3. **Progress Rate**
   - Completion rate too low → escalate

4. **Workspace Cleanup**
   - Archive old logs
   - Rotate files
   - Maintain clean workspace

### Example
```python
# HeartbeatMonitor runs INSIDE the agent during execution

agent = Agent(
    provider=...,
    heartbeat_monitor=HeartbeatMonitor(
        checks=[
            StuckDetectionCheck(max_turns_without_progress=10),
            ErrorThresholdCheck(max_consecutive_errors=5),
        ],
    ),
)

# During agent.run(), the monitor checks health periodically
result = await agent.run("Do task")
# Monitor detected: "Stuck for 10 turns" → escalates to user
```

**Key Point:** HeartbeatMonitor is a safety feature at the execution level, not a process orchestrator.

---

## Detailed Example: Email Bot with PlannerWorkerHarness

Let's trace a complete example:

```python
from forge.daemon import AgentDaemon, create_simple_executor
from forge.core.provider import AnthropicProvider
from pathlib import Path

# LAYER 2: Create execution pattern (PlannerWorkerHarness)
from forge.primitives.harness.orchestrator import PlannerWorkerHarness

workspace = Path("~/.teotl/agents/email-bot")

harness = PlannerWorkerHarness(
    agent_id="email-bot",
    planner_provider=AnthropicProvider("claude-3-5-sonnet-20241022"),
    worker_provider=AnthropicProvider("claude-3-haiku-20240307"),
    workspace_dir=workspace,
    # LAYER 3: Enable safety features
    enable_cost_tracking=True,
    enable_heartbeat=True,  # ← HeartbeatMonitor (health checks)
)

# Create executor function that wraps the harness
async def harness_executor(description: str, context: dict) -> str:
    """Executor that uses PlannerWorkerHarness pattern."""
    # Create plan
    plan = await harness.plan(goals=description)

    # Execute plan
    while not harness.is_complete():
        result = await harness.execute_next_step()
        if not result.success:
            break

    # Return final evaluation
    evaluation = await harness.evaluate()
    return evaluation.summary

# LAYER 1: Create daemon (process management)
daemon = AgentDaemon(
    agent_id="email-bot",
    agent_executor=harness_executor,  # Uses PlannerWorkerHarness pattern
    poll_interval=10,
)

# Start daemon - it will:
# 1. Poll for tasks/missions every 10 seconds
# 2. When work arrives, call harness_executor()
# 3. Harness uses Planner + Worker internally
# 4. Both Planner and Worker share the HeartbeatMonitor
await daemon.start()
```

### What happens when a task arrives:

```
1. AgentDaemon detects task in queue
   ↓
2. Calls harness_executor("Process inbox", {})
   ↓
3. PlannerWorkerHarness.plan() is called
   ↓
4. Planner (internal component) creates plan
   - Planner.agent has HeartbeatMonitor
   - During planning, monitor checks health
   ↓
5. PlannerWorkerHarness.execute_next_step() called N times
   ↓
6. Worker (internal component) executes each step
   - Worker.agent has HeartbeatMonitor (SAME instance as Planner)
   - During execution, monitor checks health
   ↓
7. Returns result to AgentDaemon
   ↓
8. AgentDaemon marks task complete, continues polling
```

**Key Insight:** There is still only ONE daemon, even though the execution pattern uses two internal components (Planner and Worker).

---

## Common Misconceptions

### ❌ Misconception: "Each agent has its own daemon"
**Reality:** Each agent **instance** has its own daemon. If you run multiple agents, each gets a daemon.

### ❌ Misconception: "Planner and Worker each have their own daemon"
**Reality:** Planner and Worker are internal components, not agent instances. They share ONE daemon.

### ❌ Misconception: "HeartbeatMonitor is the same as AgentDaemon"
**Reality:**
- **AgentDaemon** = Process orchestrator (WHEN to work)
- **HeartbeatMonitor** = Health monitor (IS work healthy)

---

## Multi-Agent Setup Example

If you want multiple agents, each gets its own daemon:

```python
# Agent 1: Email bot with basic pattern
email_executor = create_simple_executor(
    provider=AnthropicProvider(),
    workspace_dir=Path("~/.teotl/agents/email-bot"),
)

email_daemon = AgentDaemon(
    agent_id="email-bot",
    agent_executor=email_executor,
)

# Agent 2: Code assistant with PlannerWorkerHarness pattern
code_harness = PlannerWorkerHarness(
    agent_id="code-assistant",
    planner_provider=AnthropicProvider("claude-3-5-sonnet-20241022"),
    worker_provider=AnthropicProvider("claude-3-haiku-20240307"),
    workspace_dir=Path("~/.teotl/agents/code-assistant"),
)

async def code_executor(description: str, context: dict) -> str:
    plan = await code_harness.plan(goals=description)
    # ... execute plan
    return result

code_daemon = AgentDaemon(
    agent_id="code-assistant",
    agent_executor=code_executor,
)

# Run both daemons (different processes or asyncio tasks)
await asyncio.gather(
    email_daemon.start(),  # Daemon 1
    code_daemon.start(),   # Daemon 2
)
```

**Result:**
- 2 agent instances
- 2 daemons (one per instance)
- 2 different execution patterns (basic vs harness)
- Both can use the same safety features (Layer 3)

---

## Summary Table

| Component | Layer | Scope | Purpose | Count |
|-----------|-------|-------|---------|-------|
| **AgentDaemon** | 1 | Agent instance | Process orchestration, scheduling | 1 per agent instance |
| **Basic Agent** | 2 | Execution | Simple LLM loop | 0 or 1 per daemon |
| **PlannerWorkerHarness** | 2 | Execution | Two-phase workflow | 0 or 1 per daemon |
| **Planner** | 2 | Component | Create plan (expensive model) | Part of harness if used |
| **Worker** | 2 | Component | Execute steps (cheap model) | Part of harness if used |
| **HeartbeatMonitor** | 3 | Safety | Health checks during execution | Shared by all components |
| **CostTracker** | 3 | Safety | Budget enforcement | Shared by all components |
| **AuditLogger** | 3 | Safety | Compliance trail | Shared by all components |

---

## Renamed Files

To reduce confusion, we renamed:

**Before:**
- `forge/daemon/heartbeat.py` → `HeartbeatDaemon` (confusing with monitor)
- `forge/primitives/harness/heartbeat.py` → `HeartbeatMonitor`

**After:**
- `forge/daemon/agent_daemon.py` → `AgentDaemon` (clear purpose)
- `forge/primitives/harness/heartbeat.py` → `HeartbeatMonitor` (unchanged)

**Backward compatibility:** `HeartbeatDaemon` still works as an alias for `AgentDaemon`.

---

## Final Answer to Your Question

> "Since each has its own daemon, the Planner and Worker are each independent agents?"

**No.** The architecture is:

```
ONE AgentDaemon
  └─ Uses ONE execution pattern
      ├─ EITHER: Basic Agent (one component)
      └─ OR: PlannerWorkerHarness (two internal components)
          ├─ Planner (internal)
          └─ Worker (internal)
```

Planner and Worker are **not independent agents**. They are:
- Internal components of a two-phase execution pattern
- Share the same workspace, cost tracker, state, monitor
- Coordinated by PlannerWorkerHarness
- Called sequentially (plan once → execute many steps)
- Run within the same daemon/process

**Only if you want to run Planner and Worker as SEPARATE agent instances** (which would be unusual) would you create two daemons. But that's not the intended design.

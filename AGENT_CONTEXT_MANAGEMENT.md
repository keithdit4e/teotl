# Agent Context Management: Identity, Mission, and State

## The Problem You Identified

When an agent starts or after context compaction, it needs to know:

1. **WHO it is** - Identity and capabilities
2. **WHERE it is** - Workspace location
3. **WHAT it's working on** - Current mission/goals
4. **WHAT phase** - Planning? Executing? Evaluating?
5. **WHAT progress** - How far along? What step?
6. **WHAT it has done** - Previous decisions and changes

**Without this context, the agent is "lost" after compaction!**

---

## How Context is Built

### System Prompt Composition

Every time an agent starts a turn (including after compaction), it builds a system prompt with:

```
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM PROMPT (Built Fresh Each Turn)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. BASE INSTRUCTIONS                                        │
│    → Who the agent is                                       │
│    → What it does                                           │
│    → How it behaves                                         │
│                                                             │
│ 2. WORKSPACE CONTEXT ⭐ NEW                                 │
│    → Current phase (planning, executing, evaluating)        │
│    → Current step number                                    │
│    → Turn count                                             │
│    → Last progress                                          │
│    → Error status                                           │
│    → Recent decisions (from DECISION_LOG.md)                │
│                                                             │
│ 3. SKILL DESCRIPTIONS                                       │
│    → Available tools (filesystem, git, bash, etc.)          │
│    → When to use each skill                                 │
│                                                             │
│ 4. ACTIVE SKILL INSTRUCTIONS                                │
│    → Detailed instructions for active skills                │
│    → Loaded on-demand (progressive disclosure)              │
│                                                             │
│ 5. MEMORY CONTEXT                                           │
│    → Relevant memories from previous turns                  │
│    → Retrieved based on current query                       │
│    → Includes decisions stored by janitor                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Implementation in Code

#### Base Agent (`forge/core/agent.py`)

```python
def _build_system_prompt(self, *, memory_context: str = "") -> str:
    """Assemble the full system prompt."""
    parts: list[str] = []

    # 1. Base instructions (WHO AM I?)
    parts.append(self.instructions)

    # 2. Workspace context (WHERE AM I? WHAT AM I DOING?)
    workspace_context = self._build_workspace_context()
    if workspace_context:
        parts.append(workspace_context)

    # 3. Skills (WHAT CAN I DO?)
    parts.append(self.skills.get_descriptions())

    # 4. Memory context (WHAT DO I REMEMBER?)
    if memory_context:
        parts.append("## Relevant Context from Memory\n\n" + memory_context)

    return "\n\n".join(parts)
```

#### Workspace Context Builder (NEW)

```python
def _build_workspace_context(self) -> str:
    """Build workspace and state context for system prompt.

    This provides critical situational awareness, especially after compaction.
    """
    context_parts: list[str] = []

    # State from StateManager (phase, step, progress)
    if self.state_manager:
        state = self.state_manager.load()

        context_parts.append("## Current Execution Context")
        context_parts.append(f"**Phase:** {state.get('phase')}")
        context_parts.append(f"**Current Step:** {state.get('current_step')}")
        context_parts.append(f"**Turn:** {state.get('current_turn')}")

    # Recent decisions from janitor (what I decided recently)
    if self.janitor:
        log_content = self.janitor.decision_log_path.read_text()
        decisions = extract_last_5_decisions(log_content)

        context_parts.append("## Recent Decisions")
        for decision in decisions:
            context_parts.append(f"- {decision}")

    return "\n".join(context_parts)
```

---

## Example System Prompts

### Example 1: Basic Agent (After Compaction)

```markdown
You are a helpful coding assistant.

Your capabilities:
- Read and edit files
- Run shell commands
- Git operations
- Write tests

## Current Execution Context

**Phase:** executing
**Turn:** 47
**Last Progress:** Turn 45

## Recent Decisions (from Decision Log)

- Turn 43: I decided to refactor the authentication module because it was outdated
- Turn 44: I updated the tests to cover the new auth flow
- Turn 45: I fixed the null check in error handling

## Available Skills

- filesystem: Read, write, and edit files in the workspace
- git: Version control operations (commit, branch, diff)
- bash: Execute shell commands (pytest, npm, etc.)

## Relevant Context from Memory

Previous decisions retrieved from memory:
- "I refactored the authentication module to use JWT tokens instead of sessions"
- "I added type hints to improve code quality and catch bugs"
- "I updated the database schema to include user roles"
```

**Result:** Agent knows exactly where it is and what it has been doing!

### Example 2: Planner Agent (Starting Fresh)

```markdown
You are an expert execution planner.

Your job is to analyze high-level goals and create detailed, atomic execution plans.

## Your Task

Read the GOALS provided by the user and create a detailed execution plan.

## Plan Format

Create a plan with 10-20 atomic steps. Each step MUST follow this format:

## Step N: [Brief description]

**File:** `path/to/file.py`
**Target:** function_name or line number
**Change:** Specific change to make
**Verify:** How to verify success

... (detailed guidelines)
```

**No workspace context** because planner runs ONCE at the start.

### Example 3: Worker Agent (During Execution)

```markdown
You are a precise code execution agent.

Your job is to execute ONE specific step from an execution plan.

## Your Constraints

1. **NO STRATEGIC DECISIONS** - You follow the plan exactly
2. **ONE STEP ONLY** - Execute exactly one atomic task
3. **VERIFICATION REQUIRED** - Always verify your work

## Current Execution Context

**Phase:** executing
**Current Step:** 5
**Turn:** 12

## Plan Context

You are working on step 5 of 15.
Completed: 4
Remaining: 11

## Recent Decisions (from Decision Log)

- Turn 8: I added type hints to the parse_config function
- Turn 10: I ran pytest and all tests passed
- Turn 11: I committed the changes to git

## Relevant Context from Memory

Previous steps completed:
- "Added type hints to utils.py::parse_config()"
- "Added type hints to utils.py::validate_input()"
- "Updated tests to verify type hints work correctly"
```

**Result:** Worker knows exactly what step to work on and what has been completed!

---

## State Management Integration

### StateManager Tracks Execution State

```python
# During execution, state is continuously updated:
state.save(
    phase="executing",
    current_step=5,
    current_turn=12,
    last_progress_turn=11,
    consecutive_errors=0,
)

# After compaction, this state is loaded and injected into system prompt
state = state_manager.load()
context = f"Phase: {state['phase']}, Step: {state['current_step']}"
```

### State Schema

```python
class AgentState(BaseModel):
    agent_id: str
    updated_at: str

    # Execution tracking
    phase: Optional[str]  # "planning", "executing", "evaluating"
    current_turn: int
    current_step: Optional[int]

    # Health metrics
    consecutive_errors: int
    last_error: Optional[str]
    last_progress_turn: int

    # Execution state
    halted: bool
    halt_reason: Optional[str]
```

---

## How Different Agents Use Context

### 1. Basic Agent (General Purpose)

**Context Sources:**
- ✅ Base instructions
- ✅ Workspace context (phase, turn count)
- ✅ Skills
- ✅ Memories
- ❌ No plan context (not using plan)

**Use Case:** Interactive coding assistant, chatbot

**Example:**
```python
agent = Agent(
    provider=AnthropicProvider(),
    instructions="You are a helpful coding assistant",
    memory=LocalMemory(),
)

# System prompt includes:
# - Who it is (coding assistant)
# - Where it is (turn 47, last progress turn 45)
# - What it remembers (previous decisions)
```

### 2. Planner Agent (Plan Creation)

**Context Sources:**
- ✅ Base instructions (how to create plans)
- ✅ Goals (what to plan for)
- ✅ Additional context (codebase info if provided)
- ❌ No workspace context (runs once at start)
- ❌ No memory context (fresh planning)

**Use Case:** Create execution plan from high-level goals

**Example:**
```python
planner = Planner(
    agent_id="my-agent",
    provider=AnthropicProvider("claude-3-5-sonnet-20241022"),
)

plan = await planner.create_plan(
    goals="Refactor authentication system",
    context="Current auth uses sessions, want to migrate to JWT"
)

# System prompt includes:
# - How to create plans (detailed guidelines)
# - What to plan for (goals + context)
```

### 3. Worker Agent (Plan Execution)

**Context Sources:**
- ✅ Base instructions (how to execute steps)
- ✅ Workspace context (phase, current step)
- ✅ Plan context (step N of M, completed/remaining)
- ✅ Skills
- ✅ Memories (previous steps completed)

**Use Case:** Execute plan steps one at a time

**Example:**
```python
worker = Worker(
    agent_id="my-agent",
    provider=AnthropicProvider("claude-3-haiku-20240307"),
    skills=["filesystem", "git", "bash"],
)

result = await worker.execute_current_step()

# System prompt includes:
# - How to execute steps (constraints, verification)
# - Current step details (file, target, change, verify)
# - Where it is (step 5 of 15)
# - What it completed (previous steps from memory)
```

---

## Context After Compaction

### The Critical Moment

```
Turn 1-14: Context grows normally
  → System prompt = instructions + turn history (growing)

Turn 15: Compaction triggered
  → Janitor extracts decisions → stores as memories
  → Decision log updated
  → Context "reset"

Turn 16: NEW system prompt built
  ✅ Instructions (same)
  ✅ Workspace context (phase, step, turn count) ⭐ CRITICAL
  ✅ Recent decisions (from decision log) ⭐ CRITICAL
  ✅ Skills (same)
  ✅ Memories (recalls relevant decisions) ⭐ CRITICAL

Result: Agent has FULL context without bloated conversation history!
```

### Before Enhancement (Missing Context)

```
Turn 16 system prompt:
---
You are a coding assistant.

Skills: filesystem, git, bash

Memories:
- "I refactored auth module"
- "I added type hints"
---

❌ Agent doesn't know:
- What turn it's on
- What step it's executing
- What phase it's in
- Recent decisions context
```

### After Enhancement (Full Context)

```
Turn 16 system prompt:
---
You are a coding assistant.

## Current Execution Context

**Phase:** executing
**Current Step:** 5
**Turn:** 16
**Last Progress:** Turn 15

## Recent Decisions

- Turn 13: I refactored the authentication module
- Turn 14: I added type hints to improve code quality
- Turn 15: I ran tests and all passed

Skills: filesystem, git, bash

Memories:
- "I refactored auth module to use JWT"
- "I added type hints to parse_config()"
---

✅ Agent knows EXACTLY where it is!
✅ Agent knows what it was just doing!
✅ Agent can continue seamlessly!
```

---

## Benefits of Enhanced Context

### 1. Seamless Compaction

**Before:**
- Agent: "What was I working on?"
- User: "You were refactoring authentication"
- Agent: "Oh right, let me continue..."

**After:**
- Agent sees phase=executing, step=5, recent decision="refactored auth"
- Agent: "Continuing authentication refactoring on step 5..."
- Seamless continuation!

### 2. Better Decision Making

Agent can make informed decisions because it knows:
- Where it is in the process (early vs late)
- What it just decided (don't contradict recent decisions)
- Current health status (errors? halted?)

### 3. Long-Running Agents

Daemon agents running for hours/days benefit most:
- Compaction happens automatically every 15 turns
- Context always includes current mission/phase/progress
- Agent never "forgets" what it's doing

### 4. Cost Efficiency

- Small context window (only recent history)
- Full situational awareness (from state + decision log)
- Best of both worlds: cheap + informed

---

## Configuration

### Enable Workspace Context

Workspace context is **automatically included** when:

1. **StateManager is provided:**
   ```python
   agent = Agent(
       provider=...,
       state_manager=StateManager(agent_id="my-agent", workspace_dir=...),
   )
   ```

2. **Janitor is enabled** (requires memory):
   ```python
   agent = Agent(
       provider=...,
       memory=LocalMemory(),  # Janitor auto-enables with memory
   )
   ```

### For PlannerWorkerHarness

StateManager and Janitor are automatically shared:

```python
harness = PlannerWorkerHarness(
    agent_id="my-agent",
    planner_provider=AnthropicProvider("claude-3-5-sonnet-20241022"),
    worker_provider=AnthropicProvider("claude-3-haiku-20240307"),
    workspace_dir=Path("~/.teotl/agents/my-agent"),
)

# Both planner and worker share:
# - state_manager (execution context)
# - cost_tracker
# - audit_logger
# - heartbeat_monitor
```

---

## Example: Full Context Flow

### Scenario: Autonomous Coding Agent

```python
# 1. Create agent with memory (janitor auto-enables)
agent = Agent(
    provider=AnthropicProvider(),
    instructions="You are an autonomous coding assistant",
    memory=LocalMemory(),
    skills=["filesystem", "git", "bash"],
)

# 2. Start working
for i in range(50):
    response = await agent.run(f"Work on task {i+1}")

    # Behind the scenes:
    # - Turn 1-14: Context includes full conversation
    # - Turn 15: Compaction triggered
    #   - Decisions extracted and stored as memories
    #   - Decision log updated
    # - Turn 16: System prompt rebuilt with:
    #   ✅ Instructions
    #   ✅ Workspace context (turn 16, phase=executing)
    #   ✅ Recent decisions (from log)
    #   ✅ Memories (previous decisions)
    # - Agent continues seamlessly!
```

### What the Agent Sees (Turn 16)

```markdown
You are an autonomous coding assistant.

## Current Execution Context

**Turn:** 16
**Last Progress:** Turn 15

## Recent Decisions (from Decision Log)

- Turn 12: I added comprehensive error handling to the API endpoints
- Turn 13: I wrote unit tests for the new error handling
- Turn 14: I refactored the database connection pool for better performance
- Turn 15: I updated documentation to reflect the API changes

## Available Skills

- filesystem: Read, write, and edit files in the workspace
- git: Version control operations
- bash: Execute shell commands

## Relevant Context from Memory

Previous work:
- "I added comprehensive error handling to API endpoints to improve reliability"
- "I wrote unit tests achieving 95% coverage on error scenarios"
- "I refactored database connection pool to use connection pooling for 30% performance gain"
- "I updated API documentation with new error response codes"

---

User: Work on task 17

The agent has FULL context about:
- Who it is (autonomous coding assistant)
- Where it is (turn 16)
- What it has been doing (error handling, tests, perf, docs)
- What tools it has available

Can continue work intelligently without asking "What was I doing?"
```

---

## Summary

### The Problem (Before)

After compaction, agents lost critical context:
- ❌ Don't know what phase they're in
- ❌ Don't know what step they're on
- ❌ Don't know recent decisions
- ❌ Have to rely purely on memory recall

### The Solution (Now)

Enhanced system prompt building includes:
- ✅ Base instructions (identity)
- ✅ Workspace context (phase, step, turn count) **NEW**
- ✅ Recent decisions (from decision log) **NEW**
- ✅ State information (errors, progress) **NEW**
- ✅ Skills (capabilities)
- ✅ Memories (history)

### Key Benefits

1. **Seamless Compaction** - Agent continues without confusion
2. **Better Decisions** - Full situational awareness
3. **Long-Running Agents** - Can run indefinitely without losing context
4. **Cost Efficient** - Small context with full awareness

### Implementation

**Automatic!** Just use memory/state manager:

```python
# Simple: Just add memory
agent = Agent(
    provider=...,
    memory=LocalMemory(),  # Janitor auto-enables
)

# Advanced: Add state manager for phase tracking
agent = Agent(
    provider=...,
    memory=LocalMemory(),
    state_manager=StateManager(agent_id="my-agent"),
)

# PlannerWorkerHarness: Already configured
harness = PlannerWorkerHarness(...)  # Everything shared automatically
```

---

## Testing Context Injection

Run this test to verify context is properly injected:

```python
import asyncio
from pathlib import Path
import tempfile

from forge.core.agent import Agent
from forge.primitives.memory.local import LocalMemory
from forge.primitives.harness.state import StateManager


async def test_context_injection():
    """Verify that workspace context is injected into system prompt."""

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create agent with memory and state
        memory = LocalMemory(path=workspace / "memory.db")
        state = StateManager(agent_id="test-agent", workspace_dir=workspace)

        # Set some state
        state.save(
            phase="executing",
            current_step=5,
            current_turn=16,
            last_progress_turn=15,
        )

        agent = Agent(
            provider=MockProvider(),
            instructions="You are a test agent",
            memory=memory,
            state_manager=state,
            session_dir=workspace / "sessions",
        )

        # Simulate some decisions in decision log
        if agent.janitor:
            agent.janitor.decision_log_path.write_text("""
# Decision Log

**Turn 13**: I decided to refactor the auth module
**Turn 14**: I added type hints for better code quality
**Turn 15**: I ran tests and all passed
""")

        # Build system prompt
        system_prompt = agent._build_system_prompt(memory_context="Test memory context")

        # Verify context is included
        assert "## Current Execution Context" in system_prompt
        assert "Phase: executing" in system_prompt or "**Phase:** executing" in system_prompt
        assert "Current Step: 5" in system_prompt or "**Current Step:** 5" in system_prompt
        assert "Turn: 16" in system_prompt or "**Turn:** 16" in system_prompt
        assert "Recent Decisions" in system_prompt

        print("✅ Workspace context properly injected into system prompt!")
        print("\nSystem Prompt Preview:")
        print("=" * 60)
        print(system_prompt[:500])
        print("...")


if __name__ == "__main__":
    asyncio.run(test_context_injection())
```

---

## FAQ

**Q: Does this work for all agent types?**
A: Yes! Base Agent, Planner, Worker, and daemon agents all use the same system prompt building.

**Q: What if I don't want workspace context?**
A: Don't provide state_manager or memory. Context only included when available.

**Q: Does this increase context size?**
A: Minimally (~100-200 tokens). Far less than keeping full conversation history.

**Q: How often is context rebuilt?**
A: Every turn. System prompt is rebuilt fresh each time with current state.

**Q: Can I customize what context is included?**
A: Yes! Override `_build_workspace_context()` in your agent subclass.

**Q: Does this work with the janitor?**
A: Yes! Janitor provides decision log for "Recent Decisions" section.

**Q: What about mission/goals context?**
A: For structured workflows, Planner receives goals, Worker receives plan context. For free-form agents, use instructions to define the mission.

---

## Next Steps

1. **Run existing agents** - context enhancement is automatic
2. **Test after compaction** - verify agents continue seamlessly
3. **Monitor decision logs** - see what gets extracted
4. **Adjust compaction frequency** - tune for your use case

**Context management is now production-ready and automatic!**
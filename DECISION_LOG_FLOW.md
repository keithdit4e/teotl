# Decision Log Flow: How Agent Reads and Writes

## The Question

**How does the base agent work with decision log? Does agent write and read?**

**Answer:** Agent **reads directly** but **writes indirectly** through the Janitor.

---

## The Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Turn 1-14: Agent executes, Janitor watches                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. User: "Refactor the authentication system"             │
│     ↓                                                       │
│  2. Agent.run() → generates response                        │
│     ↓                                                       │
│  3. Agent response:                                         │
│     "I decided to refactor the auth module because         │
│      it was outdated. I changed it to use JWT tokens."     │
│     ↓                                                       │
│  4. Janitor.after_turn(response) [AUTOMATIC]               │
│     ↓                                                       │
│  5. Janitor extracts decision:                             │
│     "I decided to refactor the auth module because..."     │
│     ↓                                                       │
│  6. Janitor stores in BUFFER (not yet written to file)     │
│     decision_buffer = [Decision(...)]                      │
│     ↓                                                       │
│  7. Check: should_compact()?                               │
│     - Turn count: 3 % 15 ≠ 0 → NO                          │
│     - Token count: 2,000 < 100,000 → NO                    │
│     → Continue to next turn                                 │
│                                                             │
│  Repeat for turns 2-14...                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Turn 15: Compaction Triggered                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Agent generates response (turn 15)                      │
│     ↓                                                       │
│  2. Janitor.after_turn(response)                           │
│     ↓                                                       │
│  3. Extract decision, add to buffer                         │
│     decision_buffer = [Decision(turn=1), ..., Decision(turn=15)]
│     ↓                                                       │
│  4. Check: should_compact()?                               │
│     - Turn count: 15 % 15 = 0 → YES! ✅                    │
│     ↓                                                       │
│  5. Janitor.compact() [WRITES TO FILE] ⭐                   │
│     ↓                                                       │
│  6. JANITOR WRITES TO DECISION_LOG.md:                     │
│                                                             │
│     ┌─────────────────────────────────────────┐            │
│     │ # Decision Log                          │            │
│     │                                         │            │
│     │ ## Turns 1-15                           │            │
│     │                                         │            │
│     │ Compacted: 2024-01-15T10:32:45          │            │
│     │                                         │            │
│     │ **Turn 3**: I decided to refactor...   │            │
│     │ **Turn 7**: I fixed the null check...  │            │
│     │ **Turn 12**: I updated the tests...    │            │
│     │ **Turn 15**: I committed the changes...│            │
│     │                                         │            │
│     │ ---                                     │            │
│     └─────────────────────────────────────────┘            │
│     ↓                                                       │
│  7. Clear decision buffer                                  │
│     decision_buffer = []                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Turn 16: Agent Reads Decision Log                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. User: "Continue working"                               │
│     ↓                                                       │
│  2. Agent.run() starts                                      │
│     ↓                                                       │
│  3. Agent._build_system_prompt() [BUILD PROMPT]            │
│     ↓                                                       │
│  4. Agent._build_workspace_context() [READS FILE] ⭐        │
│     ↓                                                       │
│  5. AGENT READS DECISION_LOG.md:                           │
│     log_content = self.janitor.decision_log_path.read_text()
│     ↓                                                       │
│  6. Extract last 5 decisions:                              │
│     decisions = ["I decided to refactor...",               │
│                  "I fixed the null check...",              │
│                  "I updated the tests...",                 │
│                  "I committed the changes..."]             │
│     ↓                                                       │
│  7. Include in system prompt:                              │
│                                                             │
│     ┌─────────────────────────────────────────┐            │
│     │ You are a coding assistant.             │            │
│     │                                         │            │
│     │ ## Current Execution Context            │            │
│     │                                         │            │
│     │ **Turn:** 16                            │            │
│     │ **Last Progress:** Turn 15              │            │
│     │                                         │            │
│     │ ## Recent Decisions                     │            │
│     │                                         │            │
│     │ - I decided to refactor the auth module │            │
│     │ - I fixed the null check in parser      │            │
│     │ - I updated the tests to verify changes │            │
│     │ - I committed the changes to git        │            │
│     └─────────────────────────────────────────┘            │
│     ↓                                                       │
│  8. Agent generates response WITH CONTEXT                   │
│     → Agent knows what it did in previous turns!           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Code Breakdown

### 1. Agent WRITES (Indirectly via Janitor)

**Location:** `forge/core/agent.py` in `agent.run()`

```python
# After agent generates response
if self.janitor:
    # Process turn (extracts decisions, stores as memories)
    await self.janitor.after_turn(result.content, context_snapshot)

    # Check if context should be compacted
    if self.janitor.should_compact():
        # Compact context (logs decisions to DECISION_LOG.md)
        self.janitor.compact()  # ← JANITOR WRITES TO FILE
```

**The agent doesn't write directly!** It just calls `janitor.compact()` which does the writing.

### 2. Janitor WRITES (The Actual Writing)

**Location:** `forge/primitives/harness/janitor.py` in `compact()`

```python
def compact(self) -> None:
    """Compact context by logging decisions and signaling reset."""
    if not self.decision_buffer:
        return

    # WRITE TO DECISION_LOG.md
    with open(self.decision_log_path, "a") as f:  # ← APPEND MODE
        start_turn = self.turn_count - self.compact_every + 1
        end_turn = self.turn_count

        f.write(f"\n## Turns {start_turn}-{end_turn}\n\n")
        f.write(f"Compacted: {datetime.now().isoformat()}\n\n")

        for decision in self.decision_buffer:
            timestamp_str = decision.timestamp.strftime("%H:%M:%S")
            f.write(f"**Turn {decision.turn}** ({timestamp_str}): {decision.decision}\n\n")

        f.write("---\n\n")

    # Clear decision buffer
    self.decision_buffer = []
```

**This is the ONLY place DECISION_LOG.md is written to!**

### 3. Agent READS (Directly)

**Location:** `forge/core/agent.py` in `_build_workspace_context()`

```python
def _build_workspace_context(self) -> str:
    """Build workspace and state context for system prompt."""
    context_parts: list[str] = []

    # ... state manager context ...

    # Janitor provides decision log context
    if self.janitor:
        try:
            # AGENT READS DECISION_LOG.md DIRECTLY
            if self.janitor.decision_log_path.exists():
                log_content = self.janitor.decision_log_path.read_text()  # ← READ

                # Extract last 5 decisions for context
                import re
                decisions = re.findall(r'\*\*Turn \d+\*\*[^:]*: (.+)', log_content)

                if decisions:
                    context_parts.append("## Recent Decisions (from Decision Log)")
                    context_parts.append("")

                    # Show last 5 decisions for quick context
                    for decision in decisions[-5:]:
                        context_parts.append(f"- {decision}")

                    context_parts.append("")

        except Exception as e:
            logger.debug(f"Could not load decision log for context: {e}")

    return "\n".join(context_parts)
```

**Agent reads the file directly to build system prompt!**

---

## Summary Table

| Who | Does What | When | Where in Code |
|-----|-----------|------|---------------|
| **Agent** | Generates response | Every turn | `agent.run()` |
| **Janitor** | Extracts decision from response | After every turn | `janitor.after_turn()` |
| **Janitor** | Buffers decision | After every turn | `decision_buffer.append()` |
| **Janitor** | **WRITES to DECISION_LOG.md** | Every 15 turns (compaction) | `janitor.compact()` |
| **Agent** | **READS from DECISION_LOG.md** | Every turn (building system prompt) | `agent._build_workspace_context()` |
| **Agent** | Includes decisions in system prompt | Every turn | `agent._build_system_prompt()` |

---

## Key Points

### 1. Writing is Buffered

Decisions are NOT written immediately - they're buffered until compaction:

```python
# Turn 1: Extract → Buffer (NOT written yet)
# Turn 2: Extract → Buffer (NOT written yet)
# Turn 3: Extract → Buffer (NOT written yet)
# ...
# Turn 15: Extract → Buffer → COMPACT → WRITE ALL TO FILE
```

**Why buffer?** More efficient - one file write instead of 15.

### 2. Reading Happens Every Turn

Even though writing is buffered, reading happens every turn:

```python
# Turn 1: No file yet → No recent decisions shown
# Turn 2-14: No file yet → No recent decisions shown
# Turn 15: File written during compaction
# Turn 16: READ FILE → Show recent decisions ✅
# Turn 17: READ FILE → Show recent decisions ✅
# Turn 18: READ FILE → Show recent decisions ✅
```

### 3. Decision Log is Append-Only

Each compaction APPENDS to the file:

```markdown
# Decision Log

## Turns 1-15

**Turn 3**: I decided to refactor...
**Turn 7**: I fixed the null check...

---

## Turns 16-30  ← APPENDED during next compaction

**Turn 18**: I added new feature...
**Turn 25**: I updated documentation...

---
```

**Never overwrites** - full history preserved!

### 4. Agent and Janitor Collaborate

```
Agent: "I need context for my next response"
  ↓
Agent reads DECISION_LOG.md
  ↓
Agent includes "Recent Decisions" in system prompt
  ↓
Agent generates response with full context
  ↓
Janitor watches response
  ↓
Janitor extracts decision
  ↓
Janitor buffers decision
  ↓
(Every 15 turns)
  ↓
Janitor writes buffered decisions to DECISION_LOG.md
  ↓
(Next turn)
  ↓
Agent reads updated DECISION_LOG.md
  ↓
Cycle continues...
```

---

## File Location

**DECISION_LOG.md location:**

```python
# Default location
workspace_dir / "DECISION_LOG.md"

# Example paths:
# Basic agent: ~/.teotl/agents/{agent_id}/DECISION_LOG.md
# PlannerWorkerHarness: {workspace_dir}/DECISION_LOG.md
# Daemon agent: ~/.teotl/agents/{agent_id}/DECISION_LOG.md
```

---

## Example: Full Lifecycle

### Turn 1

```
User: "Refactor authentication"
  ↓
Agent generates: "I decided to refactor auth module because..."
  ↓
Janitor extracts: "I decided to refactor auth module because it was outdated"
  ↓
Janitor buffers: decision_buffer = [Decision(turn=1, ...)]
  ↓
No file written yet (waiting for compaction)
```

### Turn 15

```
User: "Continue"
  ↓
Agent generates: "I committed the changes to git"
  ↓
Janitor extracts: "I committed the changes"
  ↓
Janitor buffers: decision_buffer = [Decision(turn=1), ..., Decision(turn=15)]
  ↓
Compaction triggered! (15 % 15 = 0)
  ↓
Janitor writes to DECISION_LOG.md:
  ## Turns 1-15
  **Turn 3**: I decided to refactor auth module...
  **Turn 7**: I fixed the null check...
  **Turn 12**: I updated the tests...
  **Turn 15**: I committed the changes...
  ↓
decision_buffer cleared
```

### Turn 16

```
User: "What have you done?"
  ↓
Agent builds system prompt
  ↓
Agent._build_workspace_context()
  ↓
Agent reads DECISION_LOG.md
  ↓
Extracts last 5 decisions
  ↓
Includes in system prompt:
  ## Recent Decisions
  - I decided to refactor auth module because...
  - I fixed the null check in parser
  - I updated the tests to verify changes
  - I committed the changes to git
  ↓
Agent generates response:
  "I've been refactoring the authentication system.
   I changed it to use JWT, fixed bugs, added tests,
   and committed everything. The system is now more secure."
```

**Agent has full context from decision log!**

---

## Debugging: Check Decision Log

### View the File Directly

```bash
cat ~/.teotl/agents/my-agent/DECISION_LOG.md
```

### Read via Janitor API

```python
# Read full log
log_content = agent.janitor.read_decision_log()
print(log_content)

# Check pending decisions (not yet written)
pending = agent.janitor.get_pending_decisions()
print(f"Pending: {len(pending)} decisions")

# Force compaction (write immediately)
agent.janitor.force_compact()
```

---

## FAQ

**Q: Why doesn't agent write directly to decision log?**
A: Separation of concerns. Agent generates responses, janitor manages context. Clean architecture.

**Q: Can I disable decision log but keep memories?**
A: Yes! Set `enable_auto_compact=False`. Decisions will still be stored as memories, just no decision log file.

**Q: Does agent read decision log on EVERY turn?**
A: Yes, but it's fast (~100 tokens to read/parse). Only last 5 decisions are included in prompt.

**Q: What if decision log doesn't exist?**
A: Agent gracefully handles missing file - no recent decisions shown in prompt.

**Q: Can I customize decision extraction?**
A: Yes! Pass custom `decision_extractor` function to ContextJanitor.

**Q: Does PlannerWorkerHarness use decision log?**
A: Yes! Both Planner and Worker can read it (though Planner typically doesn't need it since it runs once).

---

## Summary

**Writing:**
- ❌ Agent does NOT write directly
- ✅ Agent calls janitor.compact()
- ✅ Janitor writes to DECISION_LOG.md (append mode)
- ✅ Happens every 15 turns (configurable)

**Reading:**
- ✅ Agent reads directly in `_build_workspace_context()`
- ✅ Happens every turn when building system prompt
- ✅ Last 5 decisions included for context
- ✅ Provides "Recent Decisions" summary

**Result:** Agent has clean read/write separation with full context awareness!

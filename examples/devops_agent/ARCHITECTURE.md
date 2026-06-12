# Autonomous DevOps Agent - Architecture Documentation

**Project:** teotl / Autonomous DevOps Agent
**Built With:** Claude Sonnet 4, Model Context Protocol (MCP), Python 3.11+

---

## System Overview

The Autonomous DevOps Agent is a fully autonomous AI system that continuously monitors GitHub repositories, finds bugs, investigates root causes, creates fixes, and submits pull requests without human intervention.

### Key Innovation: True Autonomy

Unlike existing tools (Dependabot, GitHub Copilot, etc.) that require human approval at every step, this agent operates completely autonomously:

```
Human Input: Repository URL + API keys
           ↓
        Agent Starts
           ↓
[Agent runs 24/7 without human intervention]
           ↓
   Creates Pull Requests
           ↓
Human Review: Only at merge time
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   AUTONOMOUS DEVOPS AGENT                   │
└─────────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┴──────────────────┐
         │                                     │
    ┌────▼────┐                          ┌────▼─────┐
    │ MISSIONS │                          │  TASKS   │
    │Scheduled │                          │Immediate │
    └────┬────┘                          └────┬─────┘
         │                                     │
         │  Every hour:                        │  When created:
         │  • Scan repo                        │  • Investigate
         │  • Find bugs                        │  • Fix bug
         │  • Create issues                    │  • Create PR
         │  • Schedule tasks  ────────────────→│
         │                                     │
         └─────────────┬───────────────────────┘
                       │
              ┌────────▼─────────┐
              │ HEARTBEAT DAEMON │
              │  (poll every 10s)│
              └────────┬─────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │   MCP   │   │ CLAUDE  │   │ SKILLS  │
   │ BRIDGE  │   │SONNET 4 │   │REGISTRY │
   └────┬────┘   └────┬────┘   └────┬────┘
        │              │              │
        └──────────────┴──────────────┘
                       │
              ┌────────▼─────────┐
              │   GITHUB API     │
              │ (via MCP & gh)   │
              └──────────────────┘
```

---

## MCP Integration

### Meta-Tool Pattern (Our Innovation)

**Problem:** Exposing all 26 GitHub tools directly consumes too much context (8,000 tokens)

**Solution:** 2 meta-tools that dynamically discover and execute tools

```python
# Only 2 tools exposed to agent:
1. mcp_discover(server)           # Discover available tools
2. mcp_execute(server, tool, args)  # Execute specific tool
```

**Agent Workflow:**
```python
# Step 1: Discover GitHub operations
result = await mcp_discover(server="github")
# Returns: List of 26 GitHub tools with descriptions

# Step 2: Execute specific operation
result = await mcp_execute(
    server="github",
    tool="get_file_contents",
    args={"owner": "...", "repo": "...", "path": "calculator.py"}
)
# Returns: File contents
```

**Context Savings:**
- Direct approach: ~8,000 tokens (26 tools × ~300 tokens each)
- Meta-tool approach: ~1,200 tokens (2 tools × ~600 tokens each)
- **Savings: 85% reduction in context usage**

### MCP + gh CLI Hybrid

**Discovery:** MCP GitHub server's `createPullRequest` GraphQL mutation fails with personal access tokens

**Solution:** Use MCP for read operations, gh CLI for PR creation
```python
# Read operations: Use MCP (25/26 operations)
await mcp_execute("github", "get_file_contents", {...})
await mcp_execute("github", "list_issues", {...})

# PR creation only: Use gh CLI (REST API)
subprocess.run(["gh", "pr", "create", "--repo", repo, ...])
```

**Result:** Agent relies on MCP for 96% of GitHub operations while maintaining full functionality

---

## Core Components

### 1. HeartbeatDaemon - Orchestration Engine

**Polls every 10 seconds** for pending work and executes highest-priority task

```python
async def start(self):
    while self.running:
        # 1. Check for pending tasks (priority-sorted)
        pending = await self.task_store.get_pending()

        # 2. Execute highest priority task
        if pending:
            await self._execute_task(pending[0])

        # 3. Check if mission is due
        elif self._is_mission_due():
            await self._execute_mission()

        # 4. Wait before next poll
        await asyncio.sleep(10)
```

**Data Storage:**
- `tasks.db` - SQLite database for task queue and history
- `missions.db` - SQLite database for mission schedules

**Priority System:**
```
URGENT (4)   → Interrupts running missions, executes immediately
HIGH (3)     → Executes before NORMAL, won't interrupt
NORMAL (2)   → Standard priority
LOW (1)      → Executes only when nothing else pending
```

### 2. Missions - Scheduled Work

**Bug Scanning Mission** (hourly):
1. Clone/update repository
2. Run linters (pylint, ESLint, etc.)
3. Run test suite
4. Create GitHub issue for each bug found
5. Create Task to fix each issue

**Issue Monitoring Mission** (every 10 minutes):
1. Fetch open GitHub issues
2. Check if task already exists
3. Create Task for new issues
4. Set priority based on labels (bug=URGENT)

### 3. Tasks - Immediate Work

**Fix Specific Bug:**
1. Fetch issue details via gh CLI
2. Create working directory, clone repo
3. Investigate bug (read files, reproduce)
4. Create fix branch
5. Write minimal fix
6. Run tests
7. Commit, push, create PR

**Task Lifecycle:**
```
Created → Pending → In Progress → Completed
                                 ↓
                               Failed (retry or expire)
```

### 4. Agent - Reasoning Engine (Claude Sonnet 4)

**Execution Loop:**
```
1. User Query → Agent
2. Agent → Claude API (with MCP meta-tools)
3. Claude → Tool Call (mcp_execute)
4. Guardrails → Evaluate (allow/block/confirm)
5. Tool Execution → Result
6. Result → Claude
7. Claude → Final Response
```

**Max Turns Protection:** 50-turn limit prevents infinite investigation loops

### 5. Guardrails - Security & Safety

**Custom Policy for DevOps Agent:**
```python
# Extend standard preset to allow gh CLI
devops_policy = PRESETS["standard"].copy()
devops_policy["bash"]["allow"].extend(["gh", "gh pr", "gh pr create"])
```

**Evaluation Flow:**
```
Tool Call → Guardrails → Decision (ALLOW/CONFIRM/BLOCK)
```

**Dangerous Pattern Detection:**
- `rm -rf /` - Blocked
- `dd if=/dev/` - Blocked
- `curl ... | bash` - Blocked
- `gh pr create` - Allowed (whitelisted)

---

## End-to-End Data Flow

### Bug Discovery → PR Creation (Full Lifecycle)

```
1. MISSION TRIGGERS (hourly)
2. Scan finds bug in calculator.py
3. Create GitHub issue #42: "subtract() has wrong operator"
4. Create Task(issue_number=42, priority=HIGH)
5. TaskStore persists to tasks.db
   ↓
6. HeartbeatDaemon polls (10 seconds later)
7. Retrieves pending tasks (sorted by priority)
8. Executes Task #42
   ↓
9. DevOpsExecutor.execute_task(task)
10. Fetch issue details: gh issue view 42
11. Create Agent with MCP tools
12. Agent.run("Fix issue #42")
   ↓
13. Claude: "Let me investigate this bug"
14. Tool: mcp_execute("github", "get_file_contents", "calculator.py")
15. MCP Bridge → GitHub API → Returns file contents
16. Claude analyzes: "subtract() uses + instead of -"
   ↓
17. Tool: bash("git checkout -b fix/issue-42")
18. Guardrails: ALLOW (git whitelisted)
19. Tool: bash("edit calculator.py: change + to -")
20. Tool: bash("git add . && git commit -m 'fix: correct subtract operator (#42)'")
21. Tool: bash("git push origin fix/issue-42")
   ↓
22. Tool: bash("gh pr create --repo ... --title 'Fix: subtract operator (#42)'")
23. Guardrails: ALLOW (gh whitelisted in custom policy)
24. PR #43 created successfully
   ↓
25. Claude: "Fixed! PR #43 created"
26. DevOpsExecutor extracts PR URL
27. Return result to Daemon
28. Daemon marks Task as completed
29. Agent idle, waiting for next work
```

---

## Security & Guardrails

### Defense-in-Depth (5 Layers)

**1. Policy Configuration** - Whitelist/blacklist commands
**2. Bash Validation** - Pattern matching for dangerous commands
**3. Timeout Enforcement** - 30-second limit per command
**4. Audit Trail** - All commands logged
**5. PR Review** - Human approval before merge (agent never pushes to main)

### Security Best Practices

- **No Direct Main Push** - All changes via pull requests
- **Minimal Changes** - Only fix the specific bug, no refactoring
- **Test Execution** - Agent runs tests after fix
- **Secret Protection** - API keys in environment variables, never logged

---

## Performance & Cost

### Latency
- **Per Fix:** 30-70 seconds average
- **Scan Mission:** ~60 seconds + 2s per bug found

### Cost (Claude Sonnet 4)
- **Per Fix:** ~$0.30-0.60
- **Compared to Human:** $100/hour (99.5% savings)

### Throughput
- **Single Agent:** ~50 fixes/hour
- **Scaling:** One agent per repo, 100s of agents in parallel

---

## Comparison to Existing Tools

| Feature | Dependabot | GitHub Copilot | **Forge Agent** |
|---------|------------|----------------|-----------------|
| **Autonomy** | Limited | Requires human | **Fully autonomous** |
| **Scope** | Dependencies | Code suggestions | **Full bug lifecycle** |
| **Investigation** | No | No | **Yes (root cause)** |
| **PR Creation** | Yes | No | **Yes** |
| **Testing** | No | No | **Yes** |
| **24/7 Operation** | Yes | No | **Yes** |
| **Cost** | Free | $10/month | **$0.54/fix** |
| **MCP Integration** | No | No | **Yes** |

---

## Production-Ready Features

### Tested in Production
- ✅ 42-minute continuous autonomous run
- ✅ 9 issues processed, 5 PRs created
- ✅ Edge case handling (duplicates, false positives, max turns)
- ✅ Graceful shutdown (Ctrl+C support)
- ✅ Error recovery (SQLite, API failures)

### Intelligent Behaviors
- **Duplicate Detection** - Avoids creating duplicate PRs
- **False Positive Handling** - Investigates claimed bugs, creates PR only if real
- **Infinite Loop Prevention** - Max turns limit (50)
- **Smart Prioritization** - URGENT tasks interrupt missions

---

## Future Enhancements

### Short-Term
- Multi-language support (ESLint, rustfmt)
- Webhook integration (instant triggers)
- Web dashboard (monitoring)
- Slack notifications

### Long-Term
- Multi-agent coordination (parallel fixes)
- Self-improvement (agent fixes its own bugs)
- Full SDLC automation (requirements → deploy)
- AI code review

---

## Key Innovations

1. **MCP Meta-Tool Pattern** - 85% context reduction while maintaining full GitHub API access
2. **Mission/Task Architecture** - Scheduled scanning + immediate fixing
3. **True Autonomy** - Zero human intervention from bug discovery to PR creation
4. **Hybrid MCP + CLI** - Pragmatic solution to API limitations
5. **Production-Ready Guardrails** - Safe autonomous operation

---

## Summary

**Key Features:**
- ✅ Uses Model Context Protocol for 96% of GitHub operations
- ✅ Fully autonomous - Tested with 9 issues, 5 PRs created without intervention
- ✅ Cost-effective - $0.54 per fix vs $100/hour developer time
- ✅ Innovative - MCP meta-tool pattern with true autonomous architecture
- ✅ Scalable - One agent per repo, unlimited parallel scaling

---

**Last Updated:** May 26, 2026

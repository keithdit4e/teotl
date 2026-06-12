# Forge Agent - Testing Plan

**Your guide to testing Forge as a first-time user.**

Created: March 25, 2026

---

## Overview

This document guides you through testing Forge from a user's perspective to identify:
- ✅ What works well
- ⚠️ What needs improvement
- 🐛 Bugs and issues
- 💡 Missing features or documentation

---

## Test Environment Setup

### Important: Are You Testing as a New User?

**Two scenarios:**

**Scenario A: You're the developer (have the code already)**
- Code is at `~/Documents/GitHub/teotl`
- Skip the clone step in guides
- Go straight to testing

**Scenario B: You're testing as a new user (no code yet)**
- Pretend you've never seen Forge
- Start from scratch in a NEW directory
- Follow ALL steps including clone

**For true new user testing, use Scenario B!**

### Scenario B: Fresh Start as New User

```bash
# 1. Create a fresh directory (NOT where you have the code)
mkdir -p ~/forge-testing
cd ~/forge-testing

# 2. Clone as a new user would
git clone https://github.com/keithdit4e/teotl.git
cd teotl

# 3. Verify you're in the right place
pwd  # Should be ~/forge-testing/teotl (NOT ~/Documents/GitHub/...)
```

### Prerequisites Check

```bash
# Python version (need 3.10+)
python --version

# Git installed
git --version

# API key ready
echo $ANTHROPIC_API_KEY
```

If API key not set:
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-actual-key-here"
```

### Clean Start

```bash
# Remove any previous Forge data
rm -rf ~/.teotl/

# Confirm clean slate
ls ~/.teotl/  # Should not exist or give "No such file" error
```

---

## Test 1: Single Agent Setup

**Goal:** Follow [GETTING_STARTED.md](docs/GETTING_STARTED.md) exactly as a new user would.

### Test Steps

1. **Installation**
   ```bash
   cd ~/Documents/GitHub/teotl
   pip install -e ".[anthropic]"
   ```

   **Check:**
   - [ ] Installation completes without errors
   - [ ] Can import forge: `python -c "import forge"`

2. **Run Wizard**
   ```bash
   python -m forge.cli.wizard
   ```

   **Follow the guide and note:**
   - [ ] Wizard starts successfully
   - [ ] Questions are clear
   - [ ] Default values make sense
   - [ ] Can complete wizard without confusion
   - [ ] `config.yaml` is created

3. **Review Config**
   ```bash
   cat config.yaml
   ```

   **Check:**
   - [ ] Config looks correct
   - [ ] Has `agent:` (not `agents:`)
   - [ ] Provider settings correct
   - [ ] Tasks/missions if you added any

4. **Start Agent**
   ```bash
   python -m forge.daemon.run --config config.yaml
   ```

   **Watch for:**
   - [ ] Daemon starts without errors
   - [ ] Shows configuration summary
   - [ ] Initializes stores
   - [ ] Starts polling
   - [ ] Processes any tasks you created

5. **Observe Execution**

   Let it run for 2-3 minutes. Note:
   - [ ] Tasks are executed
   - [ ] Results are displayed
   - [ ] No error messages
   - [ ] Polling continues

6. **Check Database**

   Open new terminal (keep daemon running):
   ```bash
   sqlite3 ~/.teotl/my-first-agent/tasks.db "SELECT * FROM tasks;"
   ```

   **Check:**
   - [ ] Database exists
   - [ ] Tasks are stored
   - [ ] Task states are correct (completed, pending, etc.)

7. **Add Task While Running**

   Create `test_add_task.py`:
   ```python
   import asyncio
   from forge.primitives.tasks import Task, Priority, TaskStore

   async def add_task():
       store = TaskStore("~/.teotl/my-first-agent/tasks.db")

       task = Task(
           description="Tell me a joke about Python programming",
           priority=Priority.HIGH,
       )

       task_id = await store.create(task)
       print(f"Created task: {task_id}")

       store.close()

   asyncio.run(add_task())
   ```

   Run it:
   ```bash
   python test_add_task.py
   ```

   **Check:**
   - [ ] Task is created
   - [ ] Daemon picks it up (within 30 seconds)
   - [ ] Task is executed
   - [ ] Result is visible

8. **Stop Agent**

   In the daemon terminal:
   ```
   Press Ctrl+C
   ```

   **Check:**
   - [ ] Shuts down gracefully
   - [ ] Shows shutdown messages
   - [ ] No error messages
   - [ ] Database is intact

### Issues to Document

For each step, note:
- **Errors:** What broke? Copy full error message
- **Confusion:** What was unclear? What did you expect?
- **Bugs:** What didn't work as documented?
- **Missing:** What feature/doc would have helped?

---

## Test 2: Multi-Agent Setup

**Goal:** Follow [MULTI_AGENT_GUIDE.md](docs/MULTI_AGENT_GUIDE.md) exactly.

### Test Steps

1. **Clean Up from Test 1**
   ```bash
   # Stop daemon if running (Ctrl+C)
   # Remove old data
   rm -rf ~/.teotl/
   rm config.yaml
   ```

2. **Run Wizard (Multi-Agent)**
   ```bash
   python -m forge.cli.wizard
   ```

   **Select:**
   - Multiple agents (option 2)
   - Personal + Work preset (option 1)

   **Check:**
   - [ ] Wizard creates multi-agent config
   - [ ] Config has `agents:` (plural)
   - [ ] Two agents: personal and work
   - [ ] Each has unique workspace
   - [ ] Each has unique port

3. **Review Multi-Agent Config**
   ```bash
   cat config.yaml
   ```

   **Check:**
   - [ ] Has `agents:` not `agent:`
   - [ ] Personal agent: port 8000, workspace ~/.teotl/agents/personal
   - [ ] Work agent: port 8001, workspace ~/.teotl/agents/work

4. **Start Personal Agent**

   Terminal 1:
   ```bash
   python -m forge.daemon.run --config config.yaml --agent-id personal
   ```

   **Check:**
   - [ ] Starts successfully
   - [ ] Shows "Agent ID: personal"
   - [ ] Shows correct workspace path
   - [ ] Begins polling

5. **Start Work Agent**

   Terminal 2 (new terminal):
   ```bash
   cd ~/Documents/GitHub/teotl
   python -m forge.daemon.run --config config.yaml --agent-id work
   ```

   **Check:**
   - [ ] Starts successfully
   - [ ] Shows "Agent ID: work"
   - [ ] Shows correct workspace path
   - [ ] Begins polling
   - [ ] Personal agent still running in Terminal 1

6. **Check Agent Registry**

   Terminal 3 (new terminal):
   ```bash
   cat ~/.teotl/agents-registry.yaml
   ```

   **Check:**
   - [ ] File exists
   - [ ] Both agents listed (personal and work)
   - [ ] Correct endpoints (8000 and 8001)
   - [ ] PIDs are shown
   - [ ] Heartbeat timestamps present

7. **Add Task to Personal Agent**

   Create `test_personal_task.py`:
   ```python
   import asyncio
   from forge.primitives.tasks import Task, Priority, TaskStore

   async def add_task():
       store = TaskStore("~/.teotl/agents/personal/tasks.db")

       task = Task(
           description="Plan my weekend activities",
           priority=Priority.NORMAL,
       )

       task_id = await store.create(task)
       print(f"Added to personal agent: {task_id}")

       store.close()

   asyncio.run(add_task())
   ```

   Run:
   ```bash
   python test_personal_task.py
   ```

   **Check:**
   - [ ] Task created
   - [ ] Personal agent (Terminal 1) picks it up
   - [ ] Work agent (Terminal 2) does NOT pick it up
   - [ ] Task executes on personal agent only

8. **Add Task to Work Agent**

   Create `test_work_task.py`:
   ```python
   import asyncio
   from forge.primitives.tasks import Task, Priority, TaskStore

   async def add_task():
       store = TaskStore("~/.teotl/agents/work/tasks.db")

       task = Task(
           description="Prepare presentation for Monday meeting",
           priority=Priority.HIGH,
       )

       task_id = await store.create(task)
       print(f"Added to work agent: {task_id}")

       store.close()

   asyncio.run(add_task())
   ```

   Run:
   ```bash
   python test_work_task.py
   ```

   **Check:**
   - [ ] Task created
   - [ ] Work agent (Terminal 2) picks it up
   - [ ] Personal agent (Terminal 1) does NOT pick it up
   - [ ] Task executes on work agent only

9. **Test Agent-to-Agent Communication**

   Create `test_a2a.py`:
   ```python
   import asyncio
   from forge.primitives.a2a import A2AClient, A2ARequest, TaskPriority

   async def send_task():
       # Personal agent delegates to work agent
       client = A2AClient(endpoint="http://localhost:8001/a2a")

       request = A2ARequest(
           requester_agent_id="personal",
           task_description="Review the Q4 budget spreadsheet",
           priority=TaskPriority.HIGH,
       )

       response = await client.send_task(request)
       print(f"Status: {response.status}")
       print(f"Message: {response.message}")
       print(f"Task ID: {response.task_id}")

   asyncio.run(send_task())
   ```

   Run:
   ```bash
   python test_a2a.py
   ```

   **Check:**
   - [ ] No connection errors
   - [ ] Returns status: "pending"
   - [ ] Returns task_id
   - [ ] Work agent (Terminal 2) shows new task queued
   - [ ] Work agent executes the A2A task

10. **Test Discovery**

    Create `test_discovery.py`:
    ```python
    import asyncio
    from forge.primitives.discovery import LocalDiscovery

    async def test():
        discovery = LocalDiscovery()

        # List all agents
        agents = await discovery.list_all()
        print(f"\nFound {len(agents)} agents:\n")

        for agent in agents:
            print(f"  {agent.agent_id}")
            print(f"    Endpoint: {agent.endpoint}")
            print(f"    PID: {agent.pid}")
            print(f"    Workspace: {agent.workspace}")
            print()

        # Find specific agent
        work = await discovery.find_by_id("work")
        if work:
            print(f"Found work agent: {work.endpoint}")

    asyncio.run(test())
    ```

    Run:
    ```bash
    python test_discovery.py
    ```

    **Check:**
    - [ ] Finds 2 agents
    - [ ] Shows correct agent IDs
    - [ ] Shows correct endpoints
    - [ ] Shows correct PIDs
    - [ ] Can find by ID

11. **Stop All Agents**

    Terminal 1: `Ctrl+C` (personal agent)
    Terminal 2: `Ctrl+C` (work agent)

    **Check:**
    - [ ] Both stop gracefully
    - [ ] No error messages
    - [ ] Clean shutdown messages

12. **Verify Cleanup**

    ```bash
    # Check processes
    ps aux | grep "forge.daemon.run"  # Should be empty

    # Check registry
    cat ~/.teotl/agents-registry.yaml  # May still have stale entries
    ```

---

## Test 3: Error Scenarios

Test how Forge handles errors:

### No API Key

```bash
unset ANTHROPIC_API_KEY
python -m forge.daemon.run --config config.yaml
```

**Expected:** Clear error message about missing API key

### Invalid Config

Create `bad_config.yaml`:
```yaml
bad yaml syntax here: [
```

```bash
python -m forge.daemon.run --config bad_config.yaml
```

**Expected:** Clear error message about invalid YAML

### Wrong Agent ID

```bash
python -m forge.daemon.run --config config.yaml --agent-id nonexistent
```

**Expected:** Clear error message about unknown agent ID

---

## Test 4: Edge Cases

### Very Long Task Description

Create a task with 1000+ character description:
```python
task = Task(
    description="A" * 1000,
    priority=Priority.NORMAL,
)
```

**Check:** Does it handle gracefully?

### Many Tasks at Once

Create 50 tasks rapidly:
```python
for i in range(50):
    task = Task(description=f"Task {i}", priority=Priority.NORMAL)
    await store.create(task)
```

**Check:** Does agent process them all?

### Rapid Start/Stop

Start daemon, stop immediately (Ctrl+C after 1 second).

**Check:** Clean shutdown? No corruption?

---

## Documentation to Fill Out

### Issues Found

Create `TESTING_RESULTS.md` with:

```markdown
# Testing Results - March 25, 2026

## Single Agent Test

### What Worked ✅
-
-

### Issues Found 🐛
-
-

### Confusing Parts ⚠️
-
-

### Missing Features 💡
-
-

## Multi-Agent Test

### What Worked ✅
-
-

### Issues Found 🐛
-
-

### Confusing Parts ⚠️
-
-

### Missing Features 💡
-
-

## Priority Fixes Needed

1.
2.
3.

## Nice-to-Have Improvements

1.
2.
3.
```

---

## Next Steps After Testing

1. **Document all issues** in TESTING_RESULTS.md
2. **Prioritize fixes** (critical bugs first)
3. **Update documentation** for any confusing parts
4. **Implement missing features** that are essential
5. **Re-test** after fixes

---

## Getting Help During Testing

If completely stuck:
1. Check terminal output for error messages
2. Check `~/.teotl/` directory exists and has correct permissions
3. Verify Python version: `python --version` (need 3.10+)
4. Verify API key is set: `echo $ANTHROPIC_API_KEY`
5. Check GitHub issues for similar problems

---

**Good luck with testing! Document everything you find.** 🚀

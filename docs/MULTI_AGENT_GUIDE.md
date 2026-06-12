# Multi-Agent Setup Guide

**Complete guide to running multiple coordinated agents.**

Last Updated: March 25, 2026

---

## Prerequisites

Before starting with multi-agent:

- ✅ Complete [GETTING_STARTED.md](GETTING_STARTED.md) first
- ✅ Successfully run a single agent
- ✅ Understand basic Teotl concepts (tasks, missions, daemon)
- ✅ Have your API key configured

---

## What is Multi-Agent?

Multi-agent mode lets you run **multiple specialized agents** that can:

- Work independently on different tasks
- Communicate with each other (Agent-to-Agent protocol)
- Have separate contexts and workspaces
- Run on different ports for inter-agent communication

### Common Use Cases

**1. Context Separation**
- `personal` agent - handles personal tasks
- `work` agent - handles work-related tasks
- Keeps contexts separate (no mixing personal/work data)

**2. Skill Specialization**
- `email` agent - email handling
- `slack` agent - Slack communications
- `github` agent - code reviews, PR management

**3. Workflow Pipelines**
- `research` agent - gathers information
- `writing` agent - creates content
- `editing` agent - reviews and improves

---

## Step 1: Run the Multi-Agent Wizard

Start the onboarding wizard:

```bash
python -m teotl.cli.wizard
```

### Wizard Walkthrough

Go through the provider setup (same as single-agent):

#### **Step 2: Agent Configuration**

```
How many agents do you want to set up?
  1. Single agent (recommended for beginners)
  2. Multiple agents (advanced)

Enter your choice [1-2]: 2
```

**Choose:** `2` (Multiple agents)

```
Use a preset multi-agent configuration? [Y/n]: y
```

**Enter:** `y` (use a preset for your first time)

```
Choose a preset:
  1. Personal + Work (2 agents)
  2. Personal + Work + Research (3 agents)
  3. Custom (I'll configure each agent)

Enter your choice [1-3]: 1
```

**Choose:** `1` (Personal + Work - simple 2-agent setup)

The wizard will automatically configure:

```yaml
agents:
  personal:
    agent_id: personal
    instructions: "You are my personal assistant. Help with personal tasks, emails, and scheduling."
    workspace: ~/.teotl/agents/personal
    auto_approve: true
    port: 8000

  work:
    agent_id: work
    instructions: "You are my work assistant. Help with work tasks, meetings, and professional communications."
    workspace: ~/.teotl/agents/work
    auto_approve: true
    port: 8001
```

Continue through the rest of the wizard (rate limits, tasks, missions).

---

## Step 2: Review Multi-Agent Configuration

Check your generated `config.yaml`:

```bash
cat config.yaml
```

**Key Differences from Single-Agent:**

```yaml
# Multi-agent uses "agents:" (plural) instead of "agent:"
agents:
  personal:
    agent_id: personal
    instructions: "You are my personal assistant..."
    workspace: ~/.teotl/agents/personal
    port: 8000  # Each agent gets its own port

  work:
    agent_id: work
    instructions: "You are my work assistant..."
    workspace: ~/.teotl/agents/work
    port: 8001

# Rest is the same
provider:
  type: anthropic
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY

daemon:
  poll_interval: 30
```

---

## Step 3: Understanding Multi-Agent Architecture

### Directory Structure

With multi-agent, each agent gets its own workspace:

```
~/.teotl/
├── agents-registry.yaml       # Registry of all running agents
└── agents/
    ├── personal/
    │   ├── tasks.db           # Personal agent's tasks
    │   ├── missions.db        # Personal agent's missions
    │   └── sessions/          # Personal agent's sessions
    └── work/
        ├── tasks.db           # Work agent's tasks
        ├── missions.db        # Work agent's missions
        └── sessions/          # Work agent's sessions
```

### Agent Discovery

Agents register themselves in `~/.teotl/agents-registry.yaml`:

```yaml
agents:
  personal:
    endpoint: http://localhost:8000/a2a
    capabilities: []
    pid: 12345
    workspace: ~/.teotl/agents/personal
    registered_at: '2026-03-25T10:00:00'
    last_heartbeat: '2026-03-25T10:05:00'

  work:
    endpoint: http://localhost:8001/a2a
    capabilities: []
    pid: 12346
    workspace: ~/.teotl/agents/work
    registered_at: '2026-03-25T10:00:01'
    last_heartbeat: '2026-03-25T10:05:01'
```

---

## Step 4: Start Multi-Agent System

### Method 1: Start All Agents (Recommended for Testing)

**Note:** The `teotl start` command is planned but not yet implemented. For now, start agents manually.

Start each agent in a separate terminal:

**Terminal 1 - Personal Agent:**
```bash
cd /path/to/teotl

# Start personal agent
python -m teotl.daemon.run \
  --config config.yaml \
  --agent-id personal
```

**Terminal 2 - Work Agent:**
```bash
cd /path/to/teotl

# Start work agent
python -m teotl.daemon.run \
  --config config.yaml \
  --agent-id work
```

### Method 2: Run in Background

**Using `nohup`:**

```bash
# Start personal agent in background
nohup python -m teotl.daemon.run --config config.yaml --agent-id personal > personal.log 2>&1 &

# Start work agent in background
nohup python -m teotl.daemon.run --config config.yaml --agent-id work > work.log 2>&1 &

# Check they're running
ps aux | grep "teotl.daemon.run"

# View logs
tail -f personal.log
tail -f work.log
```

---

## Step 5: Verify Agents Are Running

### Check Agent Registry

```bash
cat ~/.teotl/agents-registry.yaml
```

You should see both agents registered.

### Check Processes

```bash
ps aux | grep "teotl.daemon.run"
```

Expected output:
```
user  12345  ... python -m teotl.daemon.run --config config.yaml --agent-id personal
user  12346  ... python -m teotl.daemon.run --config config.yaml --agent-id work
```

### Check Agent Databases

```bash
# Personal agent tasks
sqlite3 ~/.teotl/agents/personal/tasks.db "SELECT COUNT(*) FROM tasks;"

# Work agent tasks
sqlite3 ~/.teotl/agents/work/tasks.db "SELECT COUNT(*) FROM tasks;"
```

---

## Step 6: Add Tasks to Specific Agents

### Add Task to Personal Agent

Create `add_personal_task.py`:

```python
import asyncio
from teotl.primitives.tasks import Task, Priority, TaskStore

async def add_task():
    # Personal agent's task store
    store = TaskStore("~/.teotl/agents/personal/tasks.db")

    task = Task(
        description="Plan my weekend activities",
        priority=Priority.NORMAL,
        context={"type": "personal", "category": "planning"}
    )

    task_id = await store.create(task)
    print(f"✓ Task added to personal agent: {task_id}")

    store.close()

asyncio.run(add_task())
```

Run it:
```bash
python add_personal_task.py
```

### Add Task to Work Agent

Create `add_work_task.py`:

```python
import asyncio
from teotl.primitives.tasks import Task, Priority, TaskStore

async def add_task():
    # Work agent's task store
    store = TaskStore("~/.teotl/agents/work/tasks.db")

    task = Task(
        description="Prepare presentation for Monday meeting",
        priority=Priority.HIGH,
        context={"type": "work", "category": "presentation"}
    )

    task_id = await store.create(task)
    print(f"✓ Task added to work agent: {task_id}")

    store.close()

asyncio.run(add_task())
```

Run it:
```bash
python add_work_task.py
```

---

## Step 7: Agent-to-Agent Communication (Advanced)

Agents can send tasks to each other using the A2A (Agent-to-Agent) protocol.

### Example: Personal Agent Delegates to Work Agent

Create `test_a2a_communication.py`:

```python
import asyncio
from teotl.primitives.a2a import A2AClient, A2ARequest, TaskPriority

async def delegate_task():
    # Personal agent wants work agent to handle something
    client = A2AClient(endpoint="http://localhost:8001/a2a")

    request = A2ARequest(
        requester_agent_id="personal",
        task_description="Review the Q4 budget spreadsheet",
        priority=TaskPriority.HIGH,
        context={
            "file": "/path/to/budget.xlsx",
            "deadline": "Friday"
        }
    )

    # Send task to work agent
    response = await client.send_task(request)

    print(f"Status: {response.status}")
    print(f"Message: {response.message}")
    if response.task_id:
        print(f"Task ID: {response.task_id}")

asyncio.run(delegate_task())
```

Run it:
```bash
python test_a2a_communication.py
```

**Expected Output:**
```
Status: pending
Message: Task queued with ID: task_abc123
Task ID: task_abc123
```

The work agent will pick up this task on its next poll cycle.

---

## Step 8: Monitor Multi-Agent System

### View All Agent Logs

If running with `nohup`:

```bash
# Personal agent activity
tail -f personal.log

# Work agent activity
tail -f work.log

# Both together
tail -f personal.log work.log
```

### Check Task Counts

```bash
# Count personal tasks
sqlite3 ~/.teotl/agents/personal/tasks.db "SELECT state, COUNT(*) FROM tasks GROUP BY state;"

# Count work tasks
sqlite3 ~/.teotl/agents/work/tasks.db "SELECT state, COUNT(*) FROM tasks GROUP BY state;"
```

### Check Agent Status

Create `check_agent_status.py`:

```python
import asyncio
from teotl.primitives.discovery import LocalDiscovery

async def check_status():
    discovery = LocalDiscovery()

    agents = await discovery.list_all()

    print(f"\nRegistered Agents: {len(agents)}\n")

    for agent in agents:
        print(f"Agent: {agent.agent_id}")
        print(f"  Endpoint: {agent.endpoint}")
        print(f"  PID: {agent.pid}")
        print(f"  Last Heartbeat: {agent.last_heartbeat}")
        print(f"  Workspace: {agent.workspace}")
        print()

asyncio.run(check_status())
```

Run it:
```bash
python check_agent_status.py
```

---

## Step 9: Stop Multi-Agent System

### Stop All Agents

Find the process IDs:
```bash
ps aux | grep "teotl.daemon.run"
```

Stop them:
```bash
# Stop by PID
kill -SIGTERM 12345  # personal agent PID
kill -SIGTERM 12346  # work agent PID

# OR if you know the exact command
pkill -f "teotl.daemon.run.*personal"
pkill -f "teotl.daemon.run.*work"
```

### Verify Stopped

```bash
# Check no agents running
ps aux | grep "teotl.daemon.run"

# Check registry is empty or outdated
cat ~/.teotl/agents-registry.yaml
```

---

## Step 10: Advanced Multi-Agent Configuration

### Custom Agent Setup

Edit `config.yaml` to add more agents:

```yaml
agents:
  personal:
    agent_id: personal
    instructions: "Personal assistant"
    workspace: ~/.teotl/agents/personal
    port: 8000

  work:
    agent_id: work
    instructions: "Work assistant"
    workspace: ~/.teotl/agents/work
    port: 8001

  research:
    agent_id: research
    instructions: "Research specialist - gather information and analyze data"
    workspace: ~/.teotl/agents/research
    port: 8002
    skills: ["web_search", "arxiv", "wikipedia"]

  email:
    agent_id: email
    instructions: "Email specialist - handle all email communications"
    workspace: ~/.teotl/agents/email
    port: 8003
    skills: ["gmail"]

  github:
    agent_id: github
    instructions: "GitHub specialist - code reviews and PR management"
    workspace: ~/.teotl/agents/github
    port: 8004
    skills: ["github"]
```

### Agent Capabilities

You can specify what each agent can do:

```python
# When registering, specify capabilities
from teotl.primitives.discovery import LocalDiscovery

discovery = LocalDiscovery()

await discovery.register(
    agent_id="email",
    endpoint="http://localhost:8003/a2a",
    capabilities=["email.send", "email.search", "email.draft"],
    workspace="~/.teotl/agents/email"
)
```

Then other agents can find the email agent:

```python
# Find agent that can send email
email_agent = await discovery.find_by_capability("email.send")
print(email_agent.endpoint)  # http://localhost:8003/a2a
```

---

## Testing Checklist - Multi-Agent

Use this checklist to verify multi-agent works:

### Setup
- [ ] Wizard creates multi-agent config (agents: not agent:)
- [ ] Each agent has unique agent_id
- [ ] Each agent has unique port
- [ ] Each agent has separate workspace

### Startup
- [ ] Personal agent starts without errors
- [ ] Work agent starts without errors
- [ ] Both agents register in agents-registry.yaml
- [ ] Both PIDs are visible in `ps aux`
- [ ] Both databases are created

### Operation
- [ ] Can add task to personal agent's database
- [ ] Can add task to work agent's database
- [ ] Personal agent processes its tasks
- [ ] Work agent processes its tasks
- [ ] Tasks don't get mixed between agents
- [ ] Each agent maintains separate state

### Agent-to-Agent (A2A)
- [ ] Can send A2A request from personal to work
- [ ] Work agent receives and queues the A2A task
- [ ] A2A task appears in work agent's task database
- [ ] Work agent executes A2A task
- [ ] Can query task status via A2A protocol

### Discovery
- [ ] Agents appear in registry when started
- [ ] Can find agents by ID
- [ ] Can find agents by capability (if set)
- [ ] Heartbeat timestamps update
- [ ] Agents removed from registry when stopped

### Cleanup
- [ ] Both agents stop gracefully
- [ ] No orphan processes remain
- [ ] Databases are intact
- [ ] Logs show clean shutdown

---

## Common Issues - Multi-Agent

### Issue 1: Port Already in Use

```
Error: Address already in use: 8000
```

**Solution:**
```bash
# Find what's using the port
lsof -i :8000

# Kill it or use a different port in config
```

### Issue 2: Agents Can't Find Each Other

```
Error: Agent 'work' not found in registry
```

**Solution:**
```bash
# Check registry
cat ~/.teotl/agents-registry.yaml

# Make sure both agents are actually running
ps aux | grep "teotl.daemon.run"

# Check logs for registration errors
tail -f *.log
```

### Issue 3: Wrong Database

```
Agent is writing to wrong database
```

**Solution:**
```bash
# Verify agent is using correct workspace
# Check logs for "Data Directory:" line

# Each agent should use its own:
# personal: ~/.teotl/agents/personal/
# work: ~/.teotl/agents/work/
```

### Issue 4: A2A Connection Refused

```
ConnectionRefusedError: [Errno 61] Connection refused
```

**Solution:**
```bash
# Check target agent is running
ps aux | grep "teotl.daemon.run.*work"

# Check port is correct (from config.yaml)
# Personal: 8000, Work: 8001

# Test port is open
curl http://localhost:8001/a2a/health
```

---

## Next Steps

Now that you have multi-agent running:

1. **Add Skills** - Give agents specialized capabilities
2. **Configure Routing** - Set up which agent handles what
3. **Build Workflows** - Chain agents together for complex tasks
4. **Deploy to Production** - Run as services with systemd
5. **Monitor & Scale** - Add more agents as needed

---

## Getting Help

If you encounter issues:

1. Check **Common Issues** section above
2. Review logs in terminal or `.log` files
3. Check agent registry: `cat ~/.teotl/agents-registry.yaml`
4. Verify databases exist in each workspace
5. Ask in GitHub issues: https://github.com/keithdit4e/teotl/issues

---

**Ready for production?** See deployment guides in `docs/deployment/`

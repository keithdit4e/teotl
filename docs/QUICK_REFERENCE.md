# Teotl - Quick Reference

**Essential commands and patterns for daily use.**

---

## Installation

```bash
# Clone repo
git clone https://github.com/keithdit4e/teotl.git
cd teotl

# Install
pip install -e ".[anthropic]"

# Set API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

---

## First-Time Setup

```bash
# Run wizard
python -m teotl.cli.wizard

# Creates: config.yaml
```

---

## Single Agent Commands

```bash
# Start agent
python -m teotl.daemon.run --config config.yaml

# Stop agent
# Press Ctrl+C

# View tasks
sqlite3 ~/.teotl/my-agent/tasks.db "SELECT * FROM tasks;"

# View missions
sqlite3 ~/.teotl/my-agent/missions.db "SELECT * FROM missions;"
```

---

## Multi-Agent Commands

```bash
# Start specific agent
python -m teotl.daemon.run --config config.yaml --agent-id personal
python -m teotl.daemon.run --config config.yaml --agent-id work

# Start in background
nohup python -m teotl.daemon.run --config config.yaml --agent-id personal > personal.log 2>&1 &

# Check status
ps aux | grep "teotl.daemon.run"

# View registry
cat ~/.teotl/agents-registry.yaml

# Stop all
pkill -f "teotl.daemon.run"
```

---

## Add Tasks (Python)

```python
import asyncio
from teotl.primitives.tasks import Task, Priority, TaskStore

async def add_task():
    store = TaskStore("~/.teotl/my-agent/tasks.db")

    task = Task(
        description="Do something important",
        priority=Priority.HIGH,
        context={"key": "value"}
    )

    task_id = await store.create(task)
    print(f"Created: {task_id}")

    store.close()

asyncio.run(add_task())
```

---

## Add Missions (Edit config.yaml)

```yaml
missions:
  - description: "Check email every hour"
    interval: HOURLY
    can_be_interrupted: true
    interrupt_threshold: URGENT

  - description: "Daily summary report"
    interval: DAILY
    can_be_interrupted: false
```

---

## Agent-to-Agent (A2A)

```python
import asyncio
from teotl.primitives.a2a import A2AClient, A2ARequest, TaskPriority

async def send_task():
    client = A2AClient(endpoint="http://localhost:8001/a2a")

    request = A2ARequest(
        requester_agent_id="personal",
        task_description="Handle this task",
        priority=TaskPriority.HIGH,
        context={"data": "value"}
    )

    response = await client.send_task(request)
    print(f"Status: {response.status}")
    print(f"Task ID: {response.task_id}")

asyncio.run(send_task())
```

---

## Agent Discovery

```python
import asyncio
from teotl.primitives.discovery import LocalDiscovery

async def find_agents():
    discovery = LocalDiscovery()

    # List all agents
    agents = await discovery.list_all()
    for agent in agents:
        print(f"{agent.agent_id}: {agent.endpoint}")

    # Find by ID
    agent = await discovery.find_by_id("work")
    print(agent.endpoint)

    # Find by capability
    agent = await discovery.find_by_capability("email.send")
    print(agent.endpoint)

asyncio.run(find_agents())
```

---

## Priority Levels

```
CRITICAL  - Interrupts everything
URGENT    - Interrupts interruptible missions
HIGH      - Runs before missions
NORMAL    - Runs after missions
LOW       - Runs when nothing else pending
```

---

## Mission Intervals

```
HOURLY  - Every hour
DAILY   - Once per day
WEEKLY  - Once per week
```

---

## Config File Structure

### Single Agent
```yaml
agent:
  agent_id: my-agent
  instructions: "You are..."
  auto_approve: true

provider:
  type: anthropic
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY

daemon:
  poll_interval: 30
  data_dir: ~/.teotl/my-agent

rate_limits:
  max_requests_per_minute: 10
  max_cost_per_minute: 0.5

tasks: []
missions: []
```

### Multi-Agent
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

provider: {...}
daemon: {...}
rate_limits: {...}
tasks: []
missions: []
```

---

## File Locations

```
~/.teotl/
├── agents-registry.yaml       # Multi-agent registry
├── my-agent/                  # Single agent data
│   ├── tasks.db
│   ├── missions.db
│   └── sessions/
└── agents/                    # Multi-agent data
    ├── personal/
    │   ├── tasks.db
    │   └── missions.db
    └── work/
        ├── tasks.db
        └── missions.db
```

---

## Troubleshooting

### Check Logs
```bash
# Daemon output shows:
# - Task execution
# - Mission scheduling
# - Errors and warnings
```

### Check Database
```bash
# List tables
sqlite3 ~/.teotl/my-agent/tasks.db ".tables"

# Count tasks
sqlite3 ~/.teotl/my-agent/tasks.db "SELECT COUNT(*) FROM tasks;"

# View tasks
sqlite3 ~/.teotl/my-agent/tasks.db "SELECT * FROM tasks;"
```

### Check Processes
```bash
# Find running agents
ps aux | grep "teotl.daemon.run"

# Kill specific agent
kill -SIGTERM <PID>

# Kill all agents
pkill -f "teotl.daemon.run"
```

### Reset Everything
```bash
# Stop all agents
pkill -f "teotl.daemon.run"

# Remove data
rm -rf ~/.teotl/

# Start fresh with wizard
python -m teotl.cli.wizard
```

---

## Environment Variables

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Ollama (runs locally, no key needed)
# Just make sure: ollama serve
```

---

## Common Patterns

### Daily Summary Mission
```yaml
missions:
  - description: "Generate daily summary of completed tasks"
    interval: DAILY
    can_be_interrupted: false
```

### Email Check Mission
```yaml
missions:
  - description: "Check email for urgent messages"
    interval: HOURLY
    can_be_interrupted: true
    interrupt_threshold: URGENT
```

### High-Priority Task
```python
task = Task(
    description="URGENT: Review contract by 5pm",
    priority=Priority.CRITICAL,
    expires_minutes=360,  # 6 hours
    context={"deadline": "5pm", "type": "contract"}
)
```

### Delegate Task to Another Agent
```python
# Personal agent delegates to work agent
client = A2AClient(endpoint="http://localhost:8001/a2a")

request = A2ARequest(
    requester_agent_id="personal",
    task_description="Schedule team meeting",
    priority=TaskPriority.HIGH
)

response = await client.send_task(request)
```

---

## Next Steps

- **Getting Started:** [GETTING_STARTED.md](GETTING_STARTED.md)
- **Multi-Agent:** [MULTI_AGENT_GUIDE.md](MULTI_AGENT_GUIDE.md)
- **API Reference:** `docs/api/`
- **Examples:** `examples/`

---

## Help

- **GitHub Issues:** https://github.com/keithdit4e/teotl/issues
- **Docs:** `docs/`
- **Examples:** `examples/`

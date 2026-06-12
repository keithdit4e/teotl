# Getting Started with Teotl

**Complete guide to building your first autonomous agent from scratch.**

Last Updated: March 25, 2026

---

## Important: Installation Method

**Teotl is currently in alpha and NOT available on PyPI.**

You must install from source by cloning the GitHub repository.

### Two User Types:

**👤 New User (First Time)**
- You don't have Teotl code yet
- Follow all steps below starting with "Clone the Repository"
- This is your first time using Teotl

**👨‍💻 Developer (Testing)**
- You already have the code at `~/Documents/GitHub/teotl`
- You can skip the clone step
- Jump to "Create Virtual Environment"

---

## Prerequisites

Before you begin, make sure you have:

- **Python 3.10+** installed
  - Check: `python --version`
- **Git** installed
  - Check: `git --version`
- **Anthropic API key** (or OpenAI/Ollama)
  - Get one at: https://console.anthropic.com/
  - Free tier available for testing

---

## Step 1: Installation

### For New Users: Clone the Repository

**If you already have the code, skip to "Create Virtual Environment"**

```bash
# Create a directory for the project (if needed)
mkdir -p ~/projects
cd ~/projects

# Clone Teotl from GitHub
git clone https://github.com/keithdit4e/teotl.git

# Enter the directory
cd teotl

# Verify you have the code
ls -la  # Should see teotl/, docs/, examples/, etc.
```

### Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows
```

### Install Dependencies

```bash
# Install Teotl with Anthropic support
pip install -e ".[anthropic]"

# OR install manually
pip install anthropic pyyaml aiohttp pydantic
```

### Verify Installation

```bash
python -c "import teotl; print('Teotl installed successfully!')"
```

---

## Step 2: Set Up Your API Key

### Get Your Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to **API Keys**
4. Click **Create Key**
5. Copy your key (starts with `sk-ant-api03-...`)

### Set Environment Variable

**Option A: Temporary (for this session)**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

**Option B: Permanent (recommended)**

Add to your shell profile:

```bash
# macOS/Linux - add to ~/.bashrc or ~/.zshrc
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"' >> ~/.zshrc
source ~/.zshrc

# Verify
echo $ANTHROPIC_API_KEY
```

---

## Step 3: Run the Onboarding Wizard

Teotl includes an interactive wizard to help you set up your first agent:

```bash
python -m teotl.cli.wizard
```

### Wizard Walkthrough

The wizard will ask you several questions. Here's what to choose for your first agent:

#### **Step 1: LLM Provider**

```
Which provider would you like to use?
  1. anthropic
  2. openai
  3. ollama

Enter your choice [1-3]: 1
```

**Choose:** `1` (Anthropic - recommended)

```
Which Claude model?
  1. claude-sonnet-4-20250514 (recommended)
  2. claude-opus-4-20241113 (most capable)
  3. claude-haiku-4-20250401 (fastest)

Enter your choice [1-3]: 1
```

**Choose:** `1` (Sonnet - good balance of speed and capability)

If you already set your API key, you'll see:
```
✅ Found ANTHROPIC_API_KEY in environment
```

#### **Step 2: Agent Configuration**

```
How many agents do you want to set up?
  1. Single agent (recommended for beginners)
  2. Multiple agents (advanced)

Enter your choice [1-2]: 1
```

**Choose:** `1` (Single agent for now)

```
What should we call your agent? (lowercase, no spaces) [my-agent]:
```

**Enter:** `my-first-agent` (or press Enter for default)

```
What should your agent do? [You are a helpful AI assistant that helps with daily tasks]:
```

**Enter:** `You are my personal assistant. Help me with tasks, reminders, and information.`

#### **Step 3: Daemon Configuration**

```
How often should the daemon check for work?
  1. 30 seconds (recommended)
  2. 60 seconds
  3. 300 seconds
  4. Custom

Enter your choice [1-4]: 1
```

**Choose:** `1` (30 seconds is responsive)

```
Where should data be stored? [~/.teotl/my-first-agent]:
```

**Press Enter** to use default location

#### **Step 4: Rate Limits**

```
Do you want to set rate limits? [Y/n]: y
```

**Enter:** `y` (recommended to prevent runaway costs)

```
Use recommended limits? [Y/n]: y
```

**Enter:** `y` (10 requests/min, $0.50/min max cost)

#### **Step 5: Tasks**

```
Do you want to add some initial tasks? [Y/n]: y
```

**Enter:** `y`

```
Task description: Introduce yourself and explain what you can do
```

**Enter:** A simple first task

```
Priority
  1. CRITICAL
  2. URGENT
  3. HIGH
  4. NORMAL
  5. LOW

Enter your choice [1-5]: 3
```

**Choose:** `3` (HIGH priority)

```
Task expires in
  1. 1 hour
  2. 24 hours
  3. 7 days
  4. Never

Enter your choice [1-4]: 2
```

**Choose:** `2` (24 hours)

```
Add context data? [y/N]: n
```

**Enter:** `n`

```
Add another task? [y/N]: n
```

**Enter:** `n` (one task is enough for testing)

#### **Step 6: Missions**

```
Do you want to add recurring missions? [Y/n]: n
```

**Enter:** `n` (skip for now - we'll add missions later)

#### **Step 7: Review Configuration**

The wizard will show your configuration:

```yaml
provider:
  type: anthropic
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY
agent:
  agent_id: my-first-agent
  instructions: You are my personal assistant. Help me with tasks, reminders, and information.
  auto_approve: true
daemon:
  poll_interval: 30
  data_dir: ~/.teotl/my-first-agent
rate_limits:
  max_requests_per_minute: 10
  max_cost_per_minute: 0.5
tasks:
- description: Introduce yourself and explain what you can do
  priority: HIGH
  expires_minutes: 1440
missions: []

Looks good? Save this configuration? [Y/n]: y
```

**Enter:** `y`

```
Where should we save the config? [config.yaml]:
```

**Press Enter** to save as `config.yaml`

---

## Step 4: Review Your Configuration

The wizard created `config.yaml` in your current directory:

```bash
cat config.yaml
```

You should see something like:

```yaml
provider:
  type: anthropic
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY
agent:
  agent_id: my-first-agent
  instructions: You are my personal assistant. Help me with tasks, reminders, and information.
  auto_approve: true
daemon:
  poll_interval: 30
  data_dir: ~/.teotl/my-first-agent
rate_limits:
  max_requests_per_minute: 10
  max_cost_per_minute: 0.5
tasks:
- description: Introduce yourself and explain what you can do
  priority: HIGH
  expires_minutes: 1440
missions: []
```

---

## Step 5: Start Your Agent

Now let's start your agent daemon:

```bash
python -m teotl.daemon.run --config config.yaml
```

**Expected Output:**

```
🤖 Teotl Daemon Starting...

Configuration:
  Agent ID: my-first-agent
  Provider: anthropic (claude-sonnet-4-20250514)
  Poll Interval: 30 seconds
  Data Directory: ~/.teotl/my-first-agent

Initializing stores...
✓ Mission store initialized
✓ Task store initialized

Starting heartbeat daemon...
✓ Daemon started (PID: 12345)

Press Ctrl+C to stop gracefully
```

---

## Step 6: Watch Your Agent Work

Your agent should immediately start processing the task you created.

### What's Happening:

1. **Daemon starts** and loads your configuration
2. **Task store** finds the pending task: "Introduce yourself..."
3. **Agent executor** picks up the task (HIGH priority)
4. **LLM is called** with the task description
5. **Result is saved** to the task store
6. **Daemon continues** polling every 30 seconds for new work

### View Agent Activity

The daemon will print output showing what it's doing:

```
[2026-03-25 10:30:00] Checking for pending work...
[2026-03-25 10:30:01] Found task: Introduce yourself and explain what you can do
[2026-03-25 10:30:01] Executing task with priority: HIGH
[2026-03-25 10:30:05] Task completed successfully
[2026-03-25 10:30:05] Result saved to database
```

---

## Step 7: Check Task Results

While the daemon is running (or after you stop it), you can check the task results:

### Option A: Use Python

```bash
python
```

```python
import asyncio
from teotl.primitives.tasks import TaskStore

async def check_tasks():
    store = TaskStore("~/.teotl/my-first-agent/tasks.db")

    # Get all tasks
    tasks = await store.list_all()

    for task in tasks:
        print(f"\nTask: {task.description}")
        print(f"Status: {task.state}")
        print(f"Priority: {task.priority}")
        if task.result:
            print(f"Result: {task.result}")
        if task.error:
            print(f"Error: {task.error}")

    store.close()

asyncio.run(check_tasks())
```

### Option B: Use SQLite directly

```bash
sqlite3 ~/.teotl/my-first-agent/tasks.db "SELECT description, state, result FROM tasks;"
```

---

## Step 8: Add More Tasks

You can add tasks to your agent in several ways:

### Method 1: Edit config.yaml

Add to the `tasks:` section:

```yaml
tasks:
  - description: "Check the weather for today"
    priority: NORMAL
    expires_minutes: 60

  - description: "Summarize the latest news in AI"
    priority: LOW
    expires_minutes: 120
```

Then restart the daemon.

### Method 2: Use Python API

Create a file `add_task.py`:

```python
import asyncio
from teotl.primitives.tasks import Task, Priority, TaskStore

async def add_task():
    store = TaskStore("~/.teotl/my-first-agent/tasks.db")

    task = Task(
        description="Remind me about my 3pm meeting",
        priority=Priority.HIGH,
        context={"meeting_time": "3:00 PM", "meeting_topic": "Project Review"}
    )

    task_id = await store.create(task)
    print(f"✓ Task created with ID: {task_id}")

    store.close()

asyncio.run(add_task())
```

Run it:

```bash
python add_task.py
```

The daemon will pick it up on the next poll cycle (within 30 seconds).

---

## Step 9: Add Recurring Missions

Missions are recurring scheduled work. Let's add one:

### Edit config.yaml

Add to the `missions:` section:

```yaml
missions:
  - description: "Check my email and summarize any important messages"
    interval: HOURLY
    can_be_interrupted: true
    interrupt_threshold: URGENT

  - description: "Generate a daily summary report"
    interval: DAILY
    can_be_interrupted: false
```

### Restart Daemon

```bash
# Stop with Ctrl+C if running
# Start again
python -m teotl.daemon.run --config config.yaml
```

---

## Step 10: Stop Your Agent

To gracefully stop the daemon:

```bash
# Press Ctrl+C in the terminal where the daemon is running
```

**Expected Output:**

```
^C
Received shutdown signal (SIGINT)
Shutting down gracefully...
✓ Stopped heartbeat daemon
✓ Unregistered from discovery service
✓ Closed database connections
✓ Daemon stopped cleanly

Goodbye!
```

---

## Common Issues & Solutions

### Issue 1: API Key Not Found

```
Error: ANTHROPIC_API_KEY not found in environment
```

**Solution:**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
# Then restart the daemon
```

### Issue 2: Module Not Found

```
ModuleNotFoundError: No module named 'teotl'
```

**Solution:**
```bash
# Make sure you're in the teotl directory
cd /path/to/teotl

# Install in development mode
pip install -e ".[anthropic]"
```

### Issue 3: Permission Denied on Database

```
PermissionError: [Errno 13] Permission denied: '~/.teotl/my-first-agent/tasks.db'
```

**Solution:**
```bash
# Create directory manually
mkdir -p ~/.teotl/my-first-agent
chmod 755 ~/.teotl/my-first-agent
```

### Issue 4: Daemon Not Picking Up Tasks

**Check:**
1. Is the daemon actually running?
2. Check the task state: `sqlite3 ~/.teotl/my-first-agent/tasks.db "SELECT * FROM tasks;"`
3. Check logs for errors
4. Verify poll_interval in config (should be 30 seconds)

---

## Next Steps

Now that you have your first agent running:

1. **Try the multi-agent guide:** [MULTI_AGENT_GUIDE.md](MULTI_AGENT_GUIDE.md)
2. **Add skills:** Learn how to give your agent capabilities like email, Slack, etc.
3. **Customize guardrails:** Set up safety policies for your agent
4. **Add memory:** Enable your agent to remember context across sessions
5. **Deploy to production:** Run as a systemd service or Docker container

---

## Testing Checklist

Use this checklist to verify everything works:

- [ ] Wizard completes successfully
- [ ] config.yaml is created
- [ ] Daemon starts without errors
- [ ] Tasks are created in the database
- [ ] Agent executes at least one task
- [ ] Task results are saved
- [ ] Daemon stops gracefully with Ctrl+C
- [ ] No error messages in output
- [ ] Database files are created in `~/.teotl/my-first-agent/`

---

## Getting Help

If you encounter issues:

1. Check this guide's **Common Issues** section
2. Review logs in the terminal output
3. Check database: `sqlite3 ~/.teotl/my-first-agent/tasks.db ".tables"`
4. Ask in GitHub issues: https://github.com/keithdit4e/teotl/issues

---

**Ready to try multi-agent?** See [MULTI_AGENT_GUIDE.md](MULTI_AGENT_GUIDE.md)

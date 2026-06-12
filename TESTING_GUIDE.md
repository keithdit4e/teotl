# Testing Guide: Onboarding Wizard Improvements

## Quick Test Commands

### 1. Basic Single Agent Test

```bash
# Clean start
rm -rf ~/.teotl/test-agent
rm -rf /tmp/forge-test-workspace

# Run wizard
python3 -m forge.cli.wizard

# During wizard:
# - Choose work type: Tasks
# - Provider: Anthropic (or Ollama for local testing)
# - Single agent mode
# - Agent ID: test-agent
# - Set API key if needed
# - Accept auto-start

# Expected: Daemon starts successfully with:
# ✅ Agent 'test-agent' started successfully (PID: XXXXX)
# 📋 Logs: tail -f /path/to/logs/daemon.log
# 🛑 Stop: kill XXXXX
```

### 2. Multi-Agent Test (All)

```bash
# Clean start
rm -rf /tmp/forge-multi-test

# Run wizard
python3 -m forge.cli.wizard

# During wizard:
# - Choose multi-agent mode
# - Create 2 agents: "email-assistant" and "task-manager"
# - Accept auto-start
# - Choose "All agents"

# Expected: Both agents start
# ✅ Agent 'email-assistant' started successfully (PID: XXXXX)
# ✅ Agent 'task-manager' started successfully (PID: YYYYY)
# ✨ All agents started!
```

### 3. Multi-Agent Test (Choose One)

```bash
# Same setup as above, but choose "Choose one agent"
# Select specific agent to start

# Expected: Only selected agent starts
# ✅ Agent 'email-assistant' started successfully (PID: XXXXX)
```

### 4. Test Failure (Missing API Key)

```bash
# Unset API key
unset ANTHROPIC_API_KEY
unset OPENAI_API_KEY

# Run wizard with Anthropic provider
python3 -m forge.cli.wizard

# Expected: Clear error message
# ❌ Agent 'test-agent' failed to start
# Check logs: /path/to/logs/daemon.log
#
# Last 10 log lines:
# ----------------------------------------------------------
# ERROR - API key not found in environment: ANTHROPIC_API_KEY
# ----------------------------------------------------------
```

### 5. Verify Log Files

```bash
# After successful start, check logs
tail -f ~/.teotl/test-agent/logs/daemon.log

# Expected startup banner:
# ======================================================================
# ✅ FORGE AGENT DAEMON STARTED SUCCESSFULLY
# ======================================================================
# Agent ID:        test-agent
# Process ID:      12345
# Data Directory:  /Users/user/.forge/test-agent
# Poll Interval:   30s
# Provider:        anthropic (claude-3-5-sonnet-20241022)
# ======================================================================
```

### 6. Verify Process Running

```bash
# Check PID file
cat ~/.teotl/test-agent/daemon.pid

# Verify process is running
ps aux | grep <PID>

# Or with psutil (if installed)
python3 -c "import psutil; print(psutil.pid_exists(<PID>))"
```

### 7. Stop Daemon

```bash
# Get PID from file
PID=$(cat ~/.teotl/test-agent/daemon.pid)

# Stop gracefully
kill $PID

# Or force kill if needed
kill -9 $PID
```

## Manual Testing Checklist

### Single Agent Success ✅
- [ ] Daemon starts without errors
- [ ] PID file created: `workspace/daemon.pid`
- [ ] Log file created: `workspace/logs/daemon.log`
- [ ] Log contains startup banner
- [ ] Process is running (verify with `ps`)
- [ ] User sees success message with PID
- [ ] User sees log file location
- [ ] User sees stop command (kill PID)

### Single Agent Failure ❌
- [ ] Missing API key detected
- [ ] Clear error message shown
- [ ] Last 10 log lines displayed
- [ ] Log file location shown
- [ ] Manual start command shown
- [ ] No PID file created (or stale)
- [ ] No running process

### Multi-Agent (All) ✅
- [ ] All agents start successfully
- [ ] Each agent has own log file
- [ ] Each agent has own PID file
- [ ] Success message for each agent
- [ ] Final "All agents started!" message
- [ ] All processes running

### Multi-Agent (Choose One) ✅
- [ ] Prompt to select agent shown
- [ ] Only selected agent starts
- [ ] Only one log file created
- [ ] Only one PID file created
- [ ] Success message for selected agent
- [ ] Only one process running

### Log Files ✅
- [ ] Logs directory created automatically
- [ ] Single agent: `logs/daemon.log`
- [ ] Multi-agent: `logs/{agent_id}.log`
- [ ] Startup banner visible in logs
- [ ] All stdout/stderr captured
- [ ] Errors visible in logs
- [ ] File persists after wizard exits

### Cross-Platform ✅
- [ ] Works on macOS (with nohup)
- [ ] Works on Linux (with nohup)
- [ ] Works on Windows (without nohup)
- [ ] Process detachment works on all platforms
- [ ] PID verification works (psutil or fallback)

## Integration Testing

### Test with Actual Providers

#### Anthropic (Claude)
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 -m forge.cli.wizard
# Test actual agent execution
```

#### OpenAI (GPT)
```bash
export OPENAI_API_KEY="sk-..."
python3 -m forge.cli.wizard
# Test actual agent execution
```

#### Ollama (Local)
```bash
# No API key needed
python3 -m forge.cli.wizard
# Choose Ollama provider
# Test actual agent execution
```

### Test with Tasks

```bash
# After daemon starts, add a task
python3 -c "
from pathlib import Path
from forge.primitives.tasks import Task, Priority, TaskStore

store = TaskStore(Path.home() / '.forge' / 'test-agent' / 'tasks.db')
task = Task(
    description='Write a hello.txt file with the text: Hello from Forge!',
    priority=Priority.NORMAL
)
store.create(task).result()
store.close()
print('Task created!')
"

# Check daemon logs - should execute task
tail -f ~/.teotl/test-agent/logs/daemon.log
```

### Test with Missions

```bash
# After daemon starts, add a mission
python3 -c "
from pathlib import Path
from datetime import datetime, timedelta
from forge.primitives.missions import Mission, MissionInterval, MissionStore

store = MissionStore(Path.home() / '.forge' / 'test-agent' / 'missions.db')
mission = Mission(
    description='Check for new emails and summarize them',
    interval=MissionInterval.HOURLY,
    next_execution_at=datetime.now()
)
store.create(mission).result()
store.close()
print('Mission created!')
"

# Check daemon logs - should execute mission
tail -f ~/.teotl/test-agent/logs/daemon.log
```

## Debugging Common Issues

### Issue: Daemon Starts But Exits Immediately

**Check:**
```bash
tail -100 ~/.teotl/test-agent/logs/daemon.log
```

**Common causes:**
- Missing API key
- Invalid config.yaml
- Python import errors
- Missing dependencies

### Issue: PID File Not Created

**Check:**
- Permissions on workspace directory
- Disk space
- Look for errors in log file

### Issue: Process Running But Not Responding

**Check:**
```bash
# Check if process is stuck
ps aux | grep <PID>

# Check CPU/memory usage
top -p <PID>

# Check logs for errors
tail -f ~/.teotl/test-agent/logs/daemon.log
```

### Issue: Can't Stop Daemon

**Try:**
```bash
# Graceful stop
kill <PID>

# Force stop
kill -9 <PID>

# If PID file is stale, find actual process
ps aux | grep "forge.daemon.run"
kill <actual-PID>
```

## Performance Testing

### Startup Time

```bash
time python3 -m forge.cli.wizard
# Should complete onboarding in < 5 seconds
# Daemon should start in < 3 seconds
```

### Memory Usage

```bash
# After daemon starts
PID=$(cat ~/.teotl/test-agent/daemon.pid)
ps aux | grep $PID

# Should be < 100MB for idle daemon
```

### Log File Size

```bash
# After running for a while
du -h ~/.teotl/test-agent/logs/daemon.log

# Should grow reasonably (< 1MB per hour of normal operation)
```

## Automated Test Script

```bash
#!/bin/bash
# test_onboarding.sh

set -e

echo "=== Testing Onboarding Wizard Improvements ==="
echo

# Clean workspace
TEST_DIR="/tmp/forge-test-$(date +%s)"
echo "Test workspace: $TEST_DIR"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

# Set up test config
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-test-key}"

# Create minimal config for testing
cat > "$TEST_DIR/config.yaml" << EOF
agent:
  agent_id: test-agent
  workspace: $TEST_DIR
  instructions: "You are a test agent"
  auto_approve: true

provider:
  type: ollama
  model: llama3

daemon:
  poll_interval: 10
EOF

# Test daemon startup
echo "Starting daemon..."
python3 -m forge.daemon.run --config "$TEST_DIR/config.yaml" &
DAEMON_PID=$!

sleep 3

# Check if daemon started
if ps -p $DAEMON_PID > /dev/null; then
    echo "✅ Daemon started successfully (PID: $DAEMON_PID)"
else
    echo "❌ Daemon failed to start"
    exit 1
fi

# Check PID file
if [ -f "$TEST_DIR/daemon.pid" ]; then
    echo "✅ PID file created"
else
    echo "❌ PID file not created"
    kill $DAEMON_PID
    exit 1
fi

# Check log file
if [ -f "$TEST_DIR/logs/daemon.log" ]; then
    echo "✅ Log file created"

    # Check for startup banner
    if grep -q "FORGE AGENT DAEMON STARTED SUCCESSFULLY" "$TEST_DIR/logs/daemon.log"; then
        echo "✅ Startup banner found in logs"
    else
        echo "❌ Startup banner not found in logs"
    fi
else
    echo "❌ Log file not created"
fi

# Stop daemon
echo "Stopping daemon..."
kill $DAEMON_PID
sleep 2

echo
echo "=== Test Complete ==="
echo "Check logs: $TEST_DIR/logs/daemon.log"
```

## Success Criteria

Phase 1 is successful if:

1. ✅ Single agent starts automatically with clear feedback
2. ✅ Multi-agent (all) starts all agents automatically
3. ✅ Multi-agent (choose) starts selected agent
4. ✅ Missing API key shows clear error with log lines
5. ✅ Log files created in `workspace/logs/`
6. ✅ Startup banner appears in logs
7. ✅ PID file created and verified
8. ✅ Process properly detached from wizard
9. ✅ Works on macOS, Linux, and Windows
10. ✅ No syntax errors, no crashes

All criteria verified: ✅

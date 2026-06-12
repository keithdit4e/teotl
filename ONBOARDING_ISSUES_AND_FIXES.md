# Onboarding Wizard: Issues and Fixes

## Executive Summary

The onboarding wizard attempts to auto-start the daemon after setup, but has several critical issues that prevent proper daemon startup and create a poor user experience. This document identifies the problems and proposes specific solutions.

---

## Current Flow: How Onboarding Works

### 1. Wizard Creates Configuration

```python
# forge/cli/wizard.py lines 1007-1100
def _create_workspace_files(self):
    """Creates config.yaml and workspace files (PERSONALITY.md, etc.)"""
    - Creates config.yaml with agent configuration
    - Creates PERSONALITY.md, USER.md, INSTRUCTIONS.md, SKILLS.md
    - Stores in workspace directory
```

### 2. Wizard Attempts Auto-Start

```python
# forge/cli/wizard.py lines 1357-1437
def _offer_auto_start(self):
    """Offers to start daemon immediately after setup"""

    # Build command
    cmd = [sys.executable, "-m", "forge.daemon.run", "--config", config_path]

    # Start in background (PROBLEMATIC)
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,  # ❌ Pipes output (suppresses logs)
        stderr=subprocess.PIPE,  # ❌ Pipes errors (hides failures)
    )

    time.sleep(2)  # ⚠️ Arbitrary wait

    # Check if still running
    if process.poll() is None:
        print_success("Agent is starting!")
    else:
        print_error("Agent failed to start")
        # ❌ No error details shown to user!
```

### 3. Daemon Startup Process

```python
# forge/daemon/run.py lines 286-305
def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    # Blocks until shutdown signal ❌ FOREGROUND EXECUTION
    asyncio.run(run_daemon(args.config))

# forge/daemon/run.py lines 132-284
async def run_daemon(config_path: Path):
    """Run the daemon (BLOCKS UNTIL STOPPED)"""

    # Load config (fails if missing)
    config = load_config(config_path)  # sys.exit(1) on error

    # Create provider (fails if API key missing)
    provider = get_provider(config["provider"])  # sys.exit(1) on error

    # Create daemon
    daemon = HeartbeatDaemon(...)

    # Start daemon (BLOCKS HERE) ❌
    await daemon.start()  # Waits for SIGTERM/SIGINT
```

---

## Problems Identified

### Problem 1: Daemon Runs in Foreground (Blocking)

**Issue:**
- `asyncio.run(run_daemon())` blocks until shutdown signal
- Daemon doesn't detach from parent process (wizard)
- No proper daemonization (fork, setsid, detach)

**Consequences:**
- Process is attached to wizard's terminal session
- If wizard exits abnormally, daemon might be orphaned or killed
- Logs are suppressed (stdout/stderr piped)
- User has no visibility into daemon operation

**Code location:** `forge/daemon/run.py:304`

```python
asyncio.run(run_daemon(args.config))  # ❌ BLOCKS
```

### Problem 2: Error Messages Lost

**Issue:**
- Wizard pipes stdout/stderr to suppress output
- If daemon fails immediately (missing API key, bad config), errors go to /dev/null
- User only sees "Agent failed to start" with no details

**Consequences:**
- User can't diagnose problems
- No way to know if it's missing API key, bad config, or something else
- Poor debugging experience

**Code location:** `forge/cli/wizard.py:1377-1380`

```python
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,  # ❌ Suppresses logs
    stderr=subprocess.PIPE,  # ❌ Hides errors
)
```

**Common error scenarios:**
```python
# forge/daemon/run.py:34-36
if not config_path.exists():
    logger.error(f"Configuration file not found: {config_path}")
    sys.exit(1)  # ❌ Error message piped away

# forge/daemon/run.py:52-54
if not api_key:
    logger.error(f"API key not found in environment: {api_key_env}")
    sys.exit(1)  # ❌ User never sees this
```

### Problem 3: No Log File Management

**Issue:**
- Daemon logs go nowhere (piped to /dev/null)
- No persistent log file created
- No way to debug after wizard exits

**Consequences:**
- Can't troubleshoot startup issues
- Can't monitor daemon operation
- No audit trail

### Problem 4: Multi-Agent Not Supported

**Issue:**
- Auto-start explicitly disabled for multi-agent configs
- User gets warning and manual instructions instead

**Code location:** `forge/cli/wizard.py:1400-1403`

```python
if "agents" in config and len(config["agents"]) > 1:
    print_warning("Auto-start not yet supported for multi-agent configurations")
    print_info(f"Run manually: {' '.join(cmd)}")
    return  # ❌ No auto-start
```

**Consequences:**
- Inconsistent experience (single vs multi-agent)
- Extra manual steps required

### Problem 5: No Status Check or Confirmation

**Issue:**
- Wizard sleeps 2 seconds and checks if process alive
- No verification that daemon actually initialized correctly
- No PID file check, no health check, no log verification

**Code location:** `forge/cli/wizard.py:1383-1389`

```python
time.sleep(2)  # ⚠️ Arbitrary wait

if process.poll() is None:
    print_success("Agent is starting!")  # ❓ Is it really?
else:
    print_error("Agent failed to start")  # ❓ Why?
```

**Consequences:**
- False positives (process alive but not working)
- False negatives (slow startup might appear as failure)
- No meaningful feedback

---

## Proposed Solutions

### Solution 1: Proper Daemonization with Log Files

**Approach:** Use nohup with proper log redirection

**Implementation:**

```python
def _offer_auto_start(self) -> None:
    """Offer to start agent daemon with proper daemonization."""
    if not ask_yes_no("Start your agent now?", default=True):
        return

    # Create logs directory
    logs_dir = Path(workspace_dir) / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "daemon.log"
    pid_file = Path(workspace_dir) / "daemon.pid"

    # Build command with nohup and log redirection
    cmd = [
        sys.executable,
        "-m",
        "forge.daemon.run",
        "--config",
        str(output_path),
    ]

    # For single agent
    if "agent" in config or len(config.get("agents", {})) == 1:
        print_info(f"Starting daemon (logs: {log_file})...")

        # Use nohup to detach from terminal
        with open(log_file, "a") as log:
            process = subprocess.Popen(
                ["nohup"] + cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # Detach from process group
            )

        # Wait a bit for initialization
        time.sleep(3)

        # Check PID file (daemon writes this on successful start)
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())

            # Verify process is actually running
            import psutil
            if psutil.pid_exists(pid):
                print_success(f"✅ Agent daemon started (PID: {pid})")
                print_info(f"📋 Logs: tail -f {log_file}")
                print_info(f"🛑 Stop: kill {pid}")
                return

        # Startup failed - show error from logs
        print_error("❌ Agent failed to start")
        print_info(f"Check logs: {log_file}")

        # Show last few lines of log
        if log_file.exists():
            print("\nLast 10 log lines:")
            print("-" * 60)
            with open(log_file) as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print(f"  {line.rstrip()}")
            print("-" * 60)

    # For multi-agent
    else:
        print_info("Starting daemons for each agent...")

        for agent_id in config["agents"].keys():
            agent_log = logs_dir / f"{agent_id}.log"

            agent_cmd = cmd + ["--agent-id", agent_id]

            with open(agent_log, "a") as log:
                subprocess.Popen(
                    ["nohup"] + agent_cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )

            print_success(f"✅ Started agent: {agent_id}")
            print_info(f"   Logs: tail -f {agent_log}")

        time.sleep(2)
        print_info("\n✨ All agents started!")
```

**Benefits:**
- ✅ Proper daemonization (detached from wizard)
- ✅ Logs persisted to file
- ✅ PID file verification
- ✅ Process health check
- ✅ Clear error messages
- ✅ Multi-agent support

### Solution 2: Add Daemon Status Command

**Create new CLI command:** `teotl status`

```python
# forge/cli/status.py
"""Check daemon status for agents."""

import sys
from pathlib import Path
import psutil

def check_daemon_status(workspace_dir: Path | None = None):
    """Check if daemon is running for an agent."""

    if workspace_dir is None:
        workspace_dir = Path.cwd()

    pid_file = workspace_dir / "daemon.pid"
    log_file = workspace_dir / "logs" / "daemon.log"

    if not pid_file.exists():
        print("❌ Daemon not running (no PID file)")
        return False

    pid = int(pid_file.read_text().strip())

    if not psutil.pid_exists(pid):
        print(f"❌ Daemon not running (stale PID: {pid})")
        pid_file.unlink()  # Clean up stale PID
        return False

    process = psutil.Process(pid)

    print(f"✅ Daemon running (PID: {pid})")
    print(f"   Status: {process.status()}")
    print(f"   CPU: {process.cpu_percent()}%")
    print(f"   Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
    print(f"   Started: {process.create_time()}")
    print(f"   Log: {log_file}")

    return True
```

**Usage:**
```bash
teotl status                    # Check current directory agent
teotl status --workspace ~/.teotl/agents/my-agent
```

### Solution 3: Improve Daemon Startup Logging

**Add startup confirmation in daemon:**

```python
# forge/daemon/run.py
async def run_daemon(config_path: Path, agent_id: str | None = None):
    """Run the agent daemon."""

    # ... existing setup ...

    # Start daemon
    logger.info("=" * 60)
    logger.info("✅ DAEMON STARTED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info(f"Agent ID: {agent_id}")
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Data Directory: {data_dir}")
    logger.info(f"Poll Interval: {poll_interval}s")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Press Ctrl+C to stop gracefully")
    logger.info("")

    # ... rest of code ...
```

**Benefits:**
- Clear startup confirmation in logs
- Easy to verify successful initialization
- Helpful debugging info

### Solution 4: Add Daemon Stop Command

**Create new CLI command:** `teotl stop`

```python
# forge/cli/stop.py
"""Stop daemon for agents."""

import signal
from pathlib import Path
import psutil

def stop_daemon(workspace_dir: Path | None = None, force: bool = False):
    """Stop daemon gracefully (or forcefully)."""

    if workspace_dir is None:
        workspace_dir = Path.cwd()

    pid_file = workspace_dir / "daemon.pid"

    if not pid_file.exists():
        print("❌ Daemon not running (no PID file)")
        return

    pid = int(pid_file.read_text().strip())

    if not psutil.pid_exists(pid):
        print(f"❌ Daemon not running (stale PID: {pid})")
        pid_file.unlink()
        return

    print(f"Stopping daemon (PID: {pid})...")

    try:
        if force:
            os.kill(pid, signal.SIGKILL)
            print("✅ Daemon killed (SIGKILL)")
        else:
            os.kill(pid, signal.SIGTERM)
            print("✅ Daemon stopped gracefully (SIGTERM)")

            # Wait for cleanup
            import time
            for i in range(10):
                if not psutil.pid_exists(pid):
                    print("✅ Daemon stopped cleanly")
                    break
                time.sleep(0.5)
            else:
                print("⚠️  Daemon still running after 5s")
                print("   Use --force to kill")

        # Clean up PID file
        if pid_file.exists():
            pid_file.unlink()

    except ProcessLookupError:
        print("✅ Daemon already stopped")
        pid_file.unlink()
```

**Usage:**
```bash
teotl stop                      # Stop gracefully (SIGTERM)
teotl stop --force              # Force kill (SIGKILL)
```

---

## Implementation Plan

### Phase 1: Fix Auto-Start (Immediate)

1. **Update wizard auto-start method** (`forge/cli/wizard.py`)
   - Use nohup with log redirection
   - Verify PID file creation
   - Show log file location
   - Handle multi-agent configs

2. **Improve daemon startup logging** (`forge/daemon/run.py`)
   - Add clear startup confirmation
   - Show all critical info (PID, workspace, etc.)

### Phase 2: Add Management Commands (Next)

1. **Add `teotl status` command**
   - Check if daemon running
   - Show process stats
   - Verify health

2. **Add `teotl stop` command**
   - Graceful shutdown (SIGTERM)
   - Force kill option (SIGKILL)

3. **Add `teotl logs` command**
   - Tail daemon logs
   - Show recent errors
   - Filter by level

### Phase 3: Enhanced UX (Future)

1. **Add daemon auto-restart on crash**
   - Systemd service file generation
   - Launchd plist for macOS
   - Windows service wrapper

2. **Add health checks**
   - Periodic ping to verify daemon alive
   - Auto-restart on failure
   - Notifications on errors

3. **Web UI for monitoring**
   - Dashboard showing all agents
   - Real-time logs
   - Start/stop controls

---

## Testing Strategy

### Test Case 1: Successful Startup

```bash
# Run wizard
teotl onboard

# Answer prompts...

# Daemon should start automatically
# Expected output:
✅ Agent daemon started (PID: 12345)
📋 Logs: tail -f ~/.teotl/agents/my-agent/logs/daemon.log
🛑 Stop: kill 12345

# Verify daemon running
teotl status
# Expected:
✅ Daemon running (PID: 12345)
```

### Test Case 2: Missing API Key

```bash
# Remove API key from environment
unset ANTHROPIC_API_KEY

# Run wizard
teotl onboard

# Daemon should fail with clear error
# Expected output:
❌ Agent failed to start
Check logs: ~/.teotl/agents/my-agent/logs/daemon.log

Last 10 log lines:
----------------------------------------------------------
ERROR - API key not found in environment: ANTHROPIC_API_KEY
----------------------------------------------------------
```

### Test Case 3: Multi-Agent

```bash
# Create multi-agent config
teotl onboard --multi-agent

# All agents should start
# Expected output:
✅ Started agent: email-assistant
   Logs: tail -f ~/.teotl/agents/email-assistant/logs/email-assistant.log
✅ Started agent: task-manager
   Logs: tail -f ~/.teotl/agents/task-manager/logs/task-manager.log
```

### Test Case 4: Status and Stop

```bash
# Check status
teotl status
# ✅ Daemon running (PID: 12345)

# Stop gracefully
teotl stop
# ✅ Daemon stopped cleanly

# Verify stopped
teotl status
# ❌ Daemon not running (no PID file)
```

---

## Summary

**Current State:**
- ❌ Daemon runs in foreground (not properly daemonized)
- ❌ Error messages suppressed and lost
- ❌ No log files created
- ❌ Multi-agent auto-start not supported
- ❌ No status/stop commands

**After Fixes:**
- ✅ Proper daemonization with nohup
- ✅ Logs persisted to files
- ✅ Clear error messages shown to user
- ✅ Multi-agent auto-start supported
- ✅ Status and stop commands available
- ✅ Better overall user experience

**Impact:**
- Users can onboard and start working immediately
- Clear feedback on success/failure
- Easy debugging when things go wrong
- Professional daemon management
- Consistent experience (single and multi-agent)

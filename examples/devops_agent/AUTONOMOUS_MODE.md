# Autonomous DevOps Agent

**Truly autonomous repository maintenance** - finds bugs, creates issues, and fixes them automatically.

## What It Does

The autonomous agent runs 24/7 and:

### Mode A: Find Bugs Automatically (MISSIONS)
- **Scans repository every hour** using:
  - `pylint` for Python code analysis
  - `pytest` for test failures
  - Static analysis tools
- **Creates GitHub issues** for bugs found
- **Schedules fixes** as high-priority tasks

### Mode B: Fix Issues Automatically (TASKS)
- **Monitors for new issues** (from missions or humans)
- **Investigates and fixes** each issue
- **Runs tests** to verify fixes
- **Creates pull requests** automatically

## Quick Start

```bash
# Set up tokens (use the keyring token with 'repo' scope)
export GITHUB_TOKEN=$(gh auth token)
export ANTHROPIC_API_KEY="sk-ant-..."

# Run autonomous agent
cd examples/devops_agent
python3 autonomous_mode.py --repo keithdit4e/devops-agent-test
```

## How It Works

```
┌─────────────────────────────────────────────────┐
│         AUTONOMOUS DEVOPS AGENT                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  📅 MISSIONS (Every hour)                       │
│  ├─ Scan repo with pylint                       │
│  ├─ Run test suite                              │
│  ├─ Find 5 most critical bugs                   │
│  └─ Create GitHub issue for each               │
│     ↓                                            │
│     └──→ Creates TASK to fix                    │
│                                                 │
│  ⚡ TASKS (Immediate)                           │
│  ├─ Monitor for new issues                      │
│  ├─ Investigate issue                           │
│  ├─ Fix the bug                                 │
│  ├─ Run tests                                   │
│  └─ Create PR                                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Commands

```bash
# Run continuously (default: scan every hour)
python3 autonomous_mode.py --repo owner/repo

# Scan more frequently (every 30 minutes)
python3 autonomous_mode.py --repo owner/repo --scan-interval 1800

# Dry run to see what would happen
python3 autonomous_mode.py --repo owner/repo --dry-run
```

## Status Monitoring

The agent prints status every 30 seconds:

```
┏━━━━━━━━━━━━━━━━━━━━━━┓
┃ Agent Status          ┃
┡━━━━━━━━━━━━━━━━━━━━━━┩
│ Pending tasks    │ 3  │
│ Completed tasks  │ 12 │
│ Current mission  │ Scanning repo... │
└──────────────────────┘
```

## Example Session

```bash
$ python3 autonomous_mode.py --repo keithdit4e/devops-agent-test

🚀 Initializing Autonomous DevOps Agent

   ✓ Data directory: ~/.forge/devops-agent/keithdit4e-devops-agent-test
   ✓ DevOps executor created
   ✓ Heartbeat daemon initialized

╭───────────────────────────────────────────╮
│ 🤖 Autonomous DevOps Agent Running        │
│ Repository: keithdit4e/devops-agent-test  │
│ Scan interval: 3600s (1h)                 │
│ Press Ctrl+C to stop                      │
╰───────────────────────────────────────────╯

🔍 Starting bug scan mission...
   Running pylint on 5 Python files...
   ✓ Found 3 potential issues

📋 Creating GitHub issues for 3 bugs...
   ✓ Created issue #20: Bug: Missing docstring in add() function
   ✓ Created task to fix issue #20

   ✓ Created issue #21: Bug: Unused variable in subtract()
   ✓ Created task to fix issue #21

🔧 Executing task: Fix keithdit4e/devops-agent-test#20
   Issue: Missing docstring in add() function
   ✓ Fixed and created PR #22

🔧 Executing task: Fix keithdit4e/devops-agent-test#21
   Issue: Unused variable in subtract()
   ✓ Fixed and created PR #23
```

## Data Storage

The agent stores data in `~/.forge/devops-agent/<repo>/`:
- `tasks.db` - Task queue and history
- `missions.db` - Mission schedules
- `agent.log` - Detailed execution logs

## Requirements

- **GitHub Token**: Must have `repo` scope
  ```bash
  gh auth status  # Check your token
  gh auth token   # Get token with correct scopes
  ```

- **Anthropic API Key**: For Claude Sonnet 4
  ```bash
  export ANTHROPIC_API_KEY="sk-ant-..."
  ```

- **Python Tools**: For scanning
  ```bash
  pip install pylint pytest
  ```

## Architecture

### HeartbeatDaemon
- Polls every 10 seconds for work
- Executes highest priority task
- Reschedules missions when due
- Handles interruptions (urgent tasks)

### DevOpsExecutor
- Creates agent for each task
- Clones repo and investigates
- Fixes issue and creates PR
- Reports success/failure

### Missions vs Tasks

| Feature | MISSIONS | TASKS |
|---------|----------|-------|
| **When** | Scheduled (hourly) | Immediate |
| **What** | Scan for new bugs | Fix specific issue |
| **Recurring** | Yes | No |
| **Can be interrupted** | Yes | No |

## Stopping the Agent

Press `Ctrl+C` to stop gracefully:

```
⚠️  Shutting down gracefully...

📈 Final Statistics:
   Tasks completed: 15
   Tasks failed: 1

👋 Autonomous agent stopped
```

## Troubleshooting

### "GITHUB_TOKEN required"
```bash
# Get your token (must have 'repo' scope)
export GITHUB_TOKEN=$(gh auth token)
```

### "Permission denied: createPullRequest"
Your token lacks `repo` scope. Check with:
```bash
gh auth status
```

Look for the token with scopes listed. Use that one:
```bash
# Get the working token
TOKEN=$(gh auth token)
export GITHUB_TOKEN="$TOKEN"
```

### Agent creates too many issues
Reduce scan frequency:
```bash
python3 autonomous_mode.py --repo owner/repo --scan-interval 7200  # 2 hours
```

## For Google Startup Challenge

This demonstrates:
- ✅ **Track 1 Requirement**: Uses MCP for GitHub operations
- ✅ **Full Autonomy**: Runs without human intervention
- ✅ **Practical Value**: Actually maintains real codebases
- ✅ **24/7 Operation**: Continuous repository monitoring
- ✅ **Intelligent**: Uses Claude Sonnet 4 for bug analysis

**Pitch**: "Your AI DevOps engineer that never sleeps - finds bugs, creates issues, fixes them, and submits PRs automatically."

## Next Steps

1. **Test on your repo**:
   ```bash
   python3 autonomous_mode.py --repo YOUR_USERNAME/YOUR_REPO
   ```

2. **Let it run overnight** - check PRs in the morning

3. **Add more scanners** - ESLint, security audits, etc.

4. **Deploy to cloud** - Run on EC2/GCP for true 24/7 operation

## Demo Video Script

1. **Show existing bugs** in test repo
2. **Start autonomous agent**
3. **Wait 30 seconds** - agent scans and finds bugs
4. **Show created issues** on GitHub
5. **Watch live** as agent fixes and creates PRs
6. **Show final PRs** ready for merge

Total demo: **2-3 minutes** ⏱️

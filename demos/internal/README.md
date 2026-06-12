# Internal Demo: Autonomous Agent System

**Status:** Alpha - Internal Use Only
**Purpose:** Demonstrate autonomous agent execution with priority scheduling
**Time:** 5-10 minutes to run

---

## What This Demonstrates

✅ **Autonomous Execution** - Agent works without human intervention
✅ **Priority Scheduling** - CRITICAL → URGENT → HIGH → NORMAL → LOW
✅ **Mission Scheduling** - Hourly, daily, weekly recurring work
✅ **Task Interruption** - Urgent work interrupts scheduled missions
✅ **Error Handling** - Graceful failures and recovery
✅ **Clean Shutdown** - Production-ready lifecycle management

---

## 🚀 NEW: Interactive Setup Wizard

**Easiest way to get started - no YAML editing required!**

```bash
# Run the onboarding wizard
python3 ../../forge_onboard.py
```

The wizard guides you through setup in 5 minutes:
- ✅ Choose your LLM provider (Anthropic/OpenAI/Ollama)
- ✅ Configure agent name and instructions
- ✅ Set up daemon polling and storage
- ✅ Configure rate limits (prevent runaway costs)
- ✅ Add tasks and missions
- ✅ Generates config.yaml automatically

**Then run your agent:**
```bash
python demo_with_config.py
```

**See full guide:** [docs/ONBOARDING_WIZARD.md](../../docs/ONBOARDING_WIZARD.md)

---

## Quick Start (Mock Provider)

**No API key needed** - uses mock responses for testing:

```bash
cd demos/internal
python examples/autonomous_agent/main.py
```

---

## Manual Setup (Alternative)

If you prefer to edit YAML directly instead of using the wizard:

### Option 1: Anthropic (Recommended)

```bash
# 1. Get API key from https://console.anthropic.com/
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# 2. Install dependencies
pip install anthropic pyyaml

# 3. Edit config.yaml (already configured for Anthropic)

# 4. Run demo
python demo_with_config.py
```

**Cost:** ~$0.60-1.50 for full demo

### Option 2: OpenAI

```bash
export OPENAI_API_KEY="sk-..."
pip install openai pyyaml

# Edit config.yaml:
#   type: openai
#   model: gpt-4o

python demo_with_config.py
```

**Cost:** ~$0.40-1.20 for full demo

### Option 3: Ollama (Free, Local)

```bash
ollama pull llama3.1
ollama serve  # Keep running

# Edit config.yaml:
#   type: ollama
#   model: llama3.1:latest

python demo_with_config.py
```

**Cost:** $0 (runs locally)

---

## Gmail Integration (Optional)

For real email integration:

```bash
# See Gmail setup guide
cat GMAIL_SETUP.md

# Quick version:
# 1. Create Google Cloud project
# 2. Enable Gmail API
# 3. Download OAuth credentials
# 4. Run: python auth_gmail.py
# 5. Edit config.yaml to enable Gmail
```

---

## Files

| File | Purpose |
|------|---------|
| `README.md` | This file |
| `config.yaml` | Configuration (provider, tasks, missions) |
| `demo_with_config.py` | Main demo script |
| `REAL_SETUP.md` | Detailed provider setup guide |
| `GMAIL_SETUP.md` | Gmail integration guide |

---

## Configuration

Edit `config.yaml` to customize:

### Provider
```yaml
provider:
  type: anthropic  # or openai, ollama
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY
```

### Tasks (Immediate Work)
```yaml
tasks:
  - description: Send welcome email
    priority: HIGH
    expires_minutes: 60
```

### Missions (Scheduled Work)
```yaml
missions:
  - description: Check for new emails
    interval: HOURLY
    can_be_interrupted: true
    interrupt_threshold: URGENT
```

### Rate Limits
```yaml
rate_limits:
  max_requests_per_minute: 10
  max_cost_per_minute: 0.50
```

---

## Expected Output

```
============================================================
🤖 Forge Autonomous Agent Demo
============================================================
📄 Configuration loaded from config.yaml
🔌 Creating anthropic provider with model claude-sonnet-4-20250514
✅ API key found in $ANTHROPIC_API_KEY
✅ Agent executor created

📅 Adding missions:
   • Check for new emails... (hourly, interruptible by URGENT+)
   • Clean up spam folder (daily, interruptible by URGENT+)

✅ Adding tasks:
   • [HIGH] Send welcome email to new user
   • [URGENT] Reply to customer support ticket #1234
   • [LOW] Archive old emails from last year

🚀 Starting autonomous agent daemon...
⏱️  Poll interval: 30s
⚠️  Press Ctrl+C to stop

INFO - Executing: Reply to customer support ticket #1234...
INFO - Execution completed successfully
📊 [1] Pending: 2 tasks | Current: Task: Send welcome email...

INFO - Executing: Send welcome email to new user...
INFO - Execution completed successfully
📊 [2] Pending: 1 tasks | Current: Mission: Check for new emails...

INFO - Executing mission: Check for new emails hourly...
INFO - Mission completed successfully
📊 [3] Pending: 1 tasks | Current: Idle

INFO - Executing: Archive old emails from last year...
INFO - Execution completed successfully
✨ All work completed!

📈 Final Statistics:
   Tasks completed: 3
   Tasks failed: 0
   Mission executions: 1
```

---

## Key Behaviors to Observe

1. **Priority Order**
   - URGENT task executes first (interrupts scheduled work)
   - HIGH task executes next
   - Mission runs after high-priority tasks
   - LOW task runs last

2. **Mission Interruption**
   - Missions can be interrupted by URGENT+ tasks
   - Configured per mission with `interrupt_threshold`

3. **Autonomous Execution**
   - No human intervention needed
   - Daemon polls every 30 seconds
   - Work happens automatically

4. **Graceful Shutdown**
   - Ctrl+C triggers clean shutdown
   - Shows final statistics
   - State persisted to disk

---

## Testing Without Real Provider

For testing daemon behavior without LLM costs:

```python
# Use mock provider (examples/autonomous_agent/main.py)
mock_provider = Mock()
mock_provider.complete = AsyncMock(
    return_value=Mock(message=Mock(content="Done", tool_calls=[]))
)
```

This simulates agent responses for testing:
- Priority scheduling
- Mission interruption
- Error handling
- Lifecycle management

---

## Troubleshooting

### "API key not set"
```bash
export ANTHROPIC_API_KEY="your-key"
echo $ANTHROPIC_API_KEY  # Verify
```

### "Module not found"
```bash
pip install anthropic pyyaml  # Or openai, ollama
```

### "Connection error"
- Check internet connection
- Verify API key is correct
- For Ollama: ensure `ollama serve` is running

### "Rate limit exceeded"
Edit `config.yaml`:
```yaml
rate_limits:
  max_requests_per_minute: 5  # Reduce
```

---

## Architecture

```
┌─────────────────────────────────────┐
│       HeartbeatDaemon               │
│  - Polls every 30s                  │
│  - Priority-based scheduling        │
│  - Mission interruption control     │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│       AgentExecutor                 │
│  - Bridges daemon → agent           │
│  - Context injection                │
│  - Timeout handling                 │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│       Agent (LLM)                   │
│  - Anthropic/OpenAI/Ollama          │
│  - Executes tasks/missions          │
│  - Returns results                  │
└─────────────────────────────────────┘
```

---

## What's Next

After successful demo:

1. **Evaluate architecture** - Does priority scheduling work?
2. **Test interruption** - Do urgent tasks interrupt missions?
3. **Check costs** - Monitor provider console
4. **Try Gmail** - Real email integration (optional)
5. **Provide feedback** - What works? What's missing?

---

## Questions?

- **Technical details:** See REAL_SETUP.md
- **Gmail setup:** See GMAIL_SETUP.md
- **Code:** See demo_with_config.py
- **Tests:** See tests/daemon/ and tests/integration/

---

**Remember:** This is alpha software for internal testing. Not ready for production deployment without permissions + budgets (next sprint).

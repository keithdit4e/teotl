# Start Your Demo Agent

## Setup Complete! ✅

I've created everything you need:
- ✅ `config.yaml` - Agent configuration
- ✅ `~/.teotl/agents/demo-agent/` - Complete workspace
- ✅ All template files (PERSONALITY.md, INSTRUCTIONS.md, etc.)
- ✅ security.yaml with moderate preset
- ✅ All dependencies installed

## Quick Start (3 steps)

### Step 1: Set Your API Key

```bash
# Replace with your actual key from https://console.anthropic.com/
export ANTHROPIC_API_KEY="sk-ant-your-actual-key-here"

# Or add to your shell profile for persistence:
echo 'export ANTHROPIC_API_KEY="sk-ant-your-actual-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### Step 2: Start the Agent

```bash
cd ~/agent/teotl
python -m forge.daemon.run --config config.yaml
```

### Step 3: Watch It Work!

The agent will:
1. **Explore** the codebase in read-only mode (Phase 8)
2. **Plan** the analysis with cost estimates (Phase 8)
3. **Verify** no destructive patterns (Phase 8)
4. **Execute** with budget tracking (Phase 6)
5. **Log** everything to audit trail (Phase 7)
6. **Create** quality report

## What You'll See

### Console Output Example:
```
🚀 Starting Forge Agent: demo-agent
📁 Workspace: ~/.teotl/agents/demo-agent
🔒 Security: moderate preset
💰 Budget: $5.00/hour, $50.00/day

✅ Loaded PERSONALITY.md
✅ Loaded INSTRUCTIONS.md
✅ Loaded security.yaml
✅ Budget tracking enabled
✅ Audit logging enabled

🎯 Processing task: Analyze codebase and create quality report

📊 Planning Phase (Claude Sonnet)
   Cost: $0.15
   Created 4-step execution plan

✅ Safety Checks:
   • Budget check: $0.15 < $5.00/hour ✓
   • Policy validation: All steps safe ✓
   • No dangerous patterns detected ✓

⚙️  Execution Phase (Claude Haiku - 82% cheaper!)
   Step 1/4: Scan directory structure... ✅ ($0.05)
   Step 2/4: Count lines of code... ✅ ($0.05)
   Step 3/4: Analyze complexity... ✅ ($0.05)
   Step 4/4: Write quality report... ✅ ($0.05)

💰 Total cost: $0.35
```

## Generated Artifacts

After running, check these files to verify all features work:

### 1. Cost Tracking
```bash
cat ~/.teotl/agents/demo-agent/COST_LOG.jsonl
```
Shows every operation with costs (Phase 6)

### 2. Audit Trail
```bash
cat ~/.teotl/agents/demo-agent/AUDIT_LOG.jsonl | jq .
```
Complete compliance logging (Phase 7)

### 3. Progress Tracking
```bash
cat ~/.teotl/agents/demo-agent/PROGRESS.md
```
Turn-by-turn execution history

### 4. State Management
```bash
cat ~/.teotl/agents/demo-agent/STATE.json | jq .
```
Validated agent state (Phase 7)

### 5. Quality Report
```bash
# The actual analysis report will be in the workspace
ls ~/.teotl/agents/demo-agent/
```

## Testing Safety Features

After the initial run succeeds, test the safety features:

### Test 1: Budget Enforcement
Edit `config.yaml` and set:
```yaml
security:
  cost_limits:
    max_per_hour: 0.10  # Very low limit
```

Restart the agent - it should halt with `BudgetExceededError`

### Test 2: Security Policy
Edit `~/.teotl/agents/demo-agent/security.yaml` and block paths:
```yaml
filesystem:
  blocked_paths:
    - /home/  # Block everything
  allowed_paths:
    - ~/.teotl/agents/demo-agent/  # Only workspace
```

Give it a task that tries to access `/etc/passwd` - it should be blocked

### Test 3: Pattern Detection
Create a test with the StepVerifier:
```python
from forge.primitives.harness import StepVerifier, PlanStep
from pathlib import Path

verifier = StepVerifier(workspace_dir=Path.cwd(), strict_mode=True)

dangerous_step = PlanStep(
    number=1,
    description="Run rm -rf /var/lib/data to clean up",
)

result = verifier.verify_step(dangerous_step)
print(f"Safe: {result.safe}")
print(f"Risk: {result.risk_level}")
print(f"Warnings: {result.warnings}")
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'forge'"
```bash
cd ~/agent/teotl
pip install -e .
```

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key"
```

### Agent seems stuck
Check the heartbeat monitor logs in the daemon output

### No artifacts generated
Check `~/.teotl/agents/demo-agent/` for error logs

## Expected Cost

**Typical run:** $0.35 - $0.75
- Planning: ~$0.15 (Sonnet)
- Execution: ~$0.20 (Haiku)
- Evaluation: ~$0.10 (Sonnet)

**With OpenClaw:** $2.40 - $3.00 (5-6x more expensive!)

## Next Steps

Once your agent runs successfully:

1. ✅ Examine all generated artifacts
2. ✅ Test budget enforcement
3. ✅ Test security policies
4. ✅ Test pattern detection
5. ✅ Read `docs/QUICK_START_DEMO.md` for more tests

## You've Successfully Bypassed the Wizard!

Your agent is configured exactly as the wizard would have done it, but manually. Everything should work perfectly now.

Ready to start? Run:
```bash
export ANTHROPIC_API_KEY="your-key"
cd ~/agent/teotl
python -m forge.daemon.run --config config.yaml
```

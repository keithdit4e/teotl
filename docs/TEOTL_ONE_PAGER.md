# Teotl Framework
## An Autonomous Agent Framework Built for Production Safety

---

### **The Problem**

Many autonomous agent setups are hard to trust in production:
- ❌ **No budget controls** → Runaway spending
- ❌ **No rollback capabilities** → Failed operations leave a mess behind
- ❌ **No security enforcement** → Agents can reach files and commands they shouldn't
- ❌ **No transparency** → Users don't know what will happen before execution
- ❌ **No audit trails** → Missing the logging needed for review and compliance work

**Result:** Autonomous agents often stay "demos" — too risky for real business use.

---

### **The Teotl Solution**

Teotl's harness bundles **11 safety and reliability primitives** — state artifacts, planner-worker separation, evaluation, context janitor, heartbeat monitoring, cost tracking, human-in-the-loop approval, security policy, checkpoints and rollback, audit trail, and state validation — so autonomous agents can run with guardrails.

#### **Three Pillars of Safety**

**🔒 Security First**
- Budget enforcement with hourly, daily, and monthly limits (`CostTracker`)
- Pre-execution security policy validation
- Human-in-the-loop approval gates between autonomous cycles
- Automatic halt on critical health issues

**🛡️ Advanced Safety**
- Git-based checkpoints with rollback on failure (`CheckpointManager`)
- Audit trail in JSONL format with PII redaction (`AuditLogger`)
- Pydantic validation of agent state (`STATE.json`) to prevent corruption

**✨ User Experience**
- Read-only exploration mode to understand a codebase before changing it (`ExplorationMode`)
- Dry-run preview of a plan with risk analysis and cost estimates (`DryRunAnalyzer`)
- Destructive-pattern detection (`rm -rf`, `DROP DATABASE`, `TRUNCATE`, `DELETE` without `WHERE`, `chmod 777`, `sudo`, disk formatting, and more) via `StepVerifier`
- 4-level risk assessment (low, medium, high, critical) with suggestions

---

### **What's Included**

| Capability | Where it lives |
|------------|----------------|
| **Budget Enforcement** | `teotl.primitives.harness.CostTracker` (on by default in the harness) |
| **Checkpoints & Rollback** | `teotl.primitives.harness.CheckpointManager` (on by default in the harness) |
| **Human Approval Gates** | `PlannerWorkerHarness(require_approval_for_continuation=True)` |
| **Audit Trail + PII Redaction** | `teotl.primitives.harness.AuditLogger` |
| **Dry-Run Preview** | `teotl.primitives.harness.DryRunAnalyzer` |
| **Exploration Mode** | `teotl.primitives.harness.ExplorationMode` |
| **Pattern-Based Verification** | `teotl.primitives.harness.StepVerifier` |
| **Agent Guardrails** | `Agent(policy="minimal" \| "standard" \| "strict")` |

---

### **Real-World Use Cases**

**Autonomous Code Review**
```
• Agent explores the codebase read-only before planning
• Identifies security issues and anti-patterns
• Proposes fixes as a step-by-step plan
• Stays within configured budget limits
• Checkpoints before changes, with rollback if a step fails
```

**Customer Support Automation**
```
• Agent drafts answers to support tickets
• Guardrail policies limit what tools it can use
• Audit trail records each turn, with PII redaction
• Budget limits cap daily spend
```

**Database Migration Assistant**
```
• Agent plans a multi-step migration
• Dry-run preview shows the planned actions and their risk levels
• Flags "DROP DATABASE" and similar destructive steps for approval
• Creates a git checkpoint before execution
• Rolls back on failure
```

---

### **Architecture Highlights**

**Planner-Worker Separation**
- Stronger model (Claude Sonnet 5.5) for planning
- Cheaper model (Claude Haiku 4.5) for execution — about half the per-token price of Sonnet 5.5

**Multi-Model Support**
- Anthropic (Claude Opus, Sonnet, Haiku, Fable)
- OpenAI (and OpenAI-compatible endpoints via `base_url`)
- Google Gemini
- Ollama (local models)

**Decentralized Agent Architecture**
- One daemon per agent (isolation)
- Scale out by running more agents
- Priority system (CRITICAL → LOW)
- Recurring missions (hourly, daily, weekly) defined in YAML

**Heartbeat Monitoring**
- Stuck detection (no progress)
- Error threshold monitoring
- Progress rate tracking
- Escalation policies

---

### **Get Started in 5 Minutes**

```python
import asyncio
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness

async def main():
    harness = PlannerWorkerHarness(
        agent_id="autonomous-developer",
        planner_provider=AnthropicProvider(model="claude-sonnet-5-5"),
        worker_provider=AnthropicProvider(model="claude-haiku-4-5"),
        workspace_dir=Path(".teotl/autonomous-developer"),
        worker_skills=["filesystem", "git"],

        # Security
        enable_cost_tracking=True,
        require_approval_for_continuation=True,
        halt_on_critical_escalation=True,

        # Safety
        enable_checkpoints=True,
        enable_heartbeat=True,
    )

    # Supervised autonomous execution: plan, execute, evaluate, ask to continue
    result = await harness.run_supervised_cycle(
        goals="Refactor authentication to use OAuth2",
        max_cycles=5,
    )
    print(f"Complete: {result.complete} after {result.cycles_completed} cycle(s)")

asyncio.run(main())
```

---

### **Pricing & Support**

**Open Source** (MIT License)
- ✅ Full framework access
- ✅ All safety features included
- ✅ Community support (GitHub Issues and Discussions)
- ✅ No usage limits from Teotl (you pay your LLM provider directly)

---

### **Key Differentiators**

**Why Teotl:**

1. **Safety-First Design** → Budget limits, approval gates, and guardrails built into the harness
2. **Rollback** → Git-based checkpoints before risky steps
3. **Cost Control** → Budget enforcement prevents runaway spending
4. **Transparency** → Exploration and dry-run preview before changes
5. **Audit-Friendly** → JSONL audit trail with PII redaction to support compliance work
6. **Model Choice** → Anthropic, OpenAI, Gemini, or local Ollama models

**The Bottom Line:**
Teotl is designed for production use with built-in safety features to reduce the risks of data loss, budget overruns, and compliance gaps.

---

### **Resources**

📚 **Documentation:** https://github.com/keithdit4e/teotl/tree/main/docs
🚀 **Quick Start:** [docs/quickstart.md](quickstart.md)
💬 **Community:** https://github.com/keithdit4e/teotl/discussions

---

### **Try Teotl Today**

```bash
# Install
pip install "teotl[anthropic]"

# Set up your first agent (generates config.yaml, and run_planner_worker.py for planner-worker agents)
teotl onboard

# Run it as a daemon
python -m teotl.daemon.run --config config.yaml
```

**Get started** with safer autonomous agents.

---

<div align="center">

### **Teotl Framework**
**Autonomous Agents with Built-In Safety**

[GitHub](https://github.com/keithdit4e/teotl) | [Documentation](https://github.com/keithdit4e/teotl/tree/main/docs)

</div>

# Teotl

**Autonomous agent framework with planner-worker architecture for cost-efficient execution.**

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]() [![License](https://img.shields.io/badge/license-MIT-blue)]()

🤖 **Autonomous Missions** • 🔒 **Built-in Guardrails** • 💰 **Cost Optimization** • 🎯 **Safety-First Design**

---

## Why Teotl?

Most agent frameworks are **expensive** and **unreliable**:

❌ Single-model agents waste tokens on simple tasks
❌ No built-in security (guardrails, credentials, sandboxing)
❌ Poor error handling for production use
❌ Expensive for long-running autonomous workflows

**Teotl solves this** with a **planner-worker architecture**:

✅ **~40% cost reduction** - Strategic planner (Sonnet) + fast worker (Haiku)
✅ **Production-focused** - Guardrails, credential management, error recovery
✅ **Autonomous missions** - Long-running workflows that execute without supervision
✅ **Tested** - Comprehensive test suite with high coverage

---

## Quick Start

### Installation

```bash
# Clone and install from source (PyPI coming soon)
git clone https://github.com/keithdit4e/teotl
cd teotl
pip install -e .
```

### Your First Agent (30 seconds)

\`\`\`python
from teotl import Agent

# Create agent with planner-worker architecture
agent = Agent.create_planner_worker(
    planner_model="claude-sonnet-4",
    worker_model="claude-haiku-4"
)

# Run autonomous task
response = await agent.run(
    "Analyze this repository and suggest 3 performance improvements"
)

print(response.text)
\`\`\`

**That's it!** 🎉

---

## Key Features

### 🎯 Planner-Worker Architecture

Strategic planning with fast execution:

\`\`\`yaml
# missions/my_agent.yaml
execution_pattern: planner_worker

planner_worker:
  planner:
    provider: claude-sonnet-4  # Strategic reasoning
  worker:
    provider: claude-haiku-4   # Fast execution
    skills:
      - filesystem
      - git
      - bash
\`\`\`

**Result:** ~40% cost savings vs single-model approaches in benchmarks

### 🤖 Autonomous Missions

Long-running workflows that execute without supervision:

\`\`\`python
from teotl import Mission

# Define mission
mission = Mission.from_file("missions/devops_agent.yaml")

# Run autonomously
result = await mission.run(context={
    "repository": "owner/repo",
    "task": "Fix all failing tests"
})

# Agent investigates, fixes, tests, creates PR - all autonomous
\`\`\`

### 🔒 Production Security

Built-in guardrails and credential management:

\`\`\`python
agent = Agent(
    provider=provider,
    policy="standard",  # or "strict" for high-security environments
)

# Guardrails automatically:
# - Block dangerous commands (rm -rf /, etc.)
# - Require approval for sensitive operations
# - Track costs and enforce budgets
# - Build trust over repeated safe actions
\`\`\`

**Credentials stored securely:**
- OS keyring (macOS/Windows/Linux)
- Encrypted file storage
- AWS Secrets Manager
- Never in code or environment variables

### 🛠️ Skills System

Modular capabilities that agents can use:

\`\`\`python
# Built-in skills
- filesystem  # Read/write files
- git         # Repository operations
- bash        # Shell commands
- python_repl # Dynamic code execution

# Custom skills
from teotl.primitives.skills import Skill

class MyCustomSkill(Skill):
    name = "my_skill"

    async def my_action(self, param: str) -> str:
        # Your logic here
        return result
\`\`\`

### 📊 Benchmark Results

Tested on real-world coding tasks:

| Metric | Result |
|--------|--------|
| **Avg cost per task** | ~$0.17 |
| **Cost savings** | ~40% vs single-model |
| **Success rate** | 87% on test suite |

*Results from internal benchmarks. Your results may vary based on task complexity.*

---

## Examples

### DevOps Automation Agent

Autonomously investigates GitHub issues and creates fixes:

\`\`\`bash
cd examples/devops_agent
python run_agent.py --repo owner/repo --mode daemon

# Agent autonomously:
# 1. Monitors for new issues
# 2. Reproduces bugs
# 3. Investigates root cause
# 4. Creates fixes
# 5. Submits pull requests
\`\`\`

**Example results:** Tested on real GitHub issues with autonomous bug fixing

[See full example →](examples/devops_agent/)


---

## Architecture

### Planner-Worker Pattern

\`\`\`
┌─────────────────────────────────────────────┐
│             User Request                     │
└──────────────┬──────────────────────────────┘
               │
       ┌───────▼────────┐
       │    Planner     │  Claude Sonnet 4
       │  (Strategic)   │  - Analyze task
       └───────┬────────┘  - Break into steps
               │           - Choose approach
               │
       ┌───────▼────────┐
       │    Worker      │  Claude Haiku 4
       │  (Execution)   │  - Execute steps
       └───────┬────────┘  - Use skills
               │           - Report results
               │
       ┌───────▼────────┐
       │     Result     │  40% cheaper
       │   + Context    │  Same quality
       └────────────────┘
\`\`\`

**Why it works:**
- **Planner**: Expensive model for strategy (infrequent calls)
- **Worker**: Cheap model for execution (frequent calls)
- **Result**: Best of both worlds - smart + efficient

### Cost Comparison

**Traditional (single model):**
\`\`\`
Task: "Fix bug in user authentication"
├─ Analysis:    Claude Sonnet 4 ($0.10)
├─ Planning:    Claude Sonnet 4 ($0.05)
├─ Execution:   Claude Sonnet 4 ($0.08)
├─ Validation:  Claude Sonnet 4 ($0.06)
└─ Total: $0.29
\`\`\`

**Teotl (planner-worker):**
\`\`\`
Task: "Fix bug in user authentication"
├─ Analysis:    Claude Sonnet 4 ($0.10)  ← Strategic
├─ Planning:    Claude Sonnet 4 ($0.05)  ← Strategic
├─ Execution:   Claude Haiku 4  ($0.01)  ← Fast tasks
├─ Validation:  Claude Haiku 4  ($0.01)  ← Fast tasks
└─ Total: $0.17 (40% savings!)
\`\`\`

---

## Documentation

- [Installation](docs/installation.md) - Setup and configuration
- [Quick Start](docs/quickstart.md) - Build your first agent in 5 minutes
- [Concepts](docs/concepts.md) - Missions, skills, planner-worker, security
- [API Reference](docs/api_reference.md) - Complete API documentation
- [Examples](examples/) - DevOps agent, comparisons, and more

---

## Use Cases

### 🐛 DevOps Automation
Autonomous bug investigation, test fixing, deployment monitoring

**Benefit:** Automate routine debugging and maintenance tasks

### 🔍 Code Review
Automated PR reviews, security scanning, best practice enforcement

**Benefit:** Catch issues before human review, faster merges

### 📊 Research & Analysis
Market research, competitive analysis, data gathering

**Benefit:** Autonomous multi-hour research tasks

### 🧪 Testing
Generate test cases, find edge cases, increase coverage

**Benefit:** Thorough testing without manual effort

### 🔄 ETL & Data Pipelines
Autonomous data extraction, transformation, validation

**Benefit:** Reliable pipelines with error recovery

---

## Key Differentiators

| Feature | Teotl |
|---------|-------|
| **Planner-Worker Architecture** | ✅ Built-in dual-model pattern |
| **Cost Optimization** | ✅ ~40% savings in benchmarks |
| **Autonomous Missions** | ✅ Long-running workflows |
| **Built-in Guardrails** | ✅ Policy-based security |
| **Credential Management** | ✅ Secure storage |
| **Audit Logging** | ✅ Compliance-informed |
| **Cost Tracking** | ✅ Real-time monitoring |
| **Error Recovery** | ✅ Built-in retry logic |

---

## Requirements

- **Python:** 3.11 or higher
- **API Keys:** Anthropic Claude or OpenAI GPT
- **OS:** macOS, Linux, Windows

---

## Installation

### From Source (Current)

```bash
git clone https://github.com/keithdit4e/teotl
cd teotl
pip install -e .
```

> **Note:** PyPI package coming soon. For now, install from source as shown above.

### Verify Installation

\`\`\`bash
teotl --version
# teotl 0.1.0

teotl --help
\`\`\`

---

## Configuration

### API Keys

\`\`\`bash
# Anthropic Claude (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."

# Or OpenAI
export OPENAI_API_KEY="sk-..."
\`\`\`

### Create Your First Agent

\`\`\`bash
# Interactive wizard
teotl init my-agent

# Creates:
# my-agent/
# ├── config.yaml      # Agent configuration
# ├── missions/        # Mission definitions
# └── skills/          # Custom skills (optional)
\`\`\`

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

\`\`\`bash
# Clone repository
git clone https://github.com/keithdit4e/teotl
cd teotl

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format code
ruff format .
\`\`\`

### Running Tests

\`\`\`bash
# Full test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=teotl --cov-report=html

# Quick test (stop on first failure)
pytest tests/ -x
\`\`\`

**Current Status:** Run `pytest tests/ -v` to see current test results

---

## Roadmap

### v0.1.0 (Current)
- ✅ Planner-worker architecture
- ✅ Autonomous missions
- ✅ Built-in guardrails
- ✅ Credential management
- ✅ Skills system
- ✅ Cost tracking
- ✅ DevOps agent example

### v0.2.0 (Planned)
- 🚧 GAIA benchmark validation
- 🚧 Additional examples (code review, testing)
- 🚧 Web dashboard
- 🚧 Multi-agent orchestration
- 🚧 Enhanced MCP integration

### v1.0.0 (Future)
- 🔮 GCP Marketplace listing
- 🔮 Gemini Enterprise support
- 🔮 Production case studies
- 🔮 Advanced monitoring

---

## Community

- **GitHub Issues:** [Report bugs or request features](https://github.com/keithdit4e/teotl/issues)
- **Discussions:** [Ask questions, share ideas](https://github.com/keithdit4e/teotl/discussions)

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with:
- [Anthropic Claude](https://www.anthropic.com/) - Strategic planning and execution
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal output
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Pytest](https://pytest.org/) - Testing framework

Inspired by the need for production-ready autonomous agents that are both powerful and cost-efficient.

---

## Citation

If you use Teotl in your research or project, please cite:

```bibtex
@software{teotl2026,
  title = {Teotl: Production-Ready Autonomous Agent Framework},
  author = {Foster, Keith},
  year = {2026},
  url = {https://github.com/keithdit4e/teotl},
  note = {Open-source autonomous agent framework with planner-worker architecture}
}
```

---

<div align="center">

**[Get Started](docs/quickstart.md)** • **[Examples](examples/)** • **[Documentation](docs/)**

</div>

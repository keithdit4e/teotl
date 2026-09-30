# Teotl

**An autonomous agent framework for Python: planner-worker execution, built-in guardrails, and any LLM provider.**

[![PyPI](https://img.shields.io/pypi/v/teotl)](https://pypi.org/project/teotl/)
[![Python](https://img.shields.io/pypi/pyversions/teotl)](https://pypi.org/project/teotl/)
[![CI](https://github.com/keithdit4e/teotl/actions/workflows/ci.yml/badge.svg)](https://github.com/keithdit4e/teotl/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Teotl splits agent work between a **planner** (a strong model that runs once to write a step-by-step plan) and a **worker** (a cheaper, faster model that executes each step). Every tool call passes through a policy-based guardrail layer before it runs, and a harness keeps plans, progress, costs, and audit logs on disk so long-running missions can pause, resume, and be inspected.

> **Status:** alpha (v0.2.0). APIs may change between minor versions.

## Features

- **Planner-worker harness**: plan once with a capable model, execute many steps with a cheap one
- **Guardrails**: `minimal` / `standard` / `strict` policies, bash command analysis, prompt-injection checks, rate and cost limits, progressive trust
- **Multi-provider**: Anthropic Claude, OpenAI, Google Gemini, Ollama (local), or LiteLLM
- **Your own tools and skills**: register Python functions as tools (with per-tool risk levels) and add `SKILL.md` skills with scripts; skills load on demand to keep prompts small
- **Memory**: optional local vector memory with automatic context compaction
- **Harness artifacts**: `PLAN.md`, `PROGRESS.md`, state checkpoints, cost tracking, append-only audit log
- **Credentials**: OS keyring, encrypted file, or AWS Secrets Manager storage
- **CLI and dashboard**: interactive chat, onboarding wizard, and a web dashboard for monitoring agents

## Installation

```bash
pip install "teotl[anthropic]"
```

Pick the extras you need:

| Extra | Adds |
|-------|------|
| `anthropic` | Claude models |
| `openai` | OpenAI models |
| `google` | Gemini models |
| `ollama` | Local models via Ollama |
| `litellm` | Any provider via LiteLLM |
| `memory` | Vector memory (sentence-transformers, sqlite-vec) |
| `security` | OS keyring and encrypted credential storage |
| `web` | Web dashboard |
| `aws` | AWS Secrets Manager credential backend |
| `all` | Everything above |

Requires Python 3.11 or newer.

## Quick start

Set an API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### A single agent

```python
import asyncio

from teotl import Agent
from teotl.core.provider import AnthropicProvider


async def main():
    agent = Agent(
        provider=AnthropicProvider(model="claude-sonnet-5-5"),
        instructions="You are a careful code reviewer.",
        skills=["filesystem", "git"],
        policy="standard",  # or "strict" / "minimal"
    )
    response = await agent.run("Summarize the last 5 commits in this repo.")
    print(response.text)
    print(f"Cost: ${response.cost:.4f}")


asyncio.run(main())
```

### Planner-worker

```python
import asyncio
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness


async def main():
    harness = PlannerWorkerHarness(
        agent_id="code-quality",
        planner_provider=AnthropicProvider(model="claude-sonnet-5-5"),        # plans once
        worker_provider=AnthropicProvider(model="claude-haiku-4-5"),  # executes each step
        workspace_dir=Path(".teotl/code-quality"),
        worker_skills=["filesystem", "git"],
    )

    plan = await harness.plan(goals="Add type hints and docstrings to public functions in src/.")
    print(f"Plan has {plan.total_steps} steps (see PLAN.md)")

    while not harness.is_complete():
        result = await harness.execute_next_step()
        print(f"Step {result.step.number}: {'ok' if result.success else result.error}")


asyncio.run(main())
```

The harness writes `PLAN.md` and `PROGRESS.md` into the workspace, so you can read, edit, or resume a plan at any point. Plans use as few steps as the goal needs (at most `max_plan_steps`, default 8). A step is marked done only on evidence: the worker reports `STEP_STATUS: DONE`, it actually used tools, none were blocked or failed, and the target file exists. Failed steps are retried with feedback, then marked skipped.

### Other providers

```python
from teotl.core.provider import GeminiProvider, OllamaProvider, OpenAIProvider

OpenAIProvider(model="gpt-5.6-terra")        # OPENAI_API_KEY
GeminiProvider(model="gemini-3.8-flash")     # GOOGLE_API_KEY
OllamaProvider(model="llama3.1")             # local, no key
```

You can mix providers, for example a Claude planner with a local Ollama worker. For a cheap worker, use `claude-haiku-4-5`, `gpt-5.6-luna` or `gemini-3.5-flash-lite`.

## Command line

```bash
teotl --help
teotl onboard      # interactive setup wizard: provider, skills, policy, planner-worker config
teotl chat         # interactive chat with an agent
teotl security     # manage credentials and security settings
```

## Guardrails

Every tool call is classified and checked against a policy **before** it executes. This happens outside the model's context, so a prompt can't talk its way past it.

- `strict`: read-only by default; writes and shell commands need approval
- `standard`: common development actions allowed; destructive or sensitive actions need approval
- `minimal`: for trusted sandboxes

Built-in protections include bash command analysis (for example blocking `rm -rf /` and piping remote scripts to a shell), prompt-injection checks on instructions and incoming messages, per-agent rate and cost limits, and a trust score that grows with repeated safe behavior. See [docs/GUARDRAILS.md](docs/GUARDRAILS.md).

## Your own skills and tools

Teotl is built to be extended. Add **tools** (Python functions the model can call) and **skills** (instructions, plus optional scripts, that teach the model how to do a task). They work with every provider: Claude, OpenAI, Gemini, and Ollama (with a model that supports tool calling).

### Tools

```python
def lookup_order(order_id: str) -> str:
    return f"Order {order_id}: shipped"  # call your database or API here

agent.register_tool(
    name="lookup_order",
    description="Look up an order's status by ID",
    handler=lookup_order,  # a regular or async function
    parameters={
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
    },
    risk="low",  # "medium" or "high" asks for confirmation under the standard policy
)
```

Declare `risk="medium"` or higher for anything that changes data or contacts people, so guardrails ask before it runs.

### Skills

A skill is a folder with a `SKILL.md` file (YAML frontmatter plus instructions), and optionally scripts or reference files:

```
~/.teotl/skills/invoice-report/
├── SKILL.md
└── scripts/report.py
```

```markdown
---
name: invoice-report
description: Summarize unpaid invoices
triggers: [unpaid invoices]
---
Run `python scripts/report.py` from the skill directory, then summarize the output.
```

```python
agent = Agent(provider=provider, skills=["invoice-report", "filesystem"])
```

Only each skill's one-line description is in the prompt until it's needed. The skill's full instructions (with its directory path) are loaded when your message names it or matches a trigger, or when the model calls the built-in `load_skill` tool.

Teotl looks for skills in:

1. the skills bundled with the package (`filesystem`, `git`, `github`, `web`, `claude_code`, `spec_kit`)
2. `~/.teotl/skills/` (move the data directory with `TEOTL_HOME`)
3. any directories listed in `TEOTL_SKILLS_PATH` (colon-separated)

See [docs/CUSTOM_SKILLS_QUICKSTART.md](docs/CUSTOM_SKILLS_QUICKSTART.md) and [docs/SKILLS_GUIDE.md](docs/SKILLS_GUIDE.md).

## Examples

| Example | What it shows |
|---------|---------------|
| [`examples/planner_worker_demo.py`](examples/planner_worker_demo.py) | Planner-worker plan and execute loop |
| [`examples/devops_agent/`](examples/devops_agent/) | Agent that triages GitHub issues and proposes fixes |
| [`examples/supervisor_demo.py`](examples/supervisor_demo.py) | Supervised execution with approvals |
| [`examples/custom_skill_example.py`](examples/custom_skill_example.py) | Writing your own skill |
| [`examples/full_config_reference.yaml`](examples/full_config_reference.yaml) | Every YAML configuration option |
| [`examples/social_media_agent.yaml`](examples/social_media_agent.yaml) | Content-drafting agent that writes social posts to files |

## Documentation

- [Getting started](docs/GETTING_STARTED.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Guardrails](docs/GUARDRAILS.md) and [security guide](docs/SECURITY_GUIDE.md)
- [Memory](docs/MEMORY.md)
- [Model strategy](docs/MODEL_STRATEGY.md)
- [Multi-agent guide](docs/MULTI_AGENT_GUIDE.md)

## Roadmap

- [x] Planner-worker harness
- [x] Guardrails, credential storage, audit log, cost tracking
- [x] Anthropic, OpenAI, Gemini, Ollama, LiteLLM providers
- [x] YAML configuration for multi-agent setups
- [ ] Published benchmark results (GAIA and cost comparisons)
- [ ] More end-to-end examples (code review, test generation)
- [ ] Deeper MCP integration

## Contributing

Bug reports, ideas, and pull requests are welcome.

- Questions and ideas: [Discussions](https://github.com/keithdit4e/teotl/discussions)
- Bugs and feature requests: [Issues](https://github.com/keithdit4e/teotl/issues)
- Code: see [CONTRIBUTING.md](CONTRIBUTING.md)

```bash
git clone https://github.com/keithdit4e/teotl
cd teotl
pip install -e ".[dev,anthropic]"
pytest
```

Report security issues privately. See [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © Keith Foster

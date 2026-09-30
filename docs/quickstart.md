# Quick Start Guide

Build your first Teotl agent in 5 minutes.

## Prerequisites

- Python 3.11+ installed
- Teotl installed: `pip install "teotl[anthropic]"` (see [Installation](installation.md))
- API key configured: `export ANTHROPIC_API_KEY="sk-ant-..."`

## Your First Agent (30 Seconds)

Create a simple agent that can chat with you:

```python
import asyncio
from teotl import Agent
from teotl.core.provider import AnthropicProvider

async def main():
    # Create provider (reads ANTHROPIC_API_KEY from the environment)
    provider = AnthropicProvider(model="claude-sonnet-5-5")

    # Create agent
    agent = Agent(
        provider=provider,
        instructions="You are a helpful AI assistant.",
    )

    # Run agent
    response = await agent.run("Hello! What can you help me with?")
    print(response.text)

asyncio.run(main())
```

`agent.run()` returns a `Response` with `text`, `messages`, `tool_calls_made`, `tokens_used`, and `cost`.

## Planner-Worker Architecture (Lower Cost)

Use a stronger model to plan and a cheaper model to execute each step with `PlannerWorkerHarness`:

```python
import asyncio
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness

async def main():
    harness = PlannerWorkerHarness(
        agent_id="code-quality",
        planner_provider=AnthropicProvider(model="claude-sonnet-5-5"),  # strategic
        worker_provider=AnthropicProvider(model="claude-haiku-4-5"),    # fast execution
        workspace_dir=Path(".teotl/code-quality"),
        worker_skills=["filesystem", "git"],
    )

    # Planner writes a step-by-step PLAN.md into the workspace
    await harness.plan(goals="Analyze the files in the current directory and suggest improvements")

    # Worker executes the plan one step at a time
    while not harness.is_complete():
        result = await harness.execute_next_step()
        status = "ok" if result.success else f"failed: {result.error}"
        print(f"Step {result.step.number}: {status}")

asyncio.run(main())
```

**Why this costs less:**
- **Planner:** Sonnet 5.5 handles planning (called infrequently)
- **Worker:** Haiku 4.5 executes steps (called frequently) at about half the per-token price of Sonnet 5.5

Other harness methods: `execute_all_steps()`, `get_progress()`, `refine_plan(feedback)`, `reset()`, and `run_supervised_cycle(goals=...)`.

## Adding Skills (Tool Use)

Skills are passed to the agent as a list of skill names. The agent also registers a `bash` tool automatically.

```python
import asyncio
from teotl import Agent
from teotl.core.provider import AnthropicProvider

async def main():
    provider = AnthropicProvider(model="claude-sonnet-5-5")

    agent = Agent(
        provider=provider,
        instructions="You are a coding assistant with file and shell access.",
        skills=["filesystem", "git"],
    )

    response = await agent.run("Read the README.md file and summarize it")
    print(response.text)

asyncio.run(main())
```

**Bundled skills:**
- `filesystem` - Read/write files
- `git` - Repository operations
- `github` - Repositories, issues, and pull requests
- `web` - Fetch pages, download files, HTTP requests
- `claude_code` - Coding tasks via the Claude Code CLI
- `spec_kit` - Structured specifications for planning
- `social-media` - Cross-post content (LinkedIn, X, Medium, Substack)

Skills are folders containing a `SKILL.md` file. Teotl looks for them in its bundled skills, `~/.teotl/skills/`, and any directories listed in `TEOTL_SKILLS_PATH`. See [Custom Skills](CUSTOM_SKILLS_QUICKSTART.md) to write your own.

## Adding Security (Guardrails)

Every agent runs with a guardrail policy. The default is `"standard"`:

```python
import asyncio
from teotl import Agent
from teotl.core.provider import AnthropicProvider

async def main():
    provider = AnthropicProvider(model="claude-sonnet-5-5")

    agent = Agent(
        provider=provider,
        instructions="You are a helpful assistant.",
        skills=["filesystem"],
        policy="strict",  # "minimal", "standard" (default), or "strict"
    )

    # Tool calls are checked against the policy before they run
    response = await agent.run("List the files in the current directory")
    print(response.text)

asyncio.run(main())
```

**Policy levels:**
- `minimal` - Fewest restrictions
- `standard` - Balanced security (default, recommended)
- `strict` - Maximum restrictions

You can also pass a `teotl.primitives.guardrails.Policy` object or a `Path` to a policy file. See [Guardrails](GUARDRAILS.md).

## Adding Memory (Context Persistence)

Give your agent long-term memory with `LocalMemory` (requires `pip install "teotl[memory]"`). Before each run, the agent recalls memories relevant to the message and adds them to its context.

```python
import asyncio
from teotl import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.memory.local import LocalMemory

async def main():
    provider = AnthropicProvider(model="claude-sonnet-5-5")
    memory = LocalMemory()

    agent = Agent(
        provider=provider,
        instructions="You are a helpful assistant with long-term memory.",
        memory=memory,
    )

    # Store a fact explicitly
    await agent.remember("The user's name is Alice and she loves Python programming.", importance=8)

    # Relevant memories are recalled into context automatically
    response = await agent.run("What's my name and what do I like?")
    print(response.text)

    memory.close()

asyncio.run(main())
```

Other memory methods on the agent: `recall(query)`, `forget(...)`, `list_memories()`. You can inspect stored memories from the command line with `teotl memory list`, `teotl memory search`, and `teotl memory stats`. See [Memory](MEMORY.md).

## Autonomous Missions

Missions are recurring scheduled work run by the Teotl daemon. Define them in the daemon's config YAML:

```yaml
missions:
  - description: "Weekly code quality review"
    interval: WEEKLY   # HOURLY, DAILY, WEEKLY
    can_be_interrupted: true
    interrupt_threshold: URGENT
```

Then run the daemon:

```bash
python -m teotl.daemon.run --config config.yaml
```

See [examples/full_config_reference.yaml](../examples/full_config_reference.yaml) for the full config schema. The easiest way to generate a config is `teotl onboard` (below).

## Interactive CLI Mode

Use Teotl from the command line:

```bash
# Start interactive chat
teotl chat

# Chat with skills (comma-separated or repeated --skills)
teotl chat --skills filesystem,git

# Chat as a specific agent (loads its workspace files)
teotl chat --agent my-agent

# Chat without memory
teotl chat --no-memory
```

**Interactive commands:**
```
/help         Show available commands
/skills       List loaded skills
/memory       Show memory status
/clear        Clear the screen
/exit, /quit  Exit
```

## Using the Onboarding Wizard

Interactive setup for your first agent:

```bash
teotl onboard    # or: teotl wizard
```

The wizard guides you through API key setup, agent naming, execution pattern (planner-worker vs single agent), model selection, skills, and security settings. It generates a `config.yaml` for the daemon and, for planner-worker agents, a `run_planner_worker.py` script you can run directly.

## Example: DevOps Automation Agent

A planner-worker harness that investigates an issue and prepares a fix, with a supervised cycle that asks for approval before continuing:

```python
import asyncio
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness

async def main():
    harness = PlannerWorkerHarness(
        agent_id="devops",
        planner_provider=AnthropicProvider(model="claude-sonnet-5-5"),
        worker_provider=AnthropicProvider(model="claude-haiku-4-5"),
        workspace_dir=Path(".teotl/devops"),
        worker_skills=["filesystem", "git", "github"],
        planner_instructions=(
            "You are a DevOps automation agent. Plan how to reproduce the bug, "
            "find the root cause, implement a fix, test it, and open a pull request."
        ),
        require_approval_for_continuation=True,
    )

    result = await harness.run_supervised_cycle(
        goals="Investigate issue #42 in this repository and create a fix",
        max_cycles=3,
    )
    print(f"Complete: {result.complete} after {result.cycles_completed} cycle(s)")

asyncio.run(main())
```

See [examples/devops_agent/](../examples/devops_agent/) for a fuller implementation.

## What's Next?

### Learn Core Concepts
- [Concepts Guide](concepts.md) - Understand missions, skills, guardrails, memory
- [Architecture](ARCHITECTURE.md) - Deep dive into the planner-worker pattern

### Explore Examples
- [DevOps Agent](../examples/devops_agent/) - Autonomous bug fixing
- [Planner-Worker Demo](../examples/planner_worker_demo.py) - Harness walkthrough

### Advanced Topics
- [Custom Skills](CUSTOM_SKILLS_QUICKSTART.md) - Build your own skills
- [Security Guide](SECURITY_GUIDE.md) - Production security
- [API Reference](api_reference.md) - Complete API documentation

## Common Patterns

### Pattern 1: Simple Task Automation

```python
agent = Agent(provider=provider, instructions="...")
result = await agent.run("Analyze codebase and suggest improvements")
```

### Pattern 2: Recurring Workflow

Define a mission in `config.yaml` and run it with the daemon:

```bash
python -m teotl.daemon.run --config config.yaml
```

### Pattern 3: Cost Optimization

```python
harness = PlannerWorkerHarness(
    agent_id="my-agent",
    planner_provider=AnthropicProvider(model="claude-sonnet-5-5"),  # strategic decisions
    worker_provider=AnthropicProvider(model="claude-haiku-4-5"),    # fast execution
)
```

### Pattern 4: Interactive Agent

```python
agent = Agent(provider=provider)

while True:
    user_input = input("You: ")
    response = await agent.run(user_input)
    print(f"Agent: {response.text}")
```

## Troubleshooting

### Issue: "API key not found"

**Solution:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Or run: teotl onboard
```

### Issue: "No module named 'teotl'"

**Solution:**
```bash
pip install --upgrade "teotl[anthropic]"
```

### Issue: Agent doesn't use skills

**Solution:** pass skill names as a list, and check the names match a bundled skill or a folder in `~/.teotl/skills/`:

```python
agent = Agent(provider=provider, skills=["filesystem"])
print(agent.list_skills())
```

### Issue: Guardrails blocking too much

**Solution:** use a less restrictive preset, or pass a custom `Policy`:

```python
agent = Agent(provider=provider, policy="minimal")
```

Only use the names `"minimal"`, `"standard"`, or `"strict"`. An unrecognized policy name disables guardrails (with a warning), so don't rely on it.

## Tips and Best Practices

### 1. Use Planner-Worker for Cost Savings

```python
# Good: Haiku worker at about half the per-token price of Sonnet
harness = PlannerWorkerHarness(agent_id="my-agent", planner_provider=sonnet, worker_provider=haiku)

# More expensive: Sonnet for everything
agent = Agent(provider=sonnet)
```

### 2. Keep Guardrails On in Production

```python
# Good: default policy
agent = Agent(provider=provider, policy="standard")

# Better for sensitive environments
agent = Agent(provider=provider, policy="strict")
```

### 3. Use Memory for Context

```python
# Good: Agent remembers across conversations
agent = Agent(provider=provider, memory=LocalMemory())

# Limited: No context retention
agent = Agent(provider=provider)
```

### 4. Scope Skills Appropriately

```python
# Good: Only the skills the task needs
agent = Agent(provider=provider, skills=["filesystem"])

# Riskier: More capabilities than needed
agent = Agent(provider=provider, skills=["filesystem", "git", "github", "web"])
```

## Getting Help

- **Documentation:** [docs/](.)
- **GitHub Issues:** [Report bugs](https://github.com/keithdit4e/teotl/issues)
- **Discussions:** [Ask questions](https://github.com/keithdit4e/teotl/discussions)

---

**Next:** [Concepts Guide](concepts.md) - Understand core concepts

# Core Concepts

Understanding the key concepts behind Teotl's architecture.

## Table of Contents

- [Agent](#agent)
- [Planner-Worker Architecture](#planner-worker-architecture)
- [Providers](#providers)
- [Skills](#skills)
- [Missions](#missions)
- [Memory](#memory)
- [Guardrails](#guardrails)
- [Credentials](#credentials)

---

## Agent

An **Agent** is the core abstraction in Teotl. It wraps an LLM provider in an agent loop that can:

- Understand natural language instructions
- Call tools (a built-in `bash` tool plus any you register) guided by skills
- Keep conversation history within a session
- Remember facts across sessions (with memory)
- Follow security policies (with guardrails)

### Basic Agent

```python
import asyncio

from teotl import Agent
from teotl.core.provider import AnthropicProvider


async def main():
    agent = Agent(
        provider=AnthropicProvider(),  # reads ANTHROPIC_API_KEY
        instructions="You are a helpful assistant.",
    )
    response = await agent.run("Hello!")
    print(response.text)


asyncio.run(main())
```

`agent.run()` returns a `Response` with `text`, `messages`, `tool_calls_made`, `tokens_used`, and `cost`.

### Agent Components

```
┌─────────────────────────────────────────┐
│              Agent                      │
├─────────────────────────────────────────┤
│ • Provider (LLM)                        │
│ • Instructions (system prompt)          │
│ • Skills (SKILL.md instructions)        │
│ • Tools (bash + registered tools)       │
│ • Memory (optional, cross-session)      │
│ • Guardrails (security policy)          │
│ • Session (conversation history)        │
└─────────────────────────────────────────┘
```

### Agent Lifecycle

1. **Initialization:** Create the agent with a provider and configuration
2. **Input:** The user provides a task or question via `agent.run()`
3. **Context:** Relevant memories (if memory is enabled) and skill descriptions are added to the prompt
4. **Execution:** The agent loop calls the LLM and executes tool calls (checked by guardrails) until it has an answer or reaches `max_turns`
5. **Output:** The agent returns a `Response`
6. **Memory:** (Optional) Explicit "remember that..." statements are stored for future sessions

---

## Planner-Worker Architecture

The **Planner-Worker** pattern is Teotl's main cost optimization strategy: a capable model plans, and a cheaper model executes the individual steps. With the default models (Sonnet 5.5 planner, Haiku 4.5 worker), worker steps run at about half the per-token price of an all-Sonnet setup.

### How It Works

```
┌──────────────────────────────────────────────┐
│          Goals                               │
│  "Fix bug in authentication system"          │
└───────────────┬──────────────────────────────┘
                │
        ┌───────▼────────┐
        │    PLANNER     │  claude-sonnet-5-5
        │  (Strategic)   │
        └───────┬────────┘  • Analyze goals
                │           • Break into steps
                │           • Write PLAN.md
        ┌───────▼────────┐
        │     WORKER     │  claude-haiku-4-5
        │  (Execution)   │
        └───────┬────────┘  • Execute one step at a time
                │           • Use tools/skills
                │           • Report results
        ┌───────▼────────┐
        │     Result     │
        │  + Progress    │
        └────────────────┘
```

### Using the Harness

Planner-worker execution is provided by `PlannerWorkerHarness`:

```python
import asyncio
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness


async def main():
    harness = PlannerWorkerHarness(
        agent_id="code-quality",
        planner_provider=AnthropicProvider(model="claude-sonnet-5-5"),
        worker_provider=AnthropicProvider(model="claude-haiku-4-5"),
        workspace_dir=Path(".teotl/code-quality"),
        worker_skills=["filesystem", "git"],
    )

    await harness.plan(goals="Fix the failing tests in the auth module")  # writes PLAN.md

    while not harness.is_complete():
        result = await harness.execute_next_step()
        print(f"Step {result.step.number}: {'ok' if result.success else result.error}")


asyncio.run(main())
```

Other harness methods include `execute_all_steps()`, `get_progress()`, `refine_plan(feedback)`, `reset()`, and `run_supervised_cycle(goals=...)`. The setup wizard (`teotl onboard`) can generate a `run_planner_worker.py` script for you.

### When to Use

**Use Planner-Worker when:**
- ✅ The task has multiple steps
- ✅ Cost is a concern
- ✅ There is a mix of strategic and execution work
- ✅ Workflows are long-running

**Use a single Agent when:**
- ✅ Simple one-off tasks
- ✅ Maximum quality is needed for every step
- ✅ Latency is critical

---

## Providers

A **Provider** is the interface to an LLM (Large Language Model). Teotl supports multiple providers.

### Supported Providers

#### Anthropic Claude (Recommended)

```python
from teotl.core.provider import AnthropicProvider

provider = AnthropicProvider(
    model="claude-sonnet-5-5",
    api_key="sk-ant-...",  # Or set ANTHROPIC_API_KEY
)
```

**Models:**
- `claude-sonnet-5-5` - Balanced (default; $2 / $10 per million input/output tokens)
- `claude-haiku-4-5` - Fastest, cheapest ($1 / $5)
- `claude-opus-5-5` - Most capable ($4 / $20)
- `claude-fable-5-1` - Premium tier ($10 / $50)

#### OpenAI

```python
from teotl.core.provider import OpenAIProvider

provider = OpenAIProvider(
    model="gpt-5.4",  # default
    api_key="sk-...",  # Or set OPENAI_API_KEY
)
```

`OpenAIProvider` also accepts `base_url` for OpenAI-compatible endpoints.

#### Google Gemini

```python
from teotl.core.provider import GeminiProvider

provider = GeminiProvider(model="gemini-2.5-flash")
```

#### Ollama (Local)

```python
from teotl.core.provider import OllamaProvider

provider = OllamaProvider(
    model="llama3",
    host="http://localhost:11434",  # Local Ollama server
)
```

Any model you have pulled into Ollama can be used.

### Provider Selection

Choose based on:
- **Cost:** Among Claude models, Haiku < Sonnet < Opus < Fable
- **Quality:** Larger models handle complex planning better; smaller models are well suited to executing well-defined steps
- **Privacy:** Ollama runs locally; the other providers are cloud services

---

## Skills

**Skills** are packaged instructions that teach an agent how to do something. Each skill is a folder containing a `SKILL.md` file (YAML frontmatter with a name and description, followed by instructions). The agent executes skill commands through its built-in `bash` tool.

Skills use progressive disclosure: only each skill's short description is always in context, and the full `SKILL.md` is loaded when the skill is activated.

### Built-in Skills

Teotl bundles these skills: `claude_code`, `filesystem`, `git`, `github`, `social-media`, `spec_kit`, and `web`.

Enable skills by passing their names to the agent:

```python
from teotl import Agent
from teotl.core.provider import AnthropicProvider

agent = Agent(
    provider=AnthropicProvider(),
    skills=["filesystem", "git"],
)

print(agent.list_skills())
```

- **filesystem** - Read, write, search, and navigate files and directories
- **git** - Version control: status, commits, branches, diffs

If `skills` is omitted, all discovered skills are registered. Skills are discovered from the bundled skills, `~/.forge/skills/`, and any directories listed in `TEOTL_SKILLS_PATH` (colon-separated).

### Custom Skills

To create a skill, write a folder with a `SKILL.md` and place it in `~/.forge/skills/` (or a directory on `TEOTL_SKILLS_PATH`). See [CUSTOM_SKILLS_QUICKSTART.md](CUSTOM_SKILLS_QUICKSTART.md) for details.

### Custom Tools

To give the agent a new Python function it can call, register a tool with an async handler:

```python
from teotl import Agent
from teotl.core.provider import AnthropicProvider


async def get_weather(location: str) -> str:
    # Your implementation
    return f"Weather in {location}: Sunny, 72°F"


agent = Agent(provider=AnthropicProvider())
agent.register_tool(
    name="get_weather",
    description="Get current weather for a location.",
    handler=get_weather,
    parameters={
        "type": "object",
        "properties": {"location": {"type": "string", "description": "City name"}},
        "required": ["location"],
    },
)
```

The handler is called with the tool call's arguments as keyword arguments.

---

## Missions

A **Mission** is recurring, scheduled work that the Teotl daemon executes autonomously. Missions are stored in a SQLite-backed `MissionStore`, so they survive daemon restarts.

### Defining Missions

Missions are defined in the daemon config YAML:

```yaml
missions:
  - description: "Weekly code quality review"
    interval: WEEKLY           # HOURLY, DAILY, WEEKLY
    can_be_interrupted: true
    interrupt_threshold: URGENT
```

See [examples/full_config_reference.yaml](../examples/full_config_reference.yaml) for the full config schema.

### Running Missions

Start the daemon with your config:

```bash
python -m teotl.daemon.run --config config.yaml
```

The daemon checks for due missions and executes each one through the agent loop. Immediate tasks take priority, and a mission marked `can_be_interrupted` can be paused for tasks at or above its `interrupt_threshold` priority.

### Mission Features

The `Mission` model (`teotl.primitives.missions`) supports:

- **Scheduling:** Intervals from every few minutes to weekly, or manual
- **Persistence:** Missions and their execution history are stored in SQLite
- **Budgets:** Optional per-execution limits on API calls, cost, and duration (`MissionBudget`)
- **Lifecycle:** Pause, resume, and cancel
- **Execution tracking:** Execution, success, and failure counts
- **Interruption:** High-priority tasks can interrupt a running mission

### Use Cases

- **Code Review:** Periodic code quality reviews
- **DevOps Automation:** Scheduled checks and investigations
- **Research:** Recurring monitoring or summarization tasks

---

## Memory

**Memory** gives agents the ability to remember context within and across conversations.

### Types of Memory

#### Short-Term Memory (Built-in)

Conversation history within a single session:

```python
agent = Agent(provider=provider)

await agent.run("My name is Alice")
await agent.run("What's my name?")
# The earlier message is still in the session history
```

#### Long-Term Memory (Opt-in)

Persistent storage across sessions. Requires `pip install "teotl[memory]"`:

```python
from teotl.primitives.memory.local import LocalMemory

memory = LocalMemory()
agent = Agent(provider=provider, memory=memory)

# First session
await agent.run("Remember that I prefer Python over JavaScript")

# Later session
await agent.run("What programming language do I prefer?")
```

When memory is enabled, the agent recalls relevant memories before each turn and stores explicit "remember that..." statements. You can also manage memories directly with `agent.remember()`, `agent.recall()`, `agent.forget()`, and `agent.list_memories()`.

### Memory Backends

#### Local Memory

SQLite-based local storage (default path: `~/.forge/memory.db`):

```python
from teotl.primitives.memory.local import LocalMemory

memory = LocalMemory(
    path="memory.db",
    max_memories=10000,
)
```

#### Encrypted Memory

Local storage with encrypted memory content:

```python
from teotl.primitives.memory.encrypted import EncryptedMemory

memory = EncryptedMemory(
    path="memory.db",
    encryption_key=None,  # None = key is retrieved from / created in the credential store
)
```

### Memory Operations

```python
# Store memory (returns the memory ID)
memory_id = await memory.remember("User prefers dark mode")

# Recall memories
results = await memory.recall("user preferences", limit=5)
for m in results:
    print(m.content)

# List memories
memories = await memory.list_all(limit=10)

# Forget a specific memory
await memory.forget(memory_id)

# Count memories
count = await memory.count()

# Close the database when done
memory.close()
```

See [MEMORY.md](MEMORY.md) for more.

---

## Guardrails

**Guardrails** are security policies that check every tool call before it runs. Each call is **allowed**, **blocked**, or requires **confirmation**.

### Policy Levels

Set the policy with the `policy` argument (default: `"standard"`). The built-in presets are `"minimal"`, `"standard"`, and `"strict"`. You can also pass a `Policy` object or a path to a policy file.

#### Minimal (Low Security)

Few restrictions:

```python
agent = Agent(provider=provider, policy="minimal")

# Blocks only catastrophic commands (e.g. rm -rf /, fork bombs)
# Denies access to ~/.ssh and ~/.aws
# Use when: the agent is trusted, local development
```

#### Standard (Balanced)

Recommended for most use cases:

```python
agent = Agent(provider=provider, policy="standard")

# Blocks dangerous commands (e.g. rm -rf /, curl ... | bash)
# Requires confirmation for risky commands (rm, git push, sudo, pip install, ...)
# Limits outbound network access to a small allowlist
# Use when: general use
```

#### Strict (High Security)

Maximum security:

```python
agent = Agent(provider=provider, policy="strict")

# Also blocks sudo and docker
# Requires confirmation for every command not on a short read-only allowlist
# Use when: critical systems, untrusted agents
```

### How Guardrails Work

```
┌─────────────────────────────────────────┐
│   Agent wants to execute command        │
│   $ rm -rf /                            │
└──────────────┬──────────────────────────┘
               │
       ┌───────▼────────┐
       │  Guardrails    │
       │    Engine      │
       └───────┬────────┘
               │
        ┌──────▼───────┐
        │   Classify   │
        │  vs. policy  │
        │  + trust     │
        └──────┬───────┘
               │
     ┌─────────▼──────────┐
     │   Decision         │
     │                    │
     │  ✅ Allow          │
     │  ⚠️  Confirm       │
     │  ❌ Block          │
     └────────────────────┘
```

Confirmations are sent to the UI passed to `agent.run(message, ui=...)`. When no UI is passed, `agent.run()` uses a headless UI that auto-approves confirmations, so supply a UI if you want to approve actions interactively. Every decision is written to an audit log.

### Progressive Trust

To reduce confirmation fatigue, guardrails track approvals per action pattern (for example, a specific command, or writes to a directory). After a pattern has been approved enough times, similar actions are auto-approved: after 1 approval with `minimal`, 3 with `standard`, and 5 with `strict`. Trust is session-scoped by default.

### Blocked Operations

The standard policy blocks:
- `rm -rf /` - Delete system
- `:(){ :|:& };:` - Fork bomb
- `curl * | bash`, `wget * | sh` (and similar) - Arbitrary code execution
- Access to sensitive paths such as `~/.ssh`, `~/.aws`, and `~/.gnupg`

See [GUARDRAILS.md](GUARDRAILS.md) for details.

---

## Credentials

**Credentials** are securely stored API keys, tokens, and secrets.

### Credential Storage

```python
from teotl.primitives.integrations.credential_store import CredentialStore

# Auto-detect the best available backend
store = CredentialStore.create()
print(store.backend_name)

# Save a credential (data is a dict)
store.save_credential("github", {"token": "ghp_..."})

# Load a credential
token = store.load_credential("github")["token"]

# List services (not supported by the keyring backend, which returns [])
services = store.list_services()

# Delete a credential
store.delete_credential("github")
```

`CredentialStore.create()` auto-detects a backend in this order: environment variables (only if `FORGE_ALLOW_ENV_AUTH=true`), AWS Secrets Manager (if `AWS_REGION` or `AWS_DEFAULT_REGION` is set), OS keyring, then an encrypted file. To choose one explicitly, pass `backend="keyring"`, `"file"`, `"environment"`, or `"aws_secrets"`.

### Storage Backends

#### OS Keyring

Uses the system credential manager (credentials are also encrypted before storage):
- **macOS:** Keychain
- **Windows:** Credential Manager
- **Linux:** Secret Service (GNOME Keyring, KWallet)

```python
from teotl.primitives.integrations.credential_store import CredentialStore, LocalKeyringBackend

store = CredentialStore(LocalKeyringBackend())
```

#### Encrypted File

Encrypted file storage (fallback). `storage_path` is a directory (default: `~/.forge/auth`) holding one encrypted file per service plus the encryption key:

```python
from pathlib import Path

from teotl.primitives.integrations.credential_store import CredentialStore, FileBackend

store = CredentialStore(FileBackend(storage_path=Path.home() / ".forge" / "auth"))
```

#### AWS Secrets Manager

Cloud-based credential storage:

```python
from teotl.primitives.integrations.credential_store import AWSSecretsBackend, CredentialStore

store = CredentialStore(AWSSecretsBackend(region="us-west-2"))
```

### Security Best Practices

✅ **DO:**
- Use the OS keyring when possible
- Rotate credentials regularly
- Use separate credentials per environment

❌ **DON'T:**
- Store credentials in code
- Share credentials across systems
- Commit credentials to git

---

## Putting It All Together

A complete example combining a provider, skills, memory, and guardrails:

```python
import asyncio

from teotl import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.memory.local import LocalMemory


async def main():
    memory = LocalMemory()

    agent = Agent(
        provider=AnthropicProvider(model="claude-sonnet-5-5"),  # reads ANTHROPIC_API_KEY
        instructions="You are a DevOps automation agent.",
        skills=["filesystem", "git"],
        memory=memory,
        policy="standard",
    )

    response = await agent.run("Investigate the failing tests and summarize the cause")
    print(response.text)
    print(f"Tokens: {response.tokens_used}, cost: {response.cost}")

    memory.close()


asyncio.run(main())
```

For multi-step work with a cheaper worker model, use [`PlannerWorkerHarness`](#planner-worker-architecture); for scheduled work, use [missions](#missions) with the daemon.

---

## Next Steps

- [API Reference](api_reference.md) - API documentation
- [Architecture](ARCHITECTURE.md) - How the pieces fit together
- [Examples](../examples/) - Real-world examples
- [Security Guide](SECURITY_GUIDE.md) - Production security
- [Custom Skills](CUSTOM_SKILLS_QUICKSTART.md) - Build your own skills

---

## Key Takeaways

1. **Agents** run an LLM tool loop with instructions, skills, and tools
2. **Planner-Worker** (`PlannerWorkerHarness`) lowers cost by running steps on a cheaper model
3. **Skills** are `SKILL.md` folders; custom Python tools use `agent.register_tool()`
4. **Missions** are recurring work scheduled by the daemon
5. **Memory** provides cross-session context persistence (opt-in)
6. **Guardrails** check every tool call against a policy
7. **Credentials** are stored in the OS keyring, an encrypted file, or a cloud secrets manager

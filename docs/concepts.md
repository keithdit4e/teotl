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

An **Agent** is the core abstraction in Teotl. It represents an autonomous AI entity that can:

- Understand natural language instructions
- Use tools and skills to complete tasks
- Make decisions based on context
- Learn from past interactions (with memory)
- Follow security policies (with guardrails)

### Basic Agent

```python
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider

agent = Agent(
    provider=AnthropicProvider(),
    instructions="You are a helpful assistant.",
)

response = await agent.run("Hello!")
```

### Agent Components

```
┌─────────────────────────────────────────┐
│              Agent                      │
├─────────────────────────────────────────┤
│ • Provider (LLM)                        │
│ • Instructions (system prompt)          │
│ • Skills (tools/capabilities)           │
│ • Memory (context persistence)          │
│ • Guardrails (security policies)        │
│ • History (conversation state)          │
└─────────────────────────────────────────┘
```

### Agent Lifecycle

1. **Initialization:** Create agent with configuration
2. **Input:** User provides task or question
3. **Processing:** Agent reasons and decides on actions
4. **Execution:** Agent uses skills to complete task
5. **Output:** Agent returns response
6. **Memory:** (Optional) Agent stores context for future

---

## Planner-Worker Architecture

The **Planner-Worker** pattern is Teotl's key cost optimization strategy, achieving **40% cost savings** compared to single-model approaches.

### How It Works

```
┌──────────────────────────────────────────────┐
│          User Request                        │
│  "Fix bug in authentication system"          │
└───────────────┬──────────────────────────────┘
                │
        ┌───────▼────────┐
        │    PLANNER     │  Claude Sonnet 4 (Expensive)
        │  (Strategic)   │  
        └───────┬────────┘  • Analyze problem
                │           • Break into steps
                │           • Choose approach
                │           • Delegate to worker
        ┌───────▼────────┐
        │     WORKER     │  Claude Haiku 4 (Cheap)
        │  (Execution)   │
        └───────┬────────┘  • Execute steps
                │           • Use tools/skills
                │           • Report results
                │
        ┌───────▼────────┐
        │     Result     │  40% cheaper!
        │   + Context    │  Same quality!
        └────────────────┘
```

### Why It Works

**Traditional Approach (Expensive):**
```python
# Single model does everything
agent = Agent(provider=claude_sonnet_4)

# Costs:
# - Analysis: $0.10 (Sonnet)
# - Planning: $0.05 (Sonnet)
# - Execution: $0.08 (Sonnet)
# - Validation: $0.06 (Sonnet)
# Total: $0.29
```

**Planner-Worker Approach (Efficient):**
```python
# Strategic model for planning, fast model for execution
agent = Agent.create_planner_worker(
    planner=claude_sonnet_4,
    worker=claude_haiku_4
)

# Costs:
# - Analysis: $0.10 (Sonnet) ← Strategic
# - Planning: $0.05 (Sonnet) ← Strategic
# - Execution: $0.01 (Haiku) ← Fast, cheap
# - Validation: $0.01 (Haiku) ← Fast, cheap
# Total: $0.17 (40% savings!)
```

### When to Use

**Use Planner-Worker when:**
- ✅ Task has multiple steps
- ✅ Cost is a concern
- ✅ Mix of strategic + execution work
- ✅ Long-running workflows

**Use Single Agent when:**
- ✅ Simple one-off tasks
- ✅ Maximum quality needed for everything
- ✅ Real-time latency critical

---

## Providers

A **Provider** is the interface to an LLM (Large Language Model). Teotl supports multiple providers.

### Supported Providers

#### Anthropic Claude (Recommended)

```python
from teotl.core.provider import AnthropicProvider

provider = AnthropicProvider(
    model="claude-sonnet-4-20250514",
    api_key="sk-ant-...",  # Or set ANTHROPIC_API_KEY
)
```

**Models:**
- `claude-sonnet-4-20250514` - Balanced (recommended)
- `claude-opus-4-20250514` - Most capable (expensive)
- `claude-haiku-4-20250514` - Fastest, cheapest

#### OpenAI

```python
from teotl.core.provider import OpenAIProvider

provider = OpenAIProvider(
    model="gpt-4o",
    api_key="sk-...",  # Or set OPENAI_API_KEY
)
```

**Models:**
- `gpt-4o` - Latest, most capable
- `gpt-4-turbo` - Fast, capable
- `gpt-3.5-turbo` - Cheapest

#### Ollama (Local)

```python
from teotl.core.provider import OllamaProvider

provider = OllamaProvider(
    model="llama3",
    base_url="http://localhost:11434"  # Local Ollama
)
```

**Models:**
- `llama3` - Open source, capable
- `mistral` - Fast, efficient
- `codellama` - Code-focused

### Provider Selection

Choose based on:
- **Cost:** Haiku < GPT-3.5 < Sonnet < GPT-4 < Opus
- **Speed:** Haiku < Sonnet < GPT-4
- **Quality:** Haiku < GPT-3.5 < Sonnet < GPT-4 < Opus
- **Privacy:** Ollama (local) > Cloud providers

---

## Skills

**Skills** are capabilities that agents can use to interact with the world. Think of them as "tools" or "functions" the agent can call.

### Built-in Skills

#### Filesystem Skill

Read and write files:

```python
registry = SkillRegistry()
registry.register_builtin("filesystem")

agent = Agent(provider=provider, skills=registry)

# Agent can now:
# - Read files
# - Write files
# - List directories
# - Check file existence
```

#### Git Skill

Repository operations:

```python
registry.register_builtin("git")

# Agent can now:
# - Clone repositories
# - Commit changes
# - Create branches
# - Push/pull
# - View diffs
```

#### Bash Skill

Execute shell commands:

```python
registry.register_builtin("bash")

# Agent can now:
# - Run commands
# - Install dependencies
# - Start servers
# - Run tests
```

#### Python REPL Skill

Execute Python code dynamically:

```python
registry.register_builtin("python_repl")

# Agent can now:
# - Run Python code
# - Import libraries
# - Analyze data
# - Generate outputs
```

### Custom Skills

Create your own skills:

```python
from teotl.primitives.skills import Skill

class WeatherSkill(Skill):
    """Get weather information."""
    
    name = "weather"
    
    async def get_weather(self, location: str) -> str:
        """Get current weather for a location.
        
        Args:
            location: City name or coordinates
            
        Returns:
            Weather description
        """
        # Your implementation
        return f"Weather in {location}: Sunny, 72°F"

# Register and use
registry = SkillRegistry()
registry.register(WeatherSkill())

agent = Agent(provider=provider, skills=registry)
```

See [CUSTOM_SKILLS_QUICKSTART.md](CUSTOM_SKILLS_QUICKSTART.md) for details.

---

## Missions

A **Mission** is a high-level autonomous workflow that can run for minutes, hours, or days without human intervention.

### Mission Structure

```yaml
# missions/devops_agent.yaml
name: devops_automation
objective: "Investigate GitHub issues and create fixes"

execution_pattern: planner_worker

planner_worker:
  planner:
    provider: claude-sonnet-4
    
  worker:
    provider: claude-haiku-4
    skills:
      - filesystem
      - git
      - bash

guardrails:
  policy: standard
  
memory:
  enabled: true
```

### Running Missions

```python
from teotl.primitives.missions import Mission

mission = Mission.from_file("missions/devops_agent.yaml")

result = await mission.run(context={
    "repository": "owner/repo",
    "issue_number": 42
})

print(f"Status: {result.status}")
print(f"Summary: {result.summary}")
```

### Mission Features

- **Autonomous Execution:** Runs without human intervention
- **Error Recovery:** Automatically handles and retries failures
- **Context Management:** Maintains state across long workflows
- **Cost Tracking:** Monitors and optimizes costs
- **Progress Reporting:** Real-time status updates

### Use Cases

- **DevOps Automation:** Monitor, investigate, fix issues
- **Code Review:** Analyze PRs, suggest improvements
- **Testing:** Generate tests, find edge cases
- **Research:** Multi-hour investigation tasks
- **Data Pipelines:** ETL, validation, transformation

---

## Memory

**Memory** gives agents the ability to remember past interactions and context across conversations.

### Types of Memory

#### Short-Term Memory (Built-in)

Conversation history within a single session:

```python
agent = Agent(provider=provider)

await agent.run("My name is Alice")
await agent.run("What's my name?")
# Agent remembers: "Alice"
```

#### Long-Term Memory (Explicit)

Persistent storage across sessions:

```python
from teotl.primitives.memory.local import LocalMemory

memory = LocalMemory()
agent = Agent(provider=provider, memory=memory)

# First session
await agent.run("I prefer Python over JavaScript")

# Later session (different day)
await agent.run("What programming language do I prefer?")
# Agent remembers: "Python"
```

### Memory Backends

#### Local Memory

SQLite-based local storage:

```python
memory = LocalMemory(
    path="~/.teotl/memory.db",
    max_memories=10000,
)
```

#### Encrypted Memory

Encrypted local storage:

```python
from teotl.primitives.memory.encrypted import EncryptedMemory

memory = EncryptedMemory(
    path="~/.teotl/memory.db",
    encryption_key=None,  # Auto-generated
)
```

### Memory Operations

```python
# Store memory
await memory.remember("User prefers dark mode")

# Recall memories
results = await memory.recall("user preferences", limit=5)

# List all memories
memories = await memory.list_all(limit=10)

# Forget specific memory
await memory.forget(memory_id)

# Count memories
count = await memory.count()
```

---

## Guardrails

**Guardrails** are security policies that protect your system from dangerous operations.

### Policy Levels

#### Permissive (Low Security)

Minimal restrictions, trust agent:

```python
agent = Agent(provider=provider, policy="permissive")

# Allows most operations
# Use when: Agent is fully trusted, testing, development
```

#### Standard (Balanced)

Recommended for most use cases:

```python
agent = Agent(provider=provider, policy="standard")

# Blocks dangerous operations
# Requests confirmation for risky actions
# Use when: Production, general use
```

#### Strict (High Security)

Maximum security, confirmation required:

```python
agent = Agent(provider=provider, policy="strict")

# Blocks many operations
# Requires explicit confirmation
# Use when: Critical systems, untrusted agents
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
        │   Analyze    │
        │  • Risk      │
        │  • Impact    │
        │  • Trust     │
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

### Trust Building

Guardrails learn to trust the agent over time:

```python
# First time: Requires confirmation
await agent.run("Write to config.json")
# Confirmation: Allow agent to write to config.json? [y/N]

# After 3 approvals: Auto-approved
await agent.run("Write to config.json")
# Automatically allowed (trust established)
```

### Blocked Operations

Standard policy blocks:
- `rm -rf /` - Delete system
- `dd if=/dev/zero of=/dev/sda` - Wipe disk
- `chmod -R 777 /` - Open permissions
- `curl | bash` - Arbitrary code execution
- Access to sensitive files (passwords, keys)

See [GUARDRAILS.md](GUARDRAILS.md) for complete list.

---

## Credentials

**Credentials** are securely stored API keys, passwords, and secrets.

### Credential Storage

Teotl stores credentials securely using OS-level keyrings:

```python
from teotl.primitives.integrations.credential_store import CredentialStore

# Auto-detect best backend (OS keyring, file, AWS)
store = CredentialStore.create()

# Save credential
await store.save_credential(
    key="github_token",
    value="ghp_...",
    description="GitHub API token"
)

# Load credential
token = await store.load_credential("github_token")

# List credentials
creds = await store.list_credentials()

# Delete credential
await store.delete_credential("github_token")
```

### Storage Backends

#### OS Keyring (Default)

Uses system credential manager:
- **macOS:** Keychain
- **Windows:** Credential Manager
- **Linux:** Secret Service (GNOME Keyring, KWallet)

```python
from teotl.primitives.integrations.credential_store import LocalKeyringBackend

backend = LocalKeyringBackend()
store = CredentialStore(backend)
```

#### Encrypted File

Encrypted file storage (fallback):

```python
from teotl.primitives.integrations.credential_store import FileBackend

backend = FileBackend(storage_path="~/.teotl/credentials.enc")
store = CredentialStore(backend)
```

#### AWS Secrets Manager

Cloud-based credential storage:

```python
from teotl.primitives.integrations.credential_store import AWSSecretsBackend

backend = AWSSecretsBackend(region="us-west-2")
store = CredentialStore(backend)
```

### Security Best Practices

✅ **DO:**
- Use OS keyring when possible
- Rotate credentials regularly
- Use separate credentials per environment
- Encrypt credential files

❌ **DON'T:**
- Store credentials in code
- Use environment variables (visible in logs)
- Share credentials across systems
- Commit credentials to git

---

## Putting It All Together

A complete example using all concepts:

```python
import asyncio
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.skills.registry import SkillRegistry
from teotl.primitives.memory.local import LocalMemory
from teotl.primitives.integrations.credential_store import CredentialStore

async def main():
    # Setup credentials
    store = CredentialStore.create()
    api_key = await store.load_credential("anthropic_api_key")
    
    # Setup providers (planner-worker)
    planner = AnthropicProvider(model="claude-sonnet-4-20250514", api_key=api_key)
    worker = AnthropicProvider(model="claude-haiku-4-20250514", api_key=api_key)
    
    # Setup skills
    registry = SkillRegistry()
    registry.register_builtin("filesystem")
    registry.register_builtin("git")
    registry.register_builtin("bash")
    
    # Setup memory
    memory = LocalMemory()
    
    # Create agent with all features
    agent = Agent.create_planner_worker(
        planner=planner,
        worker=worker,
        instructions="You are a DevOps automation agent.",
        skills=registry,
        memory=memory,
        policy="standard",
    )
    
    # Run autonomous task
    response = await agent.run(
        "Investigate failing tests and create fixes"
    )
    
    print(response.text)
    
    # Cleanup
    memory.close()

asyncio.run(main())
```

---

## Next Steps

- [API Reference](api_reference.md) - Complete API documentation
- [Examples](../examples/) - Real-world examples
- [Security Guide](SECURITY_GUIDE.md) - Production security
- [Custom Skills](CUSTOM_SKILLS_QUICKSTART.md) - Build your own skills

---

## Key Takeaways

1. **Agents** are autonomous AI entities with capabilities
2. **Planner-Worker** saves 40% cost vs single-model
3. **Skills** give agents real-world capabilities
4. **Missions** enable long-running autonomous workflows
5. **Memory** provides context persistence
6. **Guardrails** protect against dangerous operations
7. **Credentials** store secrets securely

**Teotl makes it easy to build production-ready autonomous agents.** 🚀

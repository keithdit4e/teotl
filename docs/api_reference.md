# API Reference

Complete API documentation for Teotl framework.

## Table of Contents

- [Core](#core)
  - [Agent](#agent)
  - [Provider](#provider)
  - [Types](#types)
- [Primitives](#primitives)
  - [Skills](#skills)
  - [Memory](#memory)
  - [Missions](#missions)
  - [Guardrails](#guardrails)
  - [Credentials](#credentials)
- [CLI](#cli)

---

## Core

### Agent

The main agent class that coordinates LLM, skills, memory, and guardrails.

#### Class: `Agent`

```python
from teotl.core.agent import Agent
```

**Constructor:**

```python
Agent(
    provider: Provider,
    instructions: str | Callable = "",
    skills: list[str] | None = None,
    policy: str | Any = "standard",
    memory: Any | None = None,
    extensions: list[Extension] | None = None,
    tools: list[ToolDefinition] | None = None,
    session_dir: Path | None = None,
    max_turns: int = 50,
    enable_injection_defense: bool = True,
    cost_tracker: Any | None = None,
    audit_logger: Any | None = None,
    checkpoint_manager: Any | None = None,
    heartbeat_monitor: Any | None = None,
    state_manager: Any | None = None,
    enable_auto_compact: bool | None = None,
    compact_every: int = 15,
    max_context_tokens: int | None = None,
)
```

**Parameters:**

- `provider` (Provider): LLM provider (required)
- `instructions` (str | Callable): System instructions for the agent
- `skills` (list[str] | None): List of skill names to enable
- `policy` (str | Any): Guardrail policy level ("permissive", "standard", "strict")
- `memory` (Any | None): Memory system for context persistence
- `extensions` (list[Extension] | None): Additional extensions
- `tools` (list[ToolDefinition] | None): Custom tools
- `session_dir` (Path | None): Directory for session persistence
- `max_turns` (int): Maximum conversation turns (default: 50)
- `enable_injection_defense` (bool): Enable prompt injection protection (default: True)
- `cost_tracker` (Any | None): Cost tracking system
- `audit_logger` (Any | None): Audit logging system
- `checkpoint_manager` (Any | None): Checkpoint management
- `heartbeat_monitor` (Any | None): Heartbeat monitoring
- `state_manager` (Any | None): State management
- `enable_auto_compact` (bool | None): Auto-compact context (default: auto-enabled with memory)
- `compact_every` (int): Compact frequency in turns (default: 15)
- `max_context_tokens` (int | None): Max context size (default: auto-detected)

**Methods:**

##### `async run(task: str, *, ui: UI | None = None) -> Response`

Run the agent with a task.

**Parameters:**
- `task` (str): The task or query for the agent
- `ui` (UI | None): Optional UI for confirmations and display

**Returns:**
- `Response`: Agent response with text and metadata

**Example:**

```python
agent = Agent(provider=AnthropicProvider())
response = await agent.run("Hello, how are you?")
print(response.text)
```

##### `@classmethod create_planner_worker(...) -> Agent`

Create an agent with planner-worker architecture.

**Parameters:**
- `planner` (Provider): Strategic planning model (e.g., Claude Sonnet)
- `worker` (Provider): Fast execution model (e.g., Claude Haiku)
- `instructions` (str): System instructions
- `skills` (list[str] | None): Skills to enable
- `policy` (str): Guardrail policy
- `memory` (Any | None): Memory system

**Returns:**
- `Agent`: Configured planner-worker agent

**Example:**

```python
agent = Agent.create_planner_worker(
    planner=AnthropicProvider(model="claude-sonnet-4-20250514"),
    worker=AnthropicProvider(model="claude-haiku-4-20250514"),
    instructions="You are a helpful assistant.",
)
```

##### `register_command(command: str, handler: Callable) -> None`

Register a custom slash command.

**Parameters:**
- `command` (str): Command name (e.g., "/undo")
- `handler` (Callable): Async function to handle command

**Example:**

```python
async def undo_handler(args: str, ui: UI) -> str:
    return "Undo complete"

agent.register_command("/undo", undo_handler)
```

---

### Provider

LLM provider abstraction for model-agnostic agent code.

#### Class: `Provider` (Abstract)

```python
from teotl.core.provider import Provider
```

**Abstract Methods:**

##### `async complete(...) -> CompletionResult`

Send completion request to LLM.

**Parameters:**
- `system` (str): System prompt
- `messages` (list[dict]): Conversation history
- `tools` (list[ToolDefinition] | None): Available tools
- `max_tokens` (int | None): Maximum response tokens

**Returns:**
- `CompletionResult`: Response with content, tool calls, usage

##### `estimate_tokens(text: str) -> int`

Estimate token count for text.

##### `context_window -> int` (property)

Maximum context window size in tokens.

##### `model_name -> str` (property)

Human-readable model name.

---

#### Class: `AnthropicProvider`

Anthropic Claude provider.

```python
from teotl.core.provider import AnthropicProvider
```

**Constructor:**

```python
AnthropicProvider(
    model: str = "claude-sonnet-4-20250514",
    api_key: str | None = None,
    max_tokens: int = 8192,
)
```

**Parameters:**
- `model` (str): Model name (default: "claude-sonnet-4-20250514")
- `api_key` (str | None): API key (default: from ANTHROPIC_API_KEY env)
- `max_tokens` (int): Max tokens per request (default: 8192)

**Supported Models:**
- `claude-opus-4-20250514` - Most capable
- `claude-sonnet-4-20250514` - Balanced (recommended)
- `claude-haiku-4-20250514` - Fastest, cheapest

**Example:**

```python
provider = AnthropicProvider(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
)
```

---

#### Class: `OpenAIProvider`

OpenAI GPT provider.

```python
from teotl.core.provider import OpenAIProvider
```

**Constructor:**

```python
OpenAIProvider(
    model: str = "gpt-4o",
    api_key: str | None = None,
    max_tokens: int = 4096,
)
```

**Parameters:**
- `model` (str): Model name (default: "gpt-4o")
- `api_key` (str | None): API key (default: from OPENAI_API_KEY env)
- `max_tokens` (int): Max tokens per request (default: 4096)

**Supported Models:**
- `gpt-4o` - Latest, most capable
- `gpt-4-turbo` - Fast, capable
- `gpt-3.5-turbo` - Cheapest

**Example:**

```python
provider = OpenAIProvider(
    model="gpt-4o",
    max_tokens=2048,
)
```

---

#### Class: `OllamaProvider`

Ollama local model provider.

```python
from teotl.core.provider import OllamaProvider
```

**Constructor:**

```python
OllamaProvider(
    model: str = "llama3",
    base_url: str = "http://localhost:11434",
    max_tokens: int = 4096,
)
```

**Parameters:**
- `model` (str): Model name (default: "llama3")
- `base_url` (str): Ollama server URL (default: "http://localhost:11434")
- `max_tokens` (int): Max tokens per request (default: 4096)

**Example:**

```python
provider = OllamaProvider(
    model="llama3",
    base_url="http://localhost:11434",
)
```

---

### Types

Core type definitions.

#### Class: `Response`

```python
from teotl.core.types import Response
```

**Attributes:**
- `text` (str): Response text
- `tool_calls` (list[ToolCall]): Tool calls made
- `usage` (dict): Token usage statistics
- `metadata` (dict): Additional metadata

---

#### Class: `ToolCall`

```python
from teotl.core.types import ToolCall
```

**Attributes:**
- `id` (str): Tool call ID
- `name` (str): Tool/function name
- `args` (dict): Tool arguments

---

#### Class: `ToolDefinition`

```python
from teotl.core.types import ToolDefinition
```

**Attributes:**
- `name` (str): Tool name
- `description` (str): Tool description
- `parameters` (dict): JSON schema for parameters

---

#### Class: `Message`

```python
from teotl.core.types import Message
```

**Attributes:**
- `role` (str): Message role ("user", "assistant", "system")
- `content` (str): Message content

---

## Primitives

### Skills

Modular capabilities that agents can use.

#### Class: `SkillRegistry`

```python
from teotl.primitives.skills.registry import SkillRegistry
```

**Constructor:**

```python
SkillRegistry(search_paths: list[Path] | None = None)
```

**Parameters:**
- `search_paths` (list[Path] | None): Paths to search for custom skills

**Methods:**

##### `register_builtin(name: str) -> None`

Register a built-in skill.

**Parameters:**
- `name` (str): Skill name ("filesystem", "git", "bash", "python_repl")

**Example:**

```python
registry = SkillRegistry()
registry.register_builtin("filesystem")
registry.register_builtin("git")
```

##### `register(skill: Skill) -> None`

Register a custom skill instance.

**Parameters:**
- `skill` (Skill): Skill instance

**Example:**

```python
registry.register(MyCustomSkill())
```

##### `get_descriptions() -> str`

Get formatted descriptions of all registered skills.

**Returns:**
- `str`: Formatted skill descriptions

##### `get_tools() -> list[ToolDefinition]`

Get tool definitions for all registered skills.

**Returns:**
- `list[ToolDefinition]`: Tool definitions

---

#### Class: `Skill` (Abstract)

Base class for custom skills.

```python
from teotl.primitives.skills import Skill
```

**Example:**

```python
class WeatherSkill(Skill):
    name = "weather"
    
    async def get_weather(self, location: str) -> str:
        """Get current weather.
        
        Args:
            location: City name
            
        Returns:
            Weather description
        """
        return f"Sunny, 72°F in {location}"
```

---

### Memory

Context persistence across conversations.

#### Class: `LocalMemory`

Local SQLite-based memory storage.

```python
from teotl.primitives.memory.local import LocalMemory
```

**Constructor:**

```python
LocalMemory(
    path: str | Path = "~/.teotl/memory.db",
    max_memories: int = 10000,
)
```

**Parameters:**
- `path` (str | Path): Database path (default: "~/.teotl/memory.db")
- `max_memories` (int): Max memories to store (default: 10000)

**Methods:**

##### `async remember(content: str, tags: list[str] | None = None, metadata: dict | None = None) -> str`

Store a memory.

**Parameters:**
- `content` (str): Memory content
- `tags` (list[str] | None): Tags for categorization
- `metadata` (dict | None): Additional metadata

**Returns:**
- `str`: Memory ID

**Example:**

```python
memory = LocalMemory()
memory_id = await memory.remember(
    "User prefers Python over JavaScript",
    tags=["preferences"],
)
```

##### `async recall(query: str, limit: int = 10) -> list[Memory]`

Recall relevant memories.

**Parameters:**
- `query` (str): Search query
- `limit` (int): Max results (default: 10)

**Returns:**
- `list[Memory]`: Matching memories

**Example:**

```python
results = await memory.recall("programming language", limit=5)
for mem in results:
    print(mem.content)
```

##### `async list_all(limit: int = 100) -> list[Memory]`

List all memories.

**Parameters:**
- `limit` (int): Max results (default: 100)

**Returns:**
- `list[Memory]`: All memories

##### `async forget(memory_id: str) -> bool`

Delete a memory.

**Parameters:**
- `memory_id` (str): Memory ID

**Returns:**
- `bool`: True if deleted

##### `async count() -> int`

Count total memories.

**Returns:**
- `int`: Memory count

##### `close() -> None`

Close database connection.

---

#### Class: `EncryptedMemory`

Encrypted memory storage.

```python
from teotl.primitives.memory.encrypted import EncryptedMemory
```

**Constructor:**

```python
EncryptedMemory(
    path: str | Path = "~/.teotl/memory.db",
    encryption_key: bytes | None = None,
    max_memories: int = 10000,
)
```

**Parameters:**
- `path` (str | Path): Database path
- `encryption_key` (bytes | None): Encryption key (default: auto-generated)
- `max_memories` (int): Max memories (default: 10000)

**Methods:** Same as `LocalMemory`

---

### Missions

Autonomous long-running workflows.

#### Class: `Mission`

```python
from teotl.primitives.missions import Mission
```

**Class Methods:**

##### `@classmethod from_file(path: str | Path) -> Mission`

Load mission from YAML file.

**Parameters:**
- `path` (str | Path): Path to mission YAML

**Returns:**
- `Mission`: Mission instance

**Example:**

```python
mission = Mission.from_file("missions/devops_agent.yaml")
```

##### `@classmethod from_dict(config: dict) -> Mission`

Load mission from dictionary.

**Parameters:**
- `config` (dict): Mission configuration

**Returns:**
- `Mission`: Mission instance

**Example:**

```python
mission = Mission.from_dict({
    "name": "my_mission",
    "objective": "Do something",
    "execution_pattern": "planner_worker",
})
```

**Instance Methods:**

##### `async run(context: dict | None = None) -> MissionResult`

Run the mission.

**Parameters:**
- `context` (dict | None): Context variables

**Returns:**
- `MissionResult`: Mission result with status and summary

**Example:**

```python
result = await mission.run(context={
    "repository": "owner/repo",
    "issue_number": 42,
})

print(f"Status: {result.status}")
print(f"Summary: {result.summary}")
```

---

### Guardrails

Security policies and enforcement.

#### Class: `Policy`

```python
from teotl.primitives.guardrails.policy import Policy
```

**Class Methods:**

##### `@classmethod from_preset(name: str) -> Policy`

Create policy from preset.

**Parameters:**
- `name` (str): Preset name ("permissive", "standard", "strict")

**Returns:**
- `Policy`: Policy instance

**Example:**

```python
policy = Policy.from_preset("standard")
```

**Attributes:**
- `level` (str): Policy level
- `allowed_commands` (list[str]): Allowed bash commands
- `blocked_commands` (list[str]): Blocked bash commands
- `require_confirmation` (list[str]): Commands requiring confirmation
- `max_file_size` (int): Max file size for operations
- `allowed_paths` (list[Path]): Allowed filesystem paths

---

#### Class: `GuardrailEngine`

```python
from teotl.primitives.guardrails.engine import GuardrailEngine
```

**Constructor:**

```python
GuardrailEngine(
    policy: Policy,
    event_bus: EventBus,
)
```

**Parameters:**
- `policy` (Policy): Security policy
- `event_bus` (EventBus): Event bus for tool call interception

**Methods:**

##### `async evaluate(tool_call: ToolCall, ui: UI | None = None) -> Decision`

Evaluate a tool call.

**Parameters:**
- `tool_call` (ToolCall): Tool call to evaluate
- `ui` (UI | None): UI for confirmations

**Returns:**
- `Decision`: Allow, block, or confirm

---

### Credentials

Secure credential storage.

#### Class: `CredentialStore`

```python
from teotl.primitives.integrations.credential_store import CredentialStore
```

**Class Methods:**

##### `@classmethod create(backend_type: str | None = None, **kwargs) -> CredentialStore`

Create credential store with auto-detected backend.

**Parameters:**
- `backend_type` (str | None): Backend type ("keyring", "file", "aws")
- `**kwargs`: Backend-specific arguments

**Returns:**
- `CredentialStore`: Credential store instance

**Example:**

```python
# Auto-detect backend (OS keyring, fallback to file)
store = CredentialStore.create()

# Force specific backend
store = CredentialStore.create(backend_type="file", storage_path="~/.teotl/creds")
```

**Methods:**

##### `async save_credential(key: str, value: str, description: str = "") -> None`

Save a credential.

**Parameters:**
- `key` (str): Credential key
- `value` (str): Credential value
- `description` (str): Optional description

**Example:**

```python
await store.save_credential(
    key="github_token",
    value="ghp_...",
    description="GitHub API token",
)
```

##### `async load_credential(key: str) -> str`

Load a credential.

**Parameters:**
- `key` (str): Credential key

**Returns:**
- `str`: Credential value

**Raises:**
- `ValueError`: If credential not found

**Example:**

```python
token = await store.load_credential("github_token")
```

##### `async list_credentials() -> list[str]`

List all credential keys.

**Returns:**
- `list[str]`: Credential keys

##### `async delete_credential(key: str) -> bool`

Delete a credential.

**Parameters:**
- `key` (str): Credential key

**Returns:**
- `bool`: True if deleted

---

## CLI

Command-line interface.

### Commands

#### `teotl`

Start interactive REPL.

```bash
teotl
teotl --provider anthropic --model claude-sonnet-4
teotl --policy strict
```

**Options:**
- `--provider` - LLM provider (anthropic, openai, ollama)
- `--model` - Model name
- `--policy` - Guardrail policy (permissive, standard, strict)
- `--verbose` - Enable debug logging

---

#### `teotl chat`

Start interactive chat mode.

```bash
teotl chat
teotl chat --skills filesystem,git
teotl chat --agent my-agent
teotl chat --no-memory
```

**Options:**
- `--agent`, `-a` - Agent ID to load
- `--skills`, `-s` - Skills to enable (comma-separated)
- `--no-memory` - Disable memory system

---

#### `teotl onboard`

Run interactive onboarding wizard.

```bash
teotl onboard
```

Guides through:
- API key configuration
- Agent setup
- Skills selection
- Security policies

---

#### `teotl init`

Initialize Teotl in current directory.

```bash
teotl init
```

Creates:
- `~/.teotl/` - Configuration directory
- `~/.teotl/skills/` - Custom skills
- `~/.teotl/auth/` - Credentials

---

#### `teotl memory`

Manage memories.

```bash
# List memories
teotl memory list --limit 20

# Search memories
teotl memory search "user preferences"

# Delete memory
teotl memory forget <memory-id>
```

---

#### `teotl security`

Manage security policies.

```bash
teotl security
```

Interactive security configuration.

---

### Interactive Commands

Inside interactive mode (`teotl`):

- `/help` - Show help
- `/quit` - Exit Teotl
- `/memory` - Show memory status
- `/skills` - List available skills
- `/policy` - Show current policy
- `/audit` - Show audit log
- `/undo` - Undo last change

---

## Error Handling

### Common Exceptions

#### `ImportError`

Raised when required dependencies are missing.

```python
try:
    provider = AnthropicProvider()
except ImportError as e:
    print("Install anthropic: pip install anthropic")
```

#### `ValueError`

Raised for invalid parameters or configuration.

```python
try:
    credential = await store.load_credential("missing_key")
except ValueError:
    print("Credential not found")
```

#### `RuntimeError`

Raised for runtime errors (e.g., no available credential backend).

```python
try:
    store = CredentialStore.create()
except RuntimeError:
    print("No credential backend available")
```

---

## Best Practices

### 1. Resource Cleanup

Always clean up resources:

```python
memory = LocalMemory()
try:
    await memory.remember("Something")
finally:
    memory.close()
```

### 2. Error Handling

Handle exceptions appropriately:

```python
try:
    response = await agent.run("Task")
except Exception as e:
    logger.error(f"Agent failed: {e}")
```

### 3. Type Hints

Use type hints for better IDE support:

```python
from teotl.core.agent import Agent
from teotl.core.provider import Provider

def create_agent(provider: Provider) -> Agent:
    return Agent(provider=provider)
```

### 4. Async/Await

All agent operations are async:

```python
import asyncio

async def main():
    agent = Agent(provider=provider)
    response = await agent.run("Hello")
    print(response.text)

asyncio.run(main())
```

---

## Version Compatibility

Current version: `0.1.0`

Minimum Python version: `3.11`

---

## See Also

- [Quick Start Guide](quickstart.md) - Get started quickly
- [Concepts](concepts.md) - Understand core concepts
- [Installation](installation.md) - Setup instructions
- [Examples](../examples/) - Real-world examples

---

**Questions?** Open an issue: https://github.com/yourusername/teotl/issues

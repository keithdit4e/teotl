# API Reference

API documentation for the Teotl framework. Signatures below match the source code; when in doubt, `inspect.signature(...)` on the class is authoritative.

## Table of Contents

- [Core](#core)
  - [Agent](#agent)
  - [Provider](#provider)
  - [Types](#types)
- [Primitives](#primitives)
  - [Skills](#skills)
  - [Memory](#memory)
  - [Planner-Worker Harness](#planner-worker-harness)
  - [Missions](#missions)
  - [Guardrails](#guardrails)
  - [Credentials](#credentials)
- [CLI](#cli)

---

## Core

The top-level `teotl` package exports only `Agent`, `EventBus`, `Session`, `Extension`, `Response`, and `ToolCall`. Import everything else from its own module.

### Agent

The main agent class that coordinates the LLM, skills, memory, and guardrails.

#### Class: `Agent`

```python
from teotl import Agent  # or: from teotl.core.agent import Agent
```

**Constructor:**

```python
class Agent:
    def __init__(
        self,
        provider: Provider,
        instructions: str | Callable[..., str] = "",
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
    ) -> None: ...
```

**Parameters:**

- `provider` (Provider): LLM provider (required)
- `instructions` (str | Callable[..., str]): System instructions for the agent
- `skills` (list[str] | None): Names of skills to enable, e.g. `["filesystem", "git"]`
- `policy` (str | Any): Guardrail policy: `"minimal"`, `"standard"` (default), `"strict"`, a `teotl.primitives.guardrails.Policy`, or a `Path` to a policy file
- `memory` (Any | None): Memory backend, e.g. `LocalMemory()`
- `extensions` (list[Extension] | None): Extensions to activate
- `tools` (list[ToolDefinition] | None): Additional tool definitions
- `session_dir` (Path | None): Directory for session persistence
- `max_turns` (int): Maximum turns per run (default: 50)
- `enable_injection_defense` (bool): Enable prompt injection detection (default: True)
- `cost_tracker` (Any | None): Cost tracking system
- `audit_logger` (Any | None): Audit logging system
- `checkpoint_manager` (Any | None): Checkpoint management
- `heartbeat_monitor` (Any | None): Heartbeat monitoring
- `state_manager` (Any | None): State management
- `enable_auto_compact` (bool | None): Auto-compact context (default: auto-enabled with memory)
- `compact_every` (int): Compact frequency in turns (default: 15)
- `max_context_tokens` (int | None): Max context size (default: auto-detected)

A `bash` tool is registered automatically; access to it is governed by the guardrail policy.

**Methods:**

##### `run`

```python
async def run(self, message: str, *, ui: UI | None = None) -> Response: ...
```

Run the agent on a user message.

- `message` (str): The user's input message
- `ui` (UI | None): UI adapter for confirmations and display (defaults to a headless UI)

Returns a [`Response`](#class-response).

**Example:**

```python
import asyncio
from teotl import Agent
from teotl.core.provider import AnthropicProvider


async def main():
    agent = Agent(provider=AnthropicProvider())
    response = await agent.run("Hello, how are you?")
    print(response.text)


asyncio.run(main())
```

##### `register_tool`

```python
def register_tool(
    self,
    name: str,
    description: str,
    handler: Callable,
    parameters: dict[str, Any] | None = None,
    *,
    risk: str = "low",
) -> None: ...
```

Register a custom tool. `parameters` is a JSON schema describing the tool's arguments.

The handler can be a regular function or an async function. It's called with the tool call's arguments as keyword arguments, and its return value is converted to a string and sent back to the model. If it raises, the error message is sent back instead, so the model can react to it.

Guardrails treat custom tools as low risk unless you say otherwise. Pass `risk=` to change that:

| `risk` | `minimal` policy | `standard` policy | `strict` policy |
|---|---|---|---|
| `"low"` (default) | runs | runs | asks first |
| `"medium"` | runs | asks first | asks first |
| `"high"` | asks first | asks first | blocked |
| `"critical"` | asks first | blocked | blocked |

```python
agent.register_tool("send_invoice", "Email an invoice to a customer", send_invoice, params, risk="medium")
```

Registering a tool name that already exists replaces the earlier tool. Names may contain letters, digits, `_` and `-` (at most 64 characters).

**Example:**

```python
async def get_weather(location: str) -> str:
    return f"Sunny in {location}"


agent.register_tool(
    name="get_weather",
    description="Get the current weather for a city",
    handler=get_weather,
    parameters={
        "type": "object",
        "properties": {"location": {"type": "string"}},
        "required": ["location"],
    },
)
```

##### Skill methods

```python
async def activate_skill(self, skill_name: str) -> str: ...
def deactivate_skill(self, skill_name: str) -> None: ...
def list_skills(self) -> dict[str, str]: ...
def list_active_skills(self) -> list[str]: ...
```

`activate_skill` raises `SkillNotFound` (from `teotl.primitives.skills.registry`) if the name is not registered.

##### Memory methods

These require the agent to have a memory backend; otherwise they raise `ValueError("Memory system not initialized")`.

```python
async def remember(
    self,
    content: str,
    *,
    importance: int = 5,
    tags: list[str] | None = None,
    ttl_days: int | None = None,
) -> str: ...
async def recall(self, query: str, *, limit: int = 10) -> list: ...
async def forget(self, memory_id: str) -> bool: ...
async def list_memories(self, *, limit: int = 100, offset: int = 0) -> list: ...
```

- `remember` returns the new memory ID. `importance` is 1-10; `ttl_days=None` uses an importance-based default.

##### `register_command`

```python
def register_command(self, name: str, handler: Callable) -> None: ...
```

Store a slash-command handler (e.g. `"/undo"`) on the agent. Note: the built-in `teotl chat` REPL handles only its own fixed commands and does not currently dispatch agent-registered commands.

##### `register_extension`

```python
def register_extension(self, extension: Extension) -> None: ...
```

Activate an extension on this agent.

> **Planner-worker:** there is no `Agent.create_planner_worker`. Use [`PlannerWorkerHarness`](#planner-worker-harness).

---

### Provider

LLM provider abstraction for model-agnostic agent code.

#### Class: `Provider` (Abstract)

```python
from teotl.core.provider import Provider
```

**Members:**

```python
class Provider:
    async def complete(
        self,
        *,
        system: str = "",
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResult: ...

    def estimate_tokens(self, text: str) -> int: ...

    @property
    def context_window(self) -> int: ...  # max context size in tokens

    @property
    def model_name(self) -> str: ...
```

`CompletionResult` (in `teotl.core.types`) has fields `content`, `tool_calls`, `done`, `usage`, `raw`, `assistant_content`.

---

#### Class: `AnthropicProvider`

Anthropic Claude provider. Requires `pip install "teotl[anthropic]"`.

```python
from teotl.core.provider import AnthropicProvider
```

**Constructor:**

```python
class AnthropicProvider(Provider):
    def __init__(
        self,
        model: str = "claude-sonnet-5-5",
        api_key: str | None = None,
        max_tokens: int = 8192,
    ) -> None: ...
```

- `model` (str): Model ID (default: `"claude-sonnet-5-5"`)
- `api_key` (str | None): API key (default: the Anthropic SDK reads `ANTHROPIC_API_KEY`)
- `max_tokens` (int): Max tokens per response (default: 8192)

**Claude model IDs** (no date suffix):
- `claude-sonnet-5-5` - Default; general use and planning
- `claude-haiku-4-5` - Fast, lower cost; recommended for workers
- `claude-opus-5-5` - Most capable
- `claude-fable-5-1`

**Example:**

```python
provider = AnthropicProvider(
    model="claude-sonnet-5-5",
    max_tokens=4096,
)
```

---

#### Class: `OpenAIProvider`

OpenAI provider. Requires `pip install "teotl[openai]"`.

```python
from teotl.core.provider import OpenAIProvider
```

**Constructor:**

```python
class OpenAIProvider(Provider):
    def __init__(
        self,
        model: str = "gpt-5.6-terra",
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 8192,
    ) -> None: ...
```

- `model` (str): Model name (default: `"gpt-5.6-terra"`)
- `api_key` (str | None): API key (default: the OpenAI SDK reads `OPENAI_API_KEY`)
- `base_url` (str | None): Custom API base URL, passed to the OpenAI client
- `max_tokens` (int): Max tokens per response (default: 8192)

**Example:**

```python
provider = OpenAIProvider(
    model="gpt-5.6-terra",
    max_tokens=2048,
)
```

**Which model:** `gpt-5.6-terra` (default) for general and planner use, `gpt-5.6-sol` when you need more capability, and `gpt-5.6-luna` as a cheap worker. Teotl uses OpenAI's Chat Completions API. The GPT-6 models (`gpt-6.1-sol`, `gpt-6-luna`, `gpt-6-astra`) don't fully support tool calling there, because OpenAI requires its Responses API for that, so Teotl logs a warning if you give them tools.

---

#### Class: `GeminiProvider`

Google Gemini provider. Requires `pip install "teotl[google]"`.

```python
from teotl.core.provider import GeminiProvider
```

**Constructor:**

```python
class GeminiProvider(Provider):
    def __init__(
        self,
        model: str = "gemini-3.8-flash",
        api_key: str | None = None,
        max_tokens: int = 8192,
    ) -> None: ...
```

- `model` (str): Model name (default: `"gemini-3.8-flash"`). `gemini-3.5-flash-lite` is the cheap option. Google limits the Gemini 2.5 models to projects that already used them, so new projects should use the 3.x models.
- `api_key` (str | None): API key (default: the Gemini SDK reads `GOOGLE_API_KEY`)

---

#### Class: `OllamaProvider`

Ollama local model provider. Requires `pip install "teotl[ollama]"`.

```python
from teotl.core.provider import OllamaProvider
```

**Constructor:**

```python
class OllamaProvider(Provider):
    def __init__(
        self,
        model: str = "llama3",
        host: str = "http://localhost:11434",
    ) -> None: ...
```

- `model` (str): Model name (default: `"llama3"`)
- `host` (str): Ollama server URL (default: `"http://localhost:11434"`)

**Example:**

```python
provider = OllamaProvider(
    model="llama3",
    host="http://localhost:11434",
)
```

---

### Types

Core type definitions in `teotl.core.types`.

#### Class: `Response`

```python
from teotl.core.types import Response
```

Dataclass returned by `Agent.run`:

```python
@dataclass
class Response:
    text: str
    messages: list[Message] = field(default_factory=list)
    tool_calls_made: list[ToolCall] = field(default_factory=list)
    tokens_used: int = 0
    cost: float = 0.0
```

---

#### Class: `ToolCall`

```python
from teotl.core.types import ToolCall
```

```python
@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]
```

---

#### Class: `ToolDefinition`

```python
from teotl.core.types import ToolDefinition
```

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)  # JSON schema
```

---

#### Class: `Message`

```python
from teotl.core.types import Message
```

```python
@dataclass
class Message:
    id: str
    role: Role  # "system", "user", "assistant", "tool"
    content: str
    parent_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    compact: bool = False
```

---

## Primitives

### Skills

Skills are folders containing a `SKILL.md` file (YAML frontmatter plus instructions). They are enabled by name; there is no `Skill` base class to subclass. See [CUSTOM_SKILLS_QUICKSTART.md](CUSTOM_SKILLS_QUICKSTART.md) to write your own.

**Bundled skills:** `claude_code`, `filesystem`, `git`, `github`, `spec_kit`, `web`.

**Search paths:** bundled skills, `~/.teotl/skills/`, and directories listed in `TEOTL_SKILLS_PATH` (colon-separated; legacy `TEOTL_SKILLS_PATH` is also read). To install a custom skill, copy its folder into `~/.teotl/skills/`.

**Usage:**

```python
agent = Agent(provider=provider, skills=["filesystem", "git"])
```

#### Class: `SkillRegistry`

The agent creates and manages its registry for you; direct use is rarely needed.

```python
from teotl.primitives.skills.registry import SkillRegistry
```

```python
class SkillRegistry:
    def __init__(self, enabled: list[str] | None = None) -> None: ...

    async def activate(self, skill_name: str) -> str: ...
    def deactivate(self, skill_name: str) -> None: ...
    def deactivate_all(self) -> None: ...
    def is_active(self, skill_name: str) -> bool: ...
    def get_active_instructions(self) -> str: ...
    def get_descriptions(self) -> str: ...

    @property
    def registered_count(self) -> int: ...

    @property
    def active_count(self) -> int: ...
```

---

### Memory

Context persistence across conversations. Requires `pip install "teotl[memory]"`.

#### Class: `LocalMemory`

Local SQLite-based memory storage.

```python
from teotl.primitives.memory.local import LocalMemory
```

**Constructor:**

```python
class LocalMemory:
    def __init__(
        self,
        path: Path | str | None = None,
        *,
        auto_cleanup: bool = True,
        max_memories: int = 10000,
    ) -> None: ...
```

- `path` (Path | str | None): Database path (default: `~/.teotl/memory.db`)
- `auto_cleanup` (bool): Automatically clean up expired memories (default: True)
- `max_memories` (int): Storage limit (default: 10000)

**Methods:**

```python
async def remember(
    self,
    content: str,
    metadata: MemoryMeta | None = None,
    ttl_days: int | None = None,
) -> str: ...  # returns memory ID
async def recall(self, query: str, *, limit: int = 10) -> list[Memory]: ...
async def forget(self, memory_id: str) -> bool: ...
async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[Memory]: ...
async def count(self) -> int: ...
async def cleanup_expired(self) -> int: ...
async def cleanup_by_storage_limit(self, max_memories: int = 10000) -> int: ...
async def get_retention_stats(self) -> dict: ...
def format_for_context(self, memories: list[Memory], *, token_budget: int = 500) -> str: ...
def close(self) -> None: ...
```

`MemoryMeta` (from `teotl.core.types`) has fields `source="manual"`, `tags=[]`, `importance=5`, `session_id=None`. `Memory` has fields `id`, `content`, `metadata`, `created`, `last_accessed`, `access_count`, `expires_at`.

**Example:**

```python
from teotl.core.types import MemoryMeta
from teotl.primitives.memory.local import LocalMemory

memory = LocalMemory()
memory_id = await memory.remember(
    "User prefers Python over JavaScript",
    MemoryMeta(tags=["preferences"]),
)

results = await memory.recall("programming language", limit=5)
for mem in results:
    print(mem.content)

memory.close()
```

To give an agent memory, pass it to the constructor: `Agent(provider=provider, memory=LocalMemory())`.

---

#### Class: `EncryptedMemory`

A `LocalMemory` subclass that encrypts memory content at rest.

```python
from teotl.primitives.memory.encrypted import EncryptedMemory
```

**Constructor:**

```python
class EncryptedMemory(LocalMemory):
    def __init__(
        self,
        path: Path | str | None = None,
        encryption_key: bytes | None = None,
    ) -> None: ...
```

- `path` (Path | str | None): Database path (default: `~/.teotl/memory.db`)
- `encryption_key` (bytes | None): Fernet key (default: an existing key is loaded or a new one is created)

**Methods:** Same as `LocalMemory`, plus `migrate_from_plaintext(dry_run: bool = False) -> dict`.

---

### Planner-Worker Harness

Runs a planner model (writes a plan) and a cheaper worker model (executes steps). Using `claude-haiku-4-5` as the worker costs about half the per-token price of an all-Sonnet setup.

```python
from teotl.primitives.harness import PlannerWorkerHarness
```

**Constructor:**

```python
class PlannerWorkerHarness:
    def __init__(
        self,
        agent_id: str,
        planner_provider: Provider,
        worker_provider: Provider,
        workspace_dir: Path | None = None,
        worker_skills: list[str] | None = None,
        worker_policy: SecurityPolicy | str = "autonomous-dev",
        planner_instructions: str | None = None,
        worker_instructions: str | None = None,
        enable_janitor: bool = True,
        janitor_compact_every: int = 5,
        janitor_max_tokens: int = 10000,
        enable_heartbeat: bool = True,
        heartbeat_check_every: int = 5,
        heartbeat_stuck_threshold: int = 10,
        heartbeat_error_threshold: int = 5,
        enable_cost_tracking: bool = True,
        cost_tracker: CostTracker | None = None,
        require_approval_for_continuation: bool = True,
        max_plan_steps: int = 8,
        approval_callback: Callable[[CycleApprovalRequest], bool] | None = None,
        halt_on_critical_escalation: bool = True,
        enable_checkpoints: bool = True,
        checkpoint_manager: CheckpointManager | None = None,
    ): ...
```

`worker_policy` uses the security presets from `teotl.core.security.SecurityPolicy` (`strict`, `moderate`, `permissive`, `autonomous-dev`), which are separate from the agent `policy=` presets. The worker's tool calls are checked by guardrails mapped from that preset (`strict`→`strict`, `moderate`/`autonomous-dev`→`standard`, `permissive`→`minimal`). A step whose target file is on the preset's blocked or read-only list is refused before it runs. Bash commands are not confined to a directory.

`max_plan_steps` caps the plan length; the planner is told to use as few steps as the goals need.

**How a step's success is decided:** the worker must end its reply with `STEP_STATUS: DONE` (or `STEP_STATUS: FAILED - <reason>`). A step counts as done only if all of these hold:
- the reply ends with `STEP_STATUS: DONE`
- the worker actually used a tool
- none of its tool calls was blocked by guardrails or failed
- the step's target file exists afterward, when the plan names a concrete file

Otherwise the step is retried with the failure reason as feedback. If it still fails after `max_retries`, it's marked skipped (⊘ in PLAN.md). Retries go through the same safety checks as the first attempt.

**Methods:**

```python
async def plan(self, goals: str, context: str | None = None, force_replan: bool = False) -> Any: ...
async def execute_next_step(self, max_retries: int = 3) -> WorkerResult: ...
async def execute_all_steps(self, max_retries: int = 3, stop_on_failure: bool = False) -> list[WorkerResult]: ...
def is_complete(self) -> bool: ...
def get_progress(self) -> dict: ...
async def refine_plan(self, feedback: str) -> Any: ...
def reset(self) -> None: ...
async def run_supervised_cycle(
    self,
    goals: str,
    max_cycles: int = 3,
    max_retries_per_step: int = 3,
    context: str | None = None,
) -> SupervisedResult: ...
```

`WorkerResult` has fields `success`, `step` (a `PlanStep` with `number`, `description`, ...), `response`, `tools_used`, `error`.

**Example:**

```python
from pathlib import Path

from teotl.core.provider import AnthropicProvider
from teotl.primitives.harness import PlannerWorkerHarness

harness = PlannerWorkerHarness(
    agent_id="code-quality",
    planner_provider=AnthropicProvider(model="claude-sonnet-5-5"),
    worker_provider=AnthropicProvider(model="claude-haiku-4-5"),
    workspace_dir=Path(".teotl/code-quality"),
    worker_skills=["filesystem", "git"],
)

plan = await harness.plan(goals="Fix all linting errors")  # writes PLAN.md
while not harness.is_complete():
    result = await harness.execute_next_step()
    print(result.step.number, result.success, result.error)
```

---

### Missions

Missions are recurring scheduled work records executed by the daemon. They are not run directly from Python (there is no `Mission.from_file`, `Mission.from_dict`, or `mission.run()`).

```python
from teotl.primitives.missions import (
    Mission,
    MissionBudget,
    MissionExecution,
    MissionInterval,
    MissionState,
    MissionStore,
)
```

**Defining missions** in the daemon config YAML (see `examples/full_config_reference.yaml` for the full schema):

```yaml
missions:
  - description: "Weekly code quality review"
    interval: WEEKLY   # HOURLY, DAILY, WEEKLY
    can_be_interrupted: true
    interrupt_threshold: URGENT
```

Run the daemon with `python -m teotl.daemon.run --config config.yaml [--agent-id ID]`.

#### Class: `Mission`

A pydantic model. Key fields:

- `id` (str): Auto-generated
- `description` (str): 1-2000 characters (required)
- `state` (MissionState): `active` (default), `paused`, `completed`, `failed`, `cancelled`
- `interval` (MissionInterval): `once`, `minutes_5`, `minutes_10`, `minutes_30`, `hourly`, `daily`, `weekly`, `manual` (default)
- `budget` (MissionBudget): `max_api_calls`, `max_cost_usd`, `max_duration_seconds` (all optional)
- `can_be_interrupted` (bool): Default True
- `interrupt_threshold` (Priority): Default `URGENT`
- `execution_count`, `success_count`, `failure_count` (int)
- `last_executed_at`, `next_execution_at` (datetime | None)
- `context` (dict[str, Any]), `tags` (list[str])

**Methods:** `pause()`, `resume()`, `complete()`, `fail(error: str | None = None)`, `cancel()`.

#### Class: `MissionStore`

SQLite-backed mission storage.

```python
class MissionStore:
    def __init__(self, path: Path | str | None = None) -> None: ...  # default ~/.teotl/missions.db

    async def create(self, mission: Mission) -> str: ...
    async def get(self, mission_id: str) -> Mission | None: ...
    async def update(self, mission: Mission) -> bool: ...
    async def delete(self, mission_id: str) -> bool: ...
    async def list_all(self, *, state: MissionState | None = None, limit: int = 100, offset: int = 0) -> list[Mission]: ...
    async def list_active(self) -> list[Mission]: ...
    async def list_due(self) -> list[Mission]: ...
    async def count(self, state: MissionState | None = None) -> int: ...
    async def record_execution(self, execution: MissionExecution) -> str: ...
    async def get_executions(self, mission_id: str, *, limit: int = 10) -> list[MissionExecution]: ...
    def close(self) -> None: ...
```

---

### Guardrails

Security policies and enforcement for agent tool calls. Normally you just pass `policy=` to `Agent`; the agent builds the engine itself.

#### Class: `Policy`

```python
from teotl.primitives.guardrails import Policy
```

**Constructor and class methods:**

```python
class Policy:
    def __init__(self, config: dict[str, Any]) -> None: ...

    @classmethod
    def from_preset(cls, name: str) -> "Policy": ...  # "minimal", "standard", or "strict"

    @classmethod
    def from_file(cls, path: Path | str) -> "Policy": ...

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "Policy": ...

    def decide(self, action: Action) -> Decision: ...
    def block_reason(self, action: Action) -> str: ...
```

`from_preset` raises `ValueError` for an unknown preset name.

**Attributes:** `level`, `filesystem`, `bash`, `network`, `integrations`, `limits`, `trust_config`.

**Example:**

```python
from teotl import Agent
from teotl.primitives.guardrails import Policy

policy = Policy.from_preset("strict")
agent = Agent(provider=provider, policy=policy)
```

---

#### Class: `GuardrailEngine`

```python
from teotl.primitives.guardrails import GuardrailEngine
```

```python
class GuardrailEngine:
    def __init__(self, policy: str | Policy | Path = "standard") -> None: ...

    async def evaluate(self, event: EventResult, *, ui: UI = None, **kwargs: Any) -> EventResult: ...
```

---

#### Class: `RateLimiter`

```python
from teotl.primitives.guardrails.rate_limiter import RateLimiter
```

```python
class RateLimiter:
    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_cost_per_hour: float = 5.0,
        max_cost_per_day: float = 25.0,
        max_tokens_per_request: int = 200000,
    ) -> None: ...

    def check_rate_limit(self) -> tuple[bool, str]: ...
    def check_token_limit(self, tokens: int) -> tuple[bool, str]: ...
    def record_request(self, cost: float = 0.0, tokens: int = 0) -> None: ...
    def get_stats(self) -> dict[str, Any]: ...
    def reset_stats(self) -> None: ...
```

---

### Credentials

Secure credential storage.

#### Class: `CredentialStore`

```python
from teotl.primitives.integrations.credential_store import CredentialStore
```

**Class method:**

```python
@classmethod
def create(cls, backend: str | None = None, **kwargs) -> "CredentialStore": ...
```

- `backend` (str | None): `"keyring"`, `"file"`, `"environment"`, or `"aws_secrets"`. If `None`, the best available backend is auto-detected (environment if `TEOTL_ALLOW_ENV_AUTH=true`, then AWS Secrets Manager if an AWS region is set, then the OS keyring, then an encrypted file).
- `**kwargs`: Passed to the backend constructor

Raises `ValueError` for an unknown backend name and `RuntimeError` if the backend cannot be initialized or none is available.

**Methods** (synchronous):

```python
def save_credential(self, service: str, data: dict[str, Any]) -> None: ...
def load_credential(self, service: str) -> dict[str, Any]: ...  # ValueError if not found
def delete_credential(self, service: str) -> bool: ...
def list_services(self) -> list[str]: ...

@property
def backend_name(self) -> str: ...
```

**Example:**

```python
store = CredentialStore.create()  # auto-detect

store.save_credential("github", {"token": "ghp_..."})
creds = store.load_credential("github")
print(creds["token"])
print(store.list_services())
```

---

## CLI

Command-line interface. Available commands: `chat`, `memory`, `onboard`, `security`, `wizard`.

```bash
teotl --version
teotl --help
```

---

#### `teotl chat`

Start interactive chat mode.

```bash
teotl chat
teotl chat --skills filesystem,git
teotl chat --skills filesystem --skills git
teotl chat --agent my-agent
teotl chat --no-memory
```

**Options:**
- `--agent`, `-a` - Agent ID to load workspace files from
- `--skills`, `-s` - Skills to enable (comma-separated or repeated)
- `--no-memory` - Disable memory system

**Commands inside chat:**
- `/help` - Show help
- `/skills` - Show enabled skills
- `/memory` - Show recent memories
- `/clear` - Clear the screen
- `/exit`, `/quit` - Exit

---

#### `teotl onboard` / `teotl wizard`

Run the interactive setup wizard (`wizard` is an alias). It generates a `config.yaml` and, for planner-worker setups, a `run_planner_worker.py` script.

```bash
teotl onboard
```

---

#### `teotl memory`

Manage stored memories. Every subcommand accepts `--path PATH` to select the memory database.

```bash
# List memories
teotl memory list --limit 20 --offset 0

# Search memories
teotl memory search "user preferences" --limit 10

# Delete a memory
teotl memory delete <memory-id>

# Retention statistics
teotl memory stats

# Clean up expired/inactive memories
teotl memory cleanup --dry-run

# Export / import
teotl memory export memories.json
teotl memory import-memories memories.json
```

---

#### `teotl security`

View audit logs, generate compliance reports, and show security status.

```bash
teotl security logs --workspace ~/.teotl/my-agent --days 7
teotl security report --workspace ~/.teotl/my-agent --output report.json
teotl security status --workspace ~/.teotl/my-agent
```

---

#### Other entry points

- Daemon: `python -m teotl.daemon.run --config config.yaml [--agent-id ID]`
- Web dashboard (requires `teotl[web]`): `python -m teotl.web [--agents a,b] [--port 8080] [--host localhost]`

---

## Error Handling

### Common Exceptions

#### `ImportError`

Raised when an optional dependency is missing (e.g. a provider SDK).

```python
try:
    provider = AnthropicProvider()
except ImportError:
    print('Install the extra: pip install "teotl[anthropic]"')
```

#### `ValueError`

Raised for invalid parameters, unknown policy presets, missing credentials, or memory calls on an agent without memory.

```python
try:
    credential = store.load_credential("missing_service")
except ValueError:
    print("Credential not found")
```

#### `RuntimeError`

Raised when no credential backend is available or a requested backend fails to initialize.

```python
try:
    store = CredentialStore.create()
except RuntimeError:
    print("No credential backend available")
```

---

## Best Practices

### 1. Resource Cleanup

Close memory stores when done:

```python
memory = LocalMemory()
try:
    await memory.remember("Something")
finally:
    memory.close()
```

### 2. Error Handling

```python
try:
    response = await agent.run("Task")
except Exception as e:
    logger.error(f"Agent failed: {e}")
```

### 3. Type Hints

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

This reference covers Teotl `0.2.x`.

Minimum Python version: `3.11`

---

## See Also

- [Quick Start Guide](quickstart.md) - Get started quickly
- [Concepts](concepts.md) - Understand core concepts
- [Installation](installation.md) - Setup instructions
- [Architecture](ARCHITECTURE.md) - System design
- [Custom Skills Quickstart](CUSTOM_SKILLS_QUICKSTART.md) - Write your own skills
- [Examples](../examples/) - Real-world examples

---

**Questions?** Open an issue: https://github.com/keithdit4e/teotl/issues

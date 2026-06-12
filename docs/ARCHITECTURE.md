# Teotl: Python Agent Framework Architecture

> A platform for building any agent type. Minimal core, maximum extensibility.
> Open core: free framework + paid cloud services.

---

## 1. Positioning & Competitive Gap

### What exists (2025 landscape)

| Framework | Language | Core Strength | Key Weakness |
|-----------|----------|--------------|-------------|
| pi-mono | TypeScript | Extension system, minimal core, skills | No guardrails, no memory, TS-only |
| PydanticAI | Python | Type safety, validation, model-agnostic | No progressive disclosure, no built-in memory |
| LangGraph | Python | Graph-based workflows, checkpointing | Complex abstractions, steep learning curve |
| OpenAI Agents SDK | Python | Guardrails, tracing, handoffs | OpenAI-centric despite claims otherwise |
| CrewAI | Python | Multi-agent roles | Rigid role abstraction, poor single-agent DX |
| Strands | Python | Production-ready, AWS integration | AWS gravity, heavy infrastructure |

### The gap no one fills

**No Python framework treats guardrails, memory, integrations, AND progressive disclosure as core primitives.** Every framework either:

- Makes guardrails an afterthought (PydanticAI, LangGraph)
- Ignores context management entirely (all of them — MCP bloat is universal)
- Treats memory as "bring your own database" (all of them)
- Locks you into one agent pattern (CrewAI = roles, LangGraph = graphs)

### Teotl's thesis

Take pi-mono's philosophy (minimal core, extensions, skills) and rebuild it in Python with the four primitives that consumer-facing agents actually need baked into the foundation — not as optional plugins, but as load-bearing walls.

---

## 2. Design Principles

### Inherited from pi-mono (keep these)
1. **Minimal core** — the framework is a loop, an event bus, and primitives. Everything else is optional.
2. **Extensions over built-ins** — the right answer to "should this be in core?" is almost always no.
3. **CLI tools over protocols** — bash scripts + README > MCP server. Skills > tool schemas.
4. **Session as append-only log** — JSONL with id/parentId branching. Never mutate history.
5. **Compaction as first-class** — long conversations compress; design for it.

### New principles (where pi-mono was wrong or incomplete)
6. **Guardrails are infrastructure, not policy** — they live below the agent loop, not beside it.
7. **Memory is a primitive, not a plugin** — cross-session persistence is as fundamental as tool use.
8. **Progressive disclosure is the integration strategy** — context costs tokens. Every token is a tax.
9. **The framework should be safe by default** — unsafe is opt-in, not the other way around.
10. **Platform builders need escape hatches** — every primitive has a "bypass" for advanced users.

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│              (CLI / Web / Desktop / Custom)                   │
├─────────────────────────────────────────────────────────────┤
│                      Teotl Runtime                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Agent    │ │ Session  │ │ Event    │ │ Provider      │  │
│  │ Loop     │ │ Manager  │ │ Bus      │ │ Abstraction   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────┬───────┘  │
│       │            │            │               │           │
├───────┴────────────┴────────────┴───────────────┴───────────┤
│                    Core Primitives                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Guard-   │ │ Memory   │ │ Skills   │ │ Integrations  │  │
│  │ rails    │ │ System   │ │ Engine   │ │ Registry      │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Extension Layer                            │
│     Hooks · Middleware · Custom Tools · Event Listeners       │
├─────────────────────────────────────────────────────────────┤
│                    Execution Layer                            │
│          Sandbox · Subprocess · Container · Remote            │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Project Structure

```
teotl/
├── pyproject.toml              # Package config, entry points
├── teotl/
│   ├── __init__.py             # Public API surface
│   ├── core/
│   │   ├── agent.py            # Agent loop (the heart)
│   │   ├── session.py          # JSONL session management
│   │   ├── events.py           # Event bus + hook system
│   │   ├── provider.py         # LLM provider abstraction
│   │   └── types.py            # Core type definitions
│   ├── primitives/
│   │   ├── guardrails/
│   │   │   ├── engine.py       # Policy evaluation engine
│   │   │   ├── policy.py       # Declarative policy loader
│   │   │   ├── classifier.py   # Action classification (read/write/execute/network)
│   │   │   ├── bash_analyzer.py # Structural bash command analysis
│   │   │   ├── trust.py        # Progressive trust tracker
│   │   │   └── presets.py      # minimal / standard / strict
│   │   ├── memory/
│   │   │   ├── store.py        # Memory storage interface
│   │   │   ├── local.py        # SQLite-backed local memory
│   │   │   ├── context.py      # Memory injection into prompts
│   │   │   └── compactor.py    # Session → memory extraction
│   │   ├── skills/
│   │   │   ├── registry.py     # Skill discovery + loading
│   │   │   ├── loader.py       # SKILL.md parser (frontmatter + body)
│   │   │   ├── router.py       # Description-based skill matching
│   │   │   └── standard.py     # Built-in skill format spec
│   │   └── integrations/
│   │       ├── registry.py     # Integration catalog
│   │       ├── auth.py         # OAuth/API key management
│   │       ├── connector.py    # CLI script executor
│   │       └── mcp_bridge.py   # MCP escape hatch (meta-tool pattern)
│   ├── extensions/
│   │   ├── manager.py          # Extension loading + lifecycle
│   │   ├── hooks.py            # Hook definitions (tool_call, tool_result, etc.)
│   │   └── builtin/            # Bundled extensions
│   │       ├── audit.py        # Append-only audit logging
│   │       ├── undo.py         # File snapshot + rollback
│   │       └── observe.py      # Reasoning trace / /why command
│   ├── ui/
│   │   ├── base.py             # Abstract UI interface
│   │   ├── cli.py              # Rich terminal UI (default)
│   │   ├── web.py              # WebSocket-based web UI adapter
│   │   └── headless.py         # Programmatic / API mode
│   └── cloud/                  # ← Open core boundary
│       ├── __init__.py         # Cloud client stub (free tier: noop)
│       ├── sync.py             # Memory sync client
│       ├── analytics.py        # Usage analytics client
│       └── teams.py            # Team/shared workspace client
├── skills/                     # Community skill library
│   ├── filesystem/
│   │   └── SKILL.md
│   ├── git/
│   │   ├── SKILL.md
│   │   └── scripts/
│   ├── web/
│   │   ├── SKILL.md
│   │   └── scripts/
│   └── ...
├── policies/                   # Preset policy files
│   ├── minimal.json
│   ├── standard.json
│   └── strict.json
├── tests/
├── docs/
└── examples/
    ├── coding_agent/
    ├── research_agent/
    ├── customer_support/
    └── personal_assistant/
```

---

## 5. Core Primitives — Deep Design

### 5.1 Agent Loop

The simplest possible loop. Everything else hooks into it.

```python
# teotl/core/agent.py

class Agent:
    """The agent loop. Thin by design."""

    def __init__(
        self,
        provider: Provider,
        instructions: str | Callable = "",
        skills: list[str] | None = None,      # Skill names to enable
        policy: str | Policy = "standard",      # Guardrail policy
        memory: MemoryStore | None = None,      # Memory backend
        extensions: list[Extension] | None = None,
    ):
        self.provider = provider
        self.instructions = instructions
        self.session = Session()
        self.events = EventBus()
        self.guardrails = GuardrailEngine(policy)
        self.memory = memory or LocalMemory()
        self.skills = SkillRegistry(skills)
        self.extensions = ExtensionManager(extensions or [])

        # Wire up core hooks
        self.events.on("tool_call", self.guardrails.evaluate)
        self.events.on("turn_start", self.memory.inject_context)
        self.events.on("turn_start", self.skills.inject_descriptions)
        self.events.on("turn_end", self.memory.extract_if_needed)

    async def run(self, message: str, *, ui: UI = None) -> Response:
        """Single turn of the agent loop."""
        ui = ui or HeadlessUI()

        # 1. Build context
        context = await self._build_context(message)

        # 2. Agent loop (tool use may cause multiple LLM calls)
        while True:
            result = await self.provider.complete(context)

            if result.done:
                break

            # 3. Process tool calls
            for tool_call in result.tool_calls:
                # Event system handles guardrails, logging, etc.
                event = await self.events.emit("tool_call", tool_call, ui=ui)

                if event.blocked:
                    context.add_tool_result(tool_call.id, error=event.reason)
                    continue

                # Execute tool (skill scripts, bash, etc.)
                output = await self._execute_tool(tool_call)

                # Post-execution hooks (output filtering, undo snapshots)
                output = await self.events.emit("tool_result", output)
                context.add_tool_result(tool_call.id, result=output)

            context.add_assistant(result)

        # 4. Persist
        self.session.append(context)
        return result

    async def _build_context(self, message: str) -> Context:
        """Assemble the full context for this turn."""
        ctx = Context()

        # System prompt
        ctx.add_system(self._resolve_instructions())

        # Memory (relevant memories for this conversation)
        memories = await self.memory.recall(message, limit=10)
        if memories:
            ctx.add_system(f"## Relevant memories\n{memories.format()}")

        # Skill descriptions (~50 tokens each, always present)
        ctx.add_system(self.skills.get_descriptions())

        # Session history (with compaction if needed)
        ctx.add_history(self.session.get_messages())

        # User message
        ctx.add_user(message)

        return ctx
```

### 5.2 Guardrails Engine

Operates below the agent loop via the event system. Zero context cost.

```python
# teotl/primitives/guardrails/engine.py

class GuardrailEngine:
    """Declarative policy enforcement. No context tokens consumed."""

    def __init__(self, policy: str | Policy | Path):
        if isinstance(policy, str):
            self.policy = Policy.from_preset(policy)  # "minimal" | "standard" | "strict"
        elif isinstance(policy, Path):
            self.policy = Policy.from_file(policy)
        else:
            self.policy = policy

        self.trust = TrustTracker()
        self.audit = AuditLog()

    async def evaluate(self, event: ToolCallEvent, *, ui: UI) -> EventResult:
        """Called on every tool_call event. Returns allow/confirm/block."""

        # 1. Classify the action
        action = self._classify(event.tool_call)
        # → Action(type="write", target="/home/user/doc.txt", risk="medium")

        # 2. Check policy
        decision = self.policy.decide(action)
        # → "allow" | "confirm" | "block"

        # 3. Apply progressive trust
        if decision == "confirm" and self.trust.is_trusted(action):
            decision = "allow"  # User approved similar actions N times

        # 4. Execute decision
        if decision == "block":
            self.audit.log(action, "blocked", self.policy.block_reason(action))
            return EventResult(blocked=True, reason=self.policy.block_reason(action))

        if decision == "confirm":
            description = self._describe_action(action)
            approved = await ui.confirm(f"🛡️ {description}")

            if approved:
                self.trust.record_approval(action)
                self.audit.log(action, "approved_by_user")
                return EventResult(blocked=False)
            else:
                self.audit.log(action, "denied_by_user")
                return EventResult(blocked=True, reason="Denied by user")

        # Allow
        self.audit.log(action, "allowed")
        return EventResult(blocked=False)

    def _classify(self, tool_call: ToolCall) -> Action:
        """Classify tool call into action type."""
        if tool_call.name == "bash":
            return self._classify_bash(tool_call.args["command"])
        elif tool_call.name == "write_file":
            return Action(type="write", target=tool_call.args["path"])
        elif tool_call.name == "read_file":
            return Action(type="read", target=tool_call.args["path"])
        else:
            return Action(type="execute", target=tool_call.name)

    def _classify_bash(self, command: str) -> Action:
        """Structural analysis of bash commands. Not just regex."""
        parsed = BashAnalyzer.parse(command)
        # BashAnalyzer uses shlex + AST-level analysis:
        # - Detects pipes, redirects, subshells
        # - Identifies primary command and arguments
        # - Flags network access (curl, wget, ssh)
        # - Flags destructive ops (rm, chmod, chown)
        # - Flags sensitive path access (~/.ssh, ~/.aws)
        # - Detects pipe-to-bash patterns (curl | bash)
        return Action(
            type=parsed.action_type,
            target=parsed.primary_target,
            risk=parsed.risk_level,
            details=parsed.details,
        )
```

**Policy file format** (`~/.teotl/policy.json`):

```json
{
  "level": "standard",
  "filesystem": {
    "allow": ["~/projects/**", "~/Documents/**", "/tmp/**"],
    "deny": ["~/.ssh/**", "~/.aws/**", "~/.teotl/auth/**"],
    "confirm_write_outside_scope": true
  },
  "bash": {
    "block": ["rm -rf /", ":(){ :|:& };:", "curl * | bash", "wget * | bash"],
    "confirm": ["rm", "git push", "git reset --hard", "sudo", "docker", "pip install"],
    "allow": ["ls", "cat", "grep", "find", "echo", "cd", "pwd", "head", "tail", "wc"]
  },
  "network": {
    "allow_outbound": false,
    "allowed_hosts": ["api.github.com", "pypi.org"],
    "confirm_new_hosts": true
  },
  "integrations": {
    "gmail": { "read": "allow", "send": "confirm", "delete": "confirm" },
    "github": { "read": "allow", "push": "confirm", "delete": "block" }
  },
  "limits": {
    "max_files_per_turn": 20,
    "max_bash_commands_per_turn": 50,
    "cost_limit_session": 5.00,
    "cost_limit_daily": 25.00
  },
  "trust": {
    "auto_approve_after": 3,
    "session_scoped": true,
    "persist_patterns": false
  }
}
```

### 5.3 Memory System

Memory is a core primitive, not an afterthought. Three layers:

```python
# teotl/primitives/memory/store.py

class MemoryStore(Protocol):
    """Interface that all memory backends implement."""

    async def remember(self, content: str, metadata: MemoryMeta) -> str:
        """Store a memory. Returns memory ID."""
        ...

    async def recall(self, query: str, *, limit: int = 10) -> list[Memory]:
        """Retrieve relevant memories for a query."""
        ...

    async def forget(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        ...

    async def summarize_session(self, session: Session) -> list[Memory]:
        """Extract memories from a completed session."""
        ...


# teotl/primitives/memory/local.py

class LocalMemory(MemoryStore):
    """SQLite-backed local memory. Zero external dependencies."""

    def __init__(self, path: Path = None):
        self.path = path or Path.home() / ".teotl" / "memory.db"
        self.db = sqlite3.connect(self.path)
        self._ensure_schema()

    async def remember(self, content: str, metadata: MemoryMeta) -> str:
        memory_id = ulid.new().str
        embedding = self._embed(content)  # Local embedding (sentence-transformers)
        self.db.execute(
            "INSERT INTO memories (id, content, embedding, source, created, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (memory_id, content, embedding, metadata.source, datetime.now(), json.dumps(metadata.tags))
        )
        return memory_id

    async def recall(self, query: str, *, limit: int = 10) -> list[Memory]:
        """Hybrid retrieval: embedding similarity + keyword + recency."""
        query_embedding = self._embed(query)

        # SQLite with vec0 extension for vector similarity
        # Falls back to keyword search if vec0 not available
        results = self._hybrid_search(query, query_embedding, limit)
        return [Memory(**row) for row in results]

    async def summarize_session(self, session: Session) -> list[Memory]:
        """Use LLM to extract memorable facts from a session."""
        # This is the session → memory bridge
        # Called at session end (or via compaction)
        transcript = session.format_for_extraction()

        extraction_prompt = """
        Extract factual memories from this conversation.
        Return as JSON array of objects with: content, tags, importance (1-10).
        Focus on: user preferences, decisions made, facts learned,
        project context, relationships mentioned.
        Do NOT memorize: pleasantries, meta-conversation, transient state.
        """

        # Uses a cheap/fast model for extraction
        memories_raw = await self._extraction_provider.complete(
            extraction_prompt + transcript
        )
        memories = json.loads(memories_raw)

        stored = []
        for m in memories:
            if m["importance"] >= 5:  # Threshold for remembering
                mid = await self.remember(
                    m["content"],
                    MemoryMeta(source="session", tags=m["tags"])
                )
                stored.append(mid)

        return stored

    def _embed(self, text: str) -> bytes:
        """Local embedding via sentence-transformers (no API call)."""
        # Uses all-MiniLM-L6-v2 by default (~80MB, runs on CPU)
        # Configurable: can swap to API-based embeddings
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        vector = self._embedder.encode(text)
        return vector.tobytes()
```

**Memory context injection** (how memories enter the prompt):

```python
# teotl/primitives/memory/context.py

class MemoryContext:
    """Injects relevant memories into agent context. Budget-aware."""

    def __init__(self, store: MemoryStore, token_budget: int = 500):
        self.store = store
        self.token_budget = token_budget  # Max tokens for memory block

    async def inject(self, event: TurnStartEvent) -> None:
        """Called on turn_start. Adds memories to context."""
        memories = await self.store.recall(event.message, limit=10)

        if not memories:
            return

        # Format within budget
        formatted = self._format_within_budget(memories)
        event.context.add_system(
            f"## What you remember about this user\n{formatted}",
            priority="low"  # Compacted first when context is tight
        )

    def _format_within_budget(self, memories: list[Memory]) -> str:
        """Pack as many relevant memories as fit in token budget."""
        lines = []
        tokens_used = 0
        for m in memories:
            line = f"- {m.content}"
            line_tokens = estimate_tokens(line)
            if tokens_used + line_tokens > self.token_budget:
                break
            lines.append(line)
            tokens_used += line_tokens
        return "\n".join(lines)
```

### 5.4 Skills Engine (Progressive Disclosure)

The core insight from our research: skills beat MCP for context efficiency.

```python
# teotl/primitives/skills/registry.py

class SkillRegistry:
    """
    Progressive disclosure for integrations and capabilities.

    Cost model:
    - 10 skills loaded = ~500 tokens (descriptions only)
    - Skill activated = ~500-2000 tokens (full SKILL.md, temporary)
    - MCP equivalent = ~30,000+ tokens (all tool schemas, permanent)
    """

    def __init__(self, enabled: list[str] | None = None):
        self.skills: dict[str, SkillMeta] = {}
        self.active: dict[str, SkillFull] = {}  # Currently loaded
        self._discover(enabled)

    def _discover(self, enabled: list[str] | None) -> None:
        """Scan skill directories for SKILL.md files."""
        search_paths = [
            Path.home() / ".teotl" / "skills",      # User skills
            Path(__file__).parent.parent / "skills",  # Built-in skills
        ]

        for path in search_paths:
            if not path.exists():
                continue
            for skill_dir in path.iterdir():
                if (skill_dir / "SKILL.md").exists():
                    meta = SkillLoader.parse_frontmatter(skill_dir / "SKILL.md")
                    if enabled is None or meta.name in enabled:
                        self.skills[meta.name] = meta

    def get_descriptions(self) -> str:
        """
        Returns compact descriptions for ALL enabled skills.
        This is always in context. ~50 tokens per skill.
        """
        if not self.skills:
            return ""

        lines = ["## Available capabilities"]
        for name, meta in self.skills.items():
            lines.append(f"- **{name}**: {meta.description}")
        lines.append("\nTo use a capability, just ask. Instructions will be provided.")
        return "\n".join(lines)

    async def activate(self, skill_name: str) -> str:
        """
        Load full SKILL.md into context. Called when LLM decides
        it needs a skill based on the description.
        """
        if skill_name in self.active:
            return self.active[skill_name].instructions

        meta = self.skills.get(skill_name)
        if not meta:
            raise SkillNotFound(skill_name)

        full = SkillLoader.parse_full(meta.path / "SKILL.md")
        self.active[skill_name] = full
        return full.instructions

    def deactivate(self, skill_name: str) -> None:
        """Remove skill instructions from context (e.g., after compaction)."""
        self.active.pop(skill_name, None)


# SKILL.md format

SKILL_FORMAT = """
---
name: gmail
version: 1.0.0
description: "Send, read, and search email"  # ← Always in context (~15 tokens)
auth: oauth2
triggers:
  - email
  - mail
  - inbox
  - send message
---

# Gmail Integration

## Setup
Run `teotl auth gmail` to connect your Google account.

## Commands

### List recent emails
```bash
teotl-gmail list --limit 10
```

### Read an email
```bash
teotl-gmail read <message_id>
```

### Send an email
```bash
teotl-gmail send --to "user@example.com" --subject "Hello" --body "Content here"
```

### Search emails
```bash
teotl-gmail search "from:boss@company.com after:2025/01/01"
```

## Notes
- All commands output JSON by default. Add `--format human` for readable output.
- Attachments: use `--attach /path/to/file` with send.
- The agent should always confirm before sending emails.
"""
```

### 5.5 Integration Registry

Builds on skills. Manages auth and provides the CLI bridge.

```python
# teotl/primitives/integrations/registry.py

class IntegrationRegistry:
    """
    Manages service connections. Auth is stored locally,
    skill scripts handle the actual API calls.
    """

    def __init__(self, auth_path: Path = None):
        self.auth_path = auth_path or Path.home() / ".teotl" / "auth"
        self.connected: dict[str, AuthCredential] = {}
        self._load_credentials()

    async def connect(self, service: str, *, ui: UI) -> bool:
        """Interactive auth flow for a service."""
        skill = self.skills.get(service)
        if not skill:
            raise IntegrationNotFound(service)

        if skill.auth_type == "oauth2":
            return await self._oauth_flow(service, skill, ui)
        elif skill.auth_type == "api_key":
            return await self._api_key_flow(service, skill, ui)
        elif skill.auth_type == "none":
            return True

    async def execute(self, service: str, command: str, args: dict) -> str:
        """Execute an integration command via its CLI script."""
        script = self._resolve_script(service, command)
        env = self._build_env(service)  # Injects auth tokens as env vars

        result = await subprocess.run(
            [script] + self._build_args(args),
            env=env,
            capture_output=True,
            timeout=30,
        )
        return result.stdout.decode()

    def _build_env(self, service: str) -> dict:
        """Inject auth tokens as environment variables. Never in context."""
        cred = self.connected.get(service)
        if not cred:
            raise NotConnected(service)

        env = os.environ.copy()
        env[f"TEOTL_{service.upper()}_TOKEN"] = cred.access_token
        return env
```

### 5.6 MCP Escape Hatch

For when a skill doesn't exist but an MCP server does.

```python
# teotl/primitives/integrations/mcp_bridge.py

class MCPBridge:
    """
    Meta-tool pattern: 2 tools instead of N tool schemas.
    Reduces MCP bloat by 85-95%.

    Instead of loading all 26 tools from an MCP server (~18k tokens),
    register only discover + execute (~600 tokens fixed).
    """

    def __init__(self, servers: list[MCPServerConfig]):
        self.servers = {s.name: s for s in servers}
        self._tool_cache: dict[str, list[ToolSchema]] = {}

    def get_tools(self) -> list[Tool]:
        """Returns exactly 2 tools regardless of how many MCP servers."""
        return [
            Tool(
                name="mcp_discover",
                description="List available tools from an MCP server. "
                    f"Available servers: {', '.join(self.servers.keys())}",
                parameters={"server": "string"},
            ),
            Tool(
                name="mcp_execute",
                description="Execute a specific tool on an MCP server by name.",
                parameters={
                    "server": "string",
                    "tool": "string",
                    "args": "object",
                },
            ),
        ]

    async def discover(self, server_name: str) -> list[ToolSchema]:
        """List tools available on an MCP server. Cached."""
        if server_name not in self._tool_cache:
            server = self.servers[server_name]
            async with MCPClient(server.url) as client:
                self._tool_cache[server_name] = await client.list_tools()
        return self._tool_cache[server_name]

    async def execute(self, server_name: str, tool: str, args: dict) -> str:
        """Execute a specific tool on an MCP server."""
        server = self.servers[server_name]
        async with MCPClient(server.url) as client:
            return await client.call_tool(tool, args)
```

---

## 6. Event System & Extension Model

### Event Bus

Inspired by pi-mono's extension system, Pythonified.

```python
# teotl/core/events.py

class EventBus:
    """Typed async event bus. Extensions hook into this."""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler, *, priority: int = 0) -> None:
        """Register a handler. Lower priority = runs first."""
        self._handlers[event].append((priority, handler))
        self._handlers[event].sort(key=lambda x: x[0])

    async def emit(self, event: str, data: Any, **kwargs) -> EventResult:
        """Emit event. Handlers can modify data or block execution."""
        result = EventResult(data=data, **kwargs)
        for _, handler in self._handlers.get(event, []):
            result = await handler(result)
            if result.blocked:
                break  # Short-circuit on block
        return result


# Available events:
EVENTS = {
    "turn_start":    "Before LLM call. Inject context here.",
    "turn_end":      "After LLM responds. Extract memories here.",
    "tool_call":     "Before tool execution. Guardrails hook here.",
    "tool_result":   "After tool execution. Filter output here.",
    "session_start": "New session begins.",
    "session_end":   "Session ends. Persist state here.",
    "compact":       "Context window is getting full. Summarize.",
    "error":         "Something went wrong.",
    "bash_spawn":    "Before subprocess exec. Sandbox hook.",
}
```

### Extension Model

```python
# teotl/extensions/manager.py

class Extension(Protocol):
    """All extensions implement this interface."""
    name: str
    version: str

    def activate(self, agent: Agent) -> None:
        """Register hooks, modify agent behavior."""
        ...

    def deactivate(self, agent: Agent) -> None:
        """Clean up."""
        ...


# Example: Undo extension (bundled)

class UndoExtension(Extension):
    name = "undo"
    version = "1.0.0"

    def __init__(self, snapshot_dir: Path = None):
        self.snapshot_dir = snapshot_dir or Path.home() / ".teotl" / "snapshots"
        self.snapshots: list[Snapshot] = []

    def activate(self, agent: Agent) -> None:
        agent.events.on("tool_call", self._snapshot_before_write, priority=-10)
        agent.register_command("/undo", self._undo_command)

    async def _snapshot_before_write(self, event: EventResult) -> EventResult:
        action = classify(event.data)
        if action.type in ("write", "destructive"):
            target = Path(action.target)
            if target.exists():
                snapshot_path = self.snapshot_dir / f"{ulid.new()}-{target.name}"
                shutil.copy2(target, snapshot_path)
                self.snapshots.append(Snapshot(
                    original=target, backup=snapshot_path, timestamp=datetime.now()
                ))
        return event

    async def _undo_command(self, args: str, ui: UI) -> str:
        if not self.snapshots:
            return "Nothing to undo."
        snapshot = self.snapshots.pop()
        shutil.copy2(snapshot.backup, snapshot.original)
        return f"Restored {snapshot.original} to state before last edit."
```

---

## 7. Session Management

### Append-only JSONL (from pi-mono, enhanced)

```python
# teotl/core/session.py

@dataclass
class Message:
    id: str                  # ULID
    parent_id: str | None    # For branching
    role: str                # system | user | assistant | tool
    content: str
    timestamp: datetime
    metadata: dict           # tool calls, token counts, etc.
    compact: bool = False    # True if this is a compaction summary

class Session:
    """
    Append-only session log. Never mutate, only append.
    Supports branching (id/parent_id tree) and compaction.
    """

    def __init__(self, path: Path = None):
        self.path = path
        self.messages: list[Message] = []
        if path and path.exists():
            self._load()

    def append(self, message: Message) -> None:
        self.messages.append(message)
        if self.path:
            with open(self.path, "a") as f:
                f.write(message.to_json() + "\n")

    def get_messages(self, *, token_budget: int = None) -> list[Message]:
        """Get messages for context, respecting budget."""
        if token_budget is None:
            return self.messages

        # Walk backward from newest, filling budget
        selected = []
        tokens = 0
        for msg in reversed(self.messages):
            msg_tokens = estimate_tokens(msg.content)
            if tokens + msg_tokens > token_budget:
                break
            selected.insert(0, msg)
            tokens += msg_tokens

        return selected

    async def compact(self, provider: Provider) -> Message:
        """
        Compress older messages into a summary.
        Full history preserved in JSONL. Only context is compressed.
        """
        # Keep last N messages verbatim
        keep_recent = 10
        to_compact = self.messages[:-keep_recent]

        if len(to_compact) < 5:
            return  # Not enough to compact

        summary = await provider.complete(
            "Summarize this conversation history. Preserve: "
            "key decisions, facts, user preferences, current task state. "
            "Drop: pleasantries, failed attempts, redundant exploration.\n\n"
            + format_messages(to_compact)
        )

        compact_msg = Message(
            id=ulid.new().str,
            role="system",
            content=f"## Conversation summary\n{summary}",
            compact=True,
        )

        # Replace compacted messages in active context (not in JSONL!)
        self.messages = [compact_msg] + self.messages[-keep_recent:]
        return compact_msg
```

---

## 8. Provider Abstraction

Model-agnostic. Swap providers without changing agent code.

```python
# teotl/core/provider.py

class Provider(Protocol):
    """LLM provider interface."""

    async def complete(self, context: Context) -> CompletionResult:
        ...

    def estimate_tokens(self, text: str) -> int:
        ...

    @property
    def context_window(self) -> int:
        ...


class AnthropicProvider(Provider):
    """Claude via Anthropic API."""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str = None):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, context: Context) -> CompletionResult:
        response = await self.client.messages.create(
            model=self.model,
            system=context.system_prompt,
            messages=context.messages,
            tools=context.tools,
            max_tokens=8192,
        )
        return CompletionResult.from_anthropic(response)


class OpenAIProvider(Provider):
    """GPT via OpenAI API."""
    ...

class OllamaProvider(Provider):
    """Local models via Ollama."""
    ...

class LiteLLMProvider(Provider):
    """Any model via LiteLLM proxy."""
    ...
```

---

## 9. Open Core Model

### What's included (open source)

The full Teotl framework is open source and free:

- Agent loop, session management, event system
- All four primitives (guardrails, memory, skills, integrations)
- Local memory (SQLite + local embeddings)
- All preset policies
- Extension system + bundled extensions
- CLI UI
- Community skill library
- Provider abstraction (bring your own API keys)

### Cloud services (coming soon)

Optional cloud services for teams and enterprises are planned but not yet available. The core framework is fully functional without any cloud dependencies.

---

## 10. User Experience

### CLI (default, ships with framework)

```bash
# Install
pip install -e ".[anthropic]"  # from cloned repo

# First run (interactive setup)
teotl init
# → Choose provider (Anthropic/OpenAI/Ollama/other)
# → Set API key
# → Choose guardrail level (minimal/standard/strict)
# → Discover available skills

# Run
teotl                          # Interactive REPL
teotl "refactor auth.py"       # One-shot
teotl --skill gmail,github     # Enable specific skills
teotl --policy strict          # Override policy
teotl --resume                 # Continue last session

# Manage
teotl skills list              # Show available skills
teotl skills install slack     # Install from skill store
teotl auth gmail               # Connect a service
teotl memory search "project"  # Query memories
teotl memory forget <id>       # Delete a memory
teotl audit show               # View recent audit log
teotl policy edit              # Open policy.json in editor
```

### Web UI (adapter)

```python
# teotl/ui/web.py — thin adapter over the core

from teotl import Agent, WebUI

agent = Agent(
    provider=AnthropicProvider(),
    policy="standard",
)

# WebSocket-based UI
app = WebUI(agent, port=8080)
app.run()
# → Opens browser with chat interface
# → Guardrail confirmations appear as modals
# → Audit log visible in sidebar
# → Memory browser accessible via /memory
```

### Programmatic (for platform builders)

```python
# The API that platform builders use

from teotl import Agent, HeadlessUI, AnthropicProvider, Policy

# Custom agent with full control
agent = Agent(
    provider=AnthropicProvider(model="claude-sonnet-4-20250514"),
    instructions="You are a customer support agent for Acme Corp.",
    skills=["knowledge_base", "ticketing"],
    policy=Policy.from_dict({
        "level": "strict",
        "bash": {"block": ["*"]},  # No bash access
        "integrations": {
            "zendesk": {"read": "allow", "write": "allow"},
        }
    }),
    memory=LocalMemory(path="./customer_memory.db"),
    extensions=[
        AuditExtension(sink=CloudAuditSink()),
        CustomEscalation(),
    ],
)

# Run programmatically
response = await agent.run(
    "Customer says they were charged twice",
    ui=HeadlessUI(auto_approve=True),  # No human in loop
)
```

---

## 11. Implementation Roadmap

### Phase 0: Foundation (Weeks 1-4)
- [ ] Core agent loop with tool execution
- [ ] Event bus + hook system
- [ ] Anthropic + OpenAI providers
- [ ] JSONL session management
- [ ] Basic CLI UI (Rich-based)
- [ ] `teotl init` / `teotl run`

### Phase 1: Guardrails (Weeks 5-8)
- [ ] Policy file format + presets
- [ ] Action classifier (file ops, bash analysis)
- [ ] Confirm/block/allow flow
- [ ] Progressive trust tracker
- [ ] Audit log (JSONL)
- [ ] Undo extension

### Phase 2: Skills (Weeks 9-12)
- [ ] SKILL.md parser (frontmatter + body)
- [ ] Skill registry + discovery
- [ ] Description injection (always-in-context)
- [ ] On-demand activation
- [ ] Built-in skills: filesystem, git, web
- [ ] `teotl skills` CLI

### Phase 3: Memory (Weeks 13-16)
- [ ] SQLite memory store
- [ ] Local embeddings (sentence-transformers)
- [ ] Hybrid retrieval (vector + keyword + recency)
- [ ] Session → memory extraction
- [ ] Context injection with token budget
- [ ] `teotl memory` CLI
- [ ] Compaction integration

### Phase 4: Integrations (Weeks 17-20)
- [ ] Auth management (OAuth2, API keys)
- [ ] Integration registry
- [ ] CLI script executor
- [ ] MCP bridge (meta-tool pattern)
- [ ] Built-in integrations: Gmail, GitHub, Slack
- [ ] `teotl auth` CLI

### Phase 5: Cloud (Weeks 21-26)
- [ ] Cloud client stubs
- [ ] Memory sync API
- [ ] Skill store API
- [ ] Analytics pipeline
- [ ] Web UI adapter
- [ ] Documentation site

### Phase 6: Community (Weeks 27+)
- [ ] Skill contribution guide
- [ ] Extension marketplace
- [ ] Team features
- [ ] Enterprise compliance

---

## 12. Key Technical Decisions

### Why Python over TypeScript
- **Larger ML/AI ecosystem**: sentence-transformers, numpy, pandas all native
- **Broader developer base**: more potential contributors and platform builders
- **Pydantic for validation**: already the standard for AI data validation
- **async/await**: Python's asyncio is mature enough for this
- **pi-mono's TS bet was wrong for platforms**: TS limits the audience

### Why fork pi-mono's ideas but not its code
- pi-mono is TypeScript — no code to port
- Its *philosophy* is excellent: minimal core, extensions, skills, append-only sessions
- Its *gaps* are exactly what we're filling: guardrails, memory, context management
- We carry forward: event system, extension model, SKILL.md format, JSONL sessions
- We diverge: four primitives as core, safe-by-default, open core model

### Why skills over MCP (reiterated for platform builders)
| Dimension | Skills | MCP |
|-----------|--------|-----|
| Baseline context cost (10 integrations) | ~500 tokens | ~30,000+ tokens |
| Loading strategy | On-demand | All-at-once |
| Composability | bash pipes | Context-mediated |
| Inspectability | Readable markdown | Opaque JSON schemas |
| Auth management | Framework-managed env vars | Server-managed (varies) |
| Compaction behavior | Temporary messages, summarized away | Permanent tool schemas |
| Escape hatch | MCP bridge (meta-tool) | N/A |

### Why guardrails are infrastructure, not policy
The common pattern is guardrails-as-prompt-injection: "Don't do dangerous things" in the system prompt. This fails because:
- LLMs can be convinced to ignore system prompts
- Prompt-based guardrails cost tokens every turn
- They're not auditable or testable
- Users can't customize them without prompt engineering

Teotl's guardrails operate at the **tool execution layer** — between the LLM's intent and actual execution. The LLM never sees the guardrail logic. It just gets "blocked: reason" as a tool result.

---

## 13. Naming & Identity

**Teotl** — a place where tools are made. Agents are created here.

- Install from source (PyPI coming soon)
- `teotl init` / `teotl run` / `teotl skills`
- Framework: MIT license

---

## Appendix A: Comparison with pi-mono

| Feature | pi-mono | Teotl |
|---------|---------|-------|
| Language | TypeScript | Python |
| Core philosophy | Minimal, extensible | Minimal, extensible, safe-by-default |
| Guardrails | Extension (optional) | Core primitive |
| Memory | Not built-in | Core primitive (SQLite + embeddings) |
| Skills | Extension format standard | Core primitive (always-in-context descriptions) |
| Integrations | CLI tools + README | Skills + auth management |
| MCP | Deliberately avoided | Avoided but with escape hatch |
| Session | JSONL append-only | JSONL append-only (same) |
| Compaction | Via extensions | Built-in with memory extraction |
| Extensions | First-class | First-class (same model, Pythonified) |
| UI | CLI only | CLI + Web + Headless |
| Distribution | Open source | Open core |
| Container/sandbox | "Run in container" | Guardrails + optional container |

## Appendix B: Quick Start for Platform Builders

```python
"""
Build a customer support agent in 20 lines.
"""
from teotl import Agent, AnthropicProvider, Policy

agent = Agent(
    provider=AnthropicProvider(),
    instructions="""
    You are a support agent for TechCorp. Be helpful and professional.
    You can look up customer records and create support tickets.
    Always verify customer identity before sharing account details.
    """,
    skills=["zendesk", "customer_db"],
    policy=Policy.from_dict({
        "level": "strict",
        "bash": {"block": ["*"]},
        "integrations": {
            "zendesk": {"read": "allow", "create_ticket": "allow", "delete": "block"},
            "customer_db": {"read": "allow", "write": "block"},
        }
    }),
)

# Each customer gets their own memory
async def handle_customer(customer_id: str, message: str):
    agent.memory = LocalMemory(path=f"./memories/{customer_id}.db")
    return await agent.run(message)
```

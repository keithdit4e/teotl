# Forge Architecture Decisions

**Purpose:** Document key technical decisions and trade-offs for the Forge framework

---

## ADR-001: Core Language - Python with Strategic Erlang/BEAM Integration

**Date:** March 18, 2026
**Status:** Accepted
**Decision Makers:** Keith Foster

### Context

Forge is a framework for building safe, reliable AI agents. Different parts of the system have different requirements:

- **Agent logic & LLM integration:** Needs extensive ML/AI libraries, rapid iteration
- **Core runtime & orchestration:** Needs fault tolerance, concurrency, distribution
- **Security boundaries:** Needs process isolation, supervision, crash recovery

Python is excellent for ML/AI but has limitations:
- GIL limits true parallelism
- Less robust fault tolerance
- Weaker process isolation
- No built-in supervision trees

Erlang/BEAM (via Elixir) excels at:
- Fault tolerance ("let it crash" philosophy)
- Process isolation (lightweight processes)
- Hot code reloading
- Distribution
- Supervision trees

### Decision

**Hybrid Architecture:**
1. **Core Agent Framework:** Python (teotl)
   - Agent loop, LLM providers, skills, memory
   - Leverage PyTorch, sentence-transformers, anthropic SDK
   - Rapid development, rich ecosystem

2. **Runtime & Orchestration:** Erlang/Elixir (forge-runtime)
   - Multi-agent orchestration
   - Fault-tolerant execution
   - Process supervision
   - Security boundaries
   - Communication via Protocol Buffers or MessagePack

3. **Integration Layer:** gRPC or Erlang Ports
   - Python agents run as supervised processes
   - BEAM VM manages lifecycle, restarts, isolation
   - Clean separation of concerns

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│              BEAM VM (Erlang/Elixir)                       │
│                  forge-runtime                              │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Supervisor Tree                             │   │
│  │  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │ Agent Pool   │  │ Agent Pool   │  ...          │   │
│  │  │ Supervisor   │  │ Supervisor   │               │   │
│  │  └──────┬───────┘  └──────┬───────┘               │   │
│  │         │                  │                        │   │
│  │    ┌────┴───┐         ┌───┴────┐                  │   │
│  │    │ Agent  │         │ Agent  │  ...             │   │
│  │    │ Worker │         │ Worker │                   │   │
│  │    └────────┘         └────────┘                   │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │     Communication Layer (gRPC/Ports)                │   │
│  └─────────────┬──────────────────────┬────────────────┘   │
└────────────────┼──────────────────────┼────────────────────┘
                 │                      │
                 ▼                      ▼
      ┌──────────────────┐  ┌──────────────────┐
      │  Python Agent    │  │  Python Agent    │
      │  (teotl)   │  │  (teotl)   │
      │                  │  │                  │
      │  • Agent loop    │  │  • Agent loop    │
      │  • LLM provider  │  │  • LLM provider  │
      │  • Skills        │  │  • Skills        │
      │  • Memory        │  │  • Memory        │
      │  • Guardrails    │  │  • Guardrails    │
      └──────────────────┘  └──────────────────┘
```

### Rationale

**Why Hybrid vs Pure Python:**
- Python agents are easier to develop and iterate
- BEAM provides fault tolerance Python can't match
- Process isolation is critical for multi-tenant/multi-agent
- Best of both worlds

**Why Hybrid vs Pure Erlang:**
- Erlang ML/AI ecosystem is limited
- Python has anthropic, openai, sentence-transformers, etc.
- Most AI developers know Python, not Erlang
- Framework adoption requires familiar language

### Consequences

#### Positive
- ✅ Python agents leverage rich ML ecosystem
- ✅ BEAM runtime provides fault tolerance
- ✅ Process isolation for security
- ✅ Hot code reloading for updates
- ✅ Horizontal scaling built-in
- ✅ Each agent crashes independently (doesn't affect others)

#### Negative
- ⚠️ Additional complexity (two languages)
- ⚠️ Communication overhead (serialization)
- ⚠️ Two build systems to maintain
- ⚠️ Requires Erlang/Elixir knowledge for runtime

#### Neutral
- 🔄 Clear separation of concerns
- 🔄 Gradual adoption path (Python-only initially)
- 🔄 Runtime can be swapped (Kubernetes, systemd, etc.)

### Implementation Phases

#### Phase 1: Python-Only MVP (Current)
- Build core framework in Python
- Single-process execution
- File-based process isolation
- Target: Personal assistant proof-of-concept

#### Phase 2: BEAM Runtime (Post-MVP)
- Build Elixir runtime
- gRPC integration layer
- Supervisor tree for agents
- Target: Multi-agent orchestration

#### Phase 3: Production Runtime (Future)
- Distributed agents across nodes
- Hot code reloading
- Dynamic supervision
- Target: Production multi-tenant deployment

### When to Use Each

**Python Agent Framework (teotl):**
- Single agent development
- Rapid prototyping
- Local/personal use
- Rich ML/AI requirements

**BEAM Runtime (forge-runtime):**
- Multi-agent orchestration
- Production deployment
- Multi-tenant systems
- Fault-tolerance requirements
- Agent-to-agent communication

### Alternative Runtimes

The Python agent framework can run under:
1. **Native Python** (Phase 1) - Simple, single-process
2. **BEAM/OTP** (Phase 2) - Fault-tolerant, multi-agent
3. **Kubernetes** (Phase 3) - Container orchestration
4. **Systemd** - Linux service management
5. **Docker Compose** - Local multi-agent testing

Each runtime provides different trade-offs.

---

## ADR-002: Security Model - Process Isolation

**Date:** March 18, 2026
**Status:** Accepted

### Context

Agents need strong security boundaries, especially when:
- Running multiple agents in same system
- Agents from different developers
- Multi-tenant deployments
- Untrusted code execution

### Decision

**Layered Security Model:**

1. **Python Layer (teotl):**
   - Tool-layer guardrails (policy enforcement)
   - Input validation
   - Credential encryption
   - Rate limiting

2. **Process Layer (OS/BEAM):**
   - Each agent in separate process
   - OS-level resource limits (CPU, memory)
   - File system isolation (chroot/namespaces)
   - Network policies

3. **Runtime Layer (forge-runtime):**
   - Supervision trees (automatic restart)
   - Circuit breakers (prevent cascade failures)
   - Audit logging (all cross-process calls)

### Rationale

**Why BEAM for Security:**
- Erlang processes are isolated by design
- Crash in one process doesn't affect others
- Built-in resource monitoring
- Proven in telecom systems (99.999% uptime)

**Why Not Containers Only:**
- Heavier weight than BEAM processes
- Slower startup time
- More complex orchestration
- Can still use containers at outer layer

### Implementation

```elixir
# forge-runtime/lib/forge/agent_supervisor.ex
defmodule Forge.AgentSupervisor do
  use DynamicSupervisor

  def start_agent(agent_config) do
    # Start Python agent as supervised process
    child_spec = %{
      id: agent_config.id,
      start: {Forge.AgentWorker, :start_link, [agent_config]},
      restart: :temporary,  # Don't restart on normal exit
      type: :worker,
      shutdown: 5000
    }

    DynamicSupervisor.start_child(__MODULE__, child_spec)
  end
end

defmodule Forge.AgentWorker do
  use GenServer

  def start_link(config) do
    GenServer.start_link(__MODULE__, config, name: via_tuple(config.id))
  end

  def init(config) do
    # Start Python agent process
    port = Port.open(
      {:spawn, "python3 -m forge.run #{config.id}"},
      [:binary, :exit_status, {:cd, config.work_dir}]
    )

    {:ok, %{port: port, config: config}}
  end

  # Handle messages from Python agent
  def handle_info({port, {:data, data}}, state) do
    # Process agent output
    {:noreply, state}
  end

  # Handle agent crash
  def handle_info({port, {:exit_status, status}}, state) do
    Logger.error("Agent #{state.config.id} exited with status #{status}")
    {:stop, :normal, state}
  end
end
```

---

## ADR-003: Communication Protocol

**Date:** March 18, 2026
**Status:** Accepted

### Decision

**Protocol:** gRPC with Protocol Buffers

### Rationale

**Why gRPC:**
- Language-agnostic (Python ↔ Elixir)
- Type-safe with protobuf schemas
- Bidirectional streaming
- Well-supported libraries

**Why Not JSON:**
- Slower serialization
- No type safety
- Larger payload size

**Why Not MessagePack:**
- Less tooling
- No schema validation
- Harder debugging

### Implementation

```protobuf
// forge-runtime/proto/agent.proto
syntax = "proto3";

package forge;

service AgentService {
  rpc ExecuteTurn(TurnRequest) returns (TurnResponse);
  rpc StreamResponse(TurnRequest) returns (stream TurnChunk);
  rpc GetStatus(StatusRequest) returns (StatusResponse);
}

message TurnRequest {
  string agent_id = 1;
  string message = 2;
  map<string, string> context = 3;
}

message TurnResponse {
  string response_text = 1;
  repeated ToolCall tool_calls = 2;
  map<string, double> usage = 3;
}

message ToolCall {
  string id = 1;
  string name = 2;
  map<string, string> args = 3;
}
```

---

## ADR-004: Deployment Model

**Date:** March 18, 2026
**Status:** Proposed

### Options

1. **Python-only (MVP):**
   - Simple pip install
   - Run locally
   - No runtime dependencies

2. **BEAM Runtime (Production):**
   - Elixir release
   - Supervises Python agents
   - Fault tolerance

3. **Kubernetes (Scale):**
   - Container per agent
   - K8s orchestration
   - Cloud-native

### Decision

**Progressive path:**
- MVP: Python-only
- v1.0: Add BEAM runtime option
- v2.0: Add Kubernetes option

Users choose based on needs.

---

## Future Considerations

### ADR-005: Multi-Language Agents (Future)

Could support agents written in:
- Python (primary)
- JavaScript/TypeScript (web integration)
- Rust (performance-critical)
- Go (network services)

All supervised by BEAM runtime, communicate via gRPC.

### ADR-006: Distributed Agents (Future)

BEAM's distribution primitives enable:
- Agents on different machines
- Geographic distribution
- Load balancing
- Failover

---

## References

- **BEAM/OTP:** https://www.erlang.org/doc/design_principles/des_princ.html
- **Elixir:** https://elixir-lang.org/
- **gRPC:** https://grpc.io/
- **Process Supervision:** https://erlang.org/doc/design_principles/sup_princ.html

---

**Conclusion:**

Forge uses Python for agent logic (ML/AI ecosystem) and Erlang/BEAM for runtime (fault tolerance). This hybrid approach provides the best of both worlds: rapid development with Python, production robustness with BEAM.

The MVP focuses on Python-only to prove the framework concept. BEAM runtime is added post-MVP for production deployments requiring fault tolerance and multi-agent orchestration.

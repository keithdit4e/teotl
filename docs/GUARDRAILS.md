# Guardrails System

**Declarative, zero-context-cost safety for AI agents.**

Teotl's guardrails system provides tool-layer protection that operates **before** any dangerous action is executed. Unlike prompt-based safety ("please don't do bad things"), guardrails can't be talked out of their rules by the model and consume **zero context tokens**.

---

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Quick Start](#quick-start)
4. [Policy Configuration](#policy-configuration)
5. [Built-in Policies](#built-in-policies)
6. [Custom Policies](#custom-policies)
7. [Risk Levels](#risk-levels)
8. [Trust Building](#trust-building)
9. [Security Properties](#security-properties)
10. [Best Practices](#best-practices)
11. [API Reference](#api-reference)

---

## Overview

### What Are Guardrails?

Guardrails intercept **every tool call** before execution and make a decision:

- **ALLOW** - Execute immediately, no user interaction
- **CONFIRM** - Ask user for approval before executing
- **BLOCK** - Refuse to execute, even with approval

### Key Features

✅ **Zero Context Cost** - Guardrails operate at the tool execution layer, not in the LLM prompt
✅ **Enforced in code** - Tool calls go through the guardrail engine before the handler runs
✅ **Declarative** - Define policies in JSON/YAML, not code
✅ **Progressive Trust** - Auto-approve repeated safe actions
✅ **Audit Trail** - All decisions logged to `~/.teotl/audit.jsonl`
✅ **Event-Driven** - Integrates cleanly via event bus

### Architecture

```
LLM Response → Tool Call → Guardrails → Policy Check → Decision
                                             ↓
                               [ALLOW / CONFIRM / BLOCK]
                                             ↓
                               Tool Handler (if allowed)
```

Guardrails operate **between** the LLM and tool execution, ensuring no dangerous action happens without explicit approval.

---

## How It Works

### 1. Classification

Every tool call is classified into an `Action`:

```python
Action(
    type=ActionType.WRITE,       # READ, WRITE, EXECUTE, NETWORK, DESTRUCTIVE
    target="/path/to/file.txt",  # What's being acted upon
    risk=RiskLevel.MEDIUM,       # LOW, MEDIUM, HIGH, CRITICAL
    details={...}                # Additional metadata
)
```

### 2. Policy Evaluation

The action is evaluated against your policy:

```python
decision = policy.decide(action)
# Returns: Decision.ALLOW, Decision.CONFIRM, or Decision.BLOCK
```

### 3. Trust Check

If the decision is `CONFIRM`, check if trust has been built:

```python
if trust.is_trusted(action):
    decision = Decision.ALLOW  # Auto-approve
```

### 4. User Confirmation (if needed)

If still `CONFIRM`, ask the user:

```python
approved = await ui.confirm("🛡️ Run command: ls -la?")
if approved:
    trust.record_approval(action)  # Build trust
    return ALLOW
else:
    return BLOCK
```

> **Programmatic use:** if you call `agent.run(message)` without a `ui`, Teotl uses a
> headless UI that **auto-approves** confirmations. `BLOCK` decisions still apply. Pass a UI
> adapter (e.g. `teotl.ui.cli.CliUI`) to `agent.run(message, ui=...)` for human-in-the-loop
> confirmations. (The guardrail engine itself blocks `CONFIRM` actions when no UI at all is
> supplied.)

### 5. Execution or Blocking

If `ALLOW`: Tool handler executes
If `BLOCK`: Return error to LLM

---

## Quick Start

### Basic Usage

```python
from teotl import Agent
from teotl.core.provider import AnthropicProvider

# Use built-in "standard" policy (safe by default)
agent = Agent(
    provider=AnthropicProvider(),
    instructions="You are a helpful assistant.",
    policy="standard",  # or "minimal", "strict"
)

response = await agent.run("List files in current directory")
```

> Only `"minimal"`, `"standard"` (default), and `"strict"` are valid preset names. An
> unknown name logs a warning and **disables guardrails**, so double-check spelling.

### Load Custom Policy

```python
from pathlib import Path

# From JSON file
agent = Agent(
    provider=provider,
    policy=Path("./policies/production.json")
)

# From YAML file (requires PyYAML)
agent = Agent(
    provider=provider,
    policy=Path("./policies/custom.yaml")
)

# From dict
from teotl.primitives.guardrails import Policy

policy = Policy.from_dict({
    "level": "strict",
    "filesystem": {"allow": ["./workspace/**"], "deny": ["~/.ssh/**"]},
    "bash": {"block": ["rm -rf /"], "allow": ["ls", "cat"]},
})

agent = Agent(provider=provider, policy=policy)
```

---

## Policy Configuration

A policy is a JSON or YAML file (or dict) that defines rules for different types of actions.
The built-in presets are defined in `teotl/primitives/guardrails/presets.py`; the `policies/`
directory has JSON versions (`minimal.json`, `standard.json`, `strict.json`) you can copy as a
starting point.

### Basic Structure

```yaml
# policy.yaml
level: standard         # minimal | standard | strict — sets the default decisions by risk

# Filesystem rules (for read/write actions)
filesystem:
  allow:
    - "~/Documents/**"
    - "/tmp/**"
  deny:
    - "~/.ssh/**"
    - "/etc/**"
  confirm_write_outside_scope: true

# Bash command rules (for execute actions)
bash:
  block: ["rm -rf /", "curl * | bash"]   # substring / prefix patterns
  confirm: ["rm", "git push", "sudo"]    # primary command names
  allow: ["ls", "cat", "git status"]     # primary command names

# Network access rules
network:
  allow_outbound: false
  allowed_hosts:
    - "api.github.com"
  confirm_new_hosts: true

# Trust settings
trust:
  auto_approve_after: 3
```

### How a decision is made

`Policy.decide(action)` checks, in order:

1. **Filesystem rules** (read/write actions with a target path)
2. **Bash rules** (execute actions)
3. **Network rules** (network actions)
4. **Integration rules** (if the action names an integration)
5. **Default by risk level**, based on `level`

The first rule that produces a decision wins.

### Configuration Options

#### `level`

Selects the default decision for actions no rule matched:

| Risk | `minimal` | `standard` | `strict` |
|------|-----------|------------|----------|
| `low` | allow | allow | confirm |
| `medium` | allow | confirm | confirm |
| `high` | confirm | confirm | block |
| `critical` | confirm | block | block |

Any other `level` value uses the `standard` defaults.

#### `filesystem`

```yaml
filesystem:
  # Allowed paths (glob patterns supported)
  allow:
    - "~/code/**"
    - "/tmp/**"

  # Denied paths (checked first, take priority over allow)
  deny:
    - "~/.ssh/**"
    - "~/.gnupg/**"
    - "/etc/**"

  # Confirm writes even inside allowed paths
  confirm_write_outside_scope: true
```

- Paths are matched with `fnmatch` after `~` expansion.
- `deny` match → **block**.
- `allow` match → **allow** (or **confirm** for writes when `confirm_write_outside_scope` is true).
- No match → writes need **confirmation**; reads fall through to the default for their risk level.

#### `bash`

```yaml
bash:
  # Blocked patterns: a pattern ending in "*" blocks commands starting with the prefix;
  # otherwise the command is blocked if it contains the pattern
  block:
    - "rm -rf /"
    - ":(){ :|:& };:"
    - "sudo"

  # Primary commands that require confirmation
  confirm:
    - "rm"
    - "git push"

  # Primary commands allowed without confirmation
  allow:
    - "ls"
    - "cat"
    - "grep"
```

Bash rules apply to commands classified as *execute* actions. Commands the bash analyzer
classifies as reads (`ls`, `cat`, `grep`, ...), writes (`cp`, `mv`, redirects, ...),
network access (`curl`, `wget`, `ssh`, ...), or destructive (`rm`, `dd`, ...) are evaluated
by the filesystem / network rules and the risk-level defaults instead.

#### `network`

```yaml
network:
  allow_outbound: false      # true = no network restrictions from this section
  allowed_hosts:             # exact host names
    - "api.anthropic.com"
    - "api.github.com"
  confirm_new_hosts: true    # confirm unknown hosts (false = block them)
```

#### `trust`

```yaml
trust:
  # Number of approvals before auto-approving the same pattern
  auto_approve_after: 3
```

`session_scoped` and `persist_patterns` are accepted, but trust is currently always held
in memory for the lifetime of the `Agent` (see [Trust Building](#trust-building)).

#### `integrations`

Rules for specific integrations, mapping an operation name to a decision:

```yaml
integrations:
  github:
    read: allow
    push: confirm
    delete: block
```

#### `limits`

The presets include a `limits` section (`max_files_per_turn`, `max_bash_commands_per_turn`,
`cost_limit_session`, `cost_limit_daily`). These values are loaded but **not currently
enforced** by the guardrail engine; use `RateLimiter` / `RateLimitedProvider` for cost and
rate limits (see [Best Practices](#7-combine-with-other-security-measures)).

---

## Built-in Policies

Teotl includes three preset policies (`teotl/primitives/guardrails/presets.py`):

### `standard` (Default)

Balanced policy suitable for most use cases.

```python
agent = Agent(provider=provider, policy="standard")
```

**Characteristics:**
- Low-risk actions: allow; medium/high: confirm; critical: block
- Filesystem: `~/projects/**`, `~/Documents/**`, `/tmp/**` allowed (writes confirmed);
  `~/.ssh`, `~/.aws`, `~/.teotl/auth`, `~/.gnupg` denied
- Bash: blocks `rm -rf /`, fork bombs, and piping `curl`/`wget` into a shell; confirms
  `rm`, `git push`, `git reset --hard`, `sudo`, `docker`, `pip install`, `chmod`, `kill`, ...;
  allows common read-only commands, `git status/log/diff`, `pytest`, ...
- Network: outbound restricted to `api.github.com`, `pypi.org`, `registry.npmjs.org`; other hosts confirmed
- Trust threshold: 3 approvals

**Use for:** General-purpose assistants, development work

### `strict`

High-security policy that requires confirmation for most actions.

```python
agent = Agent(provider=provider, policy="strict")
```

**Characteristics:**
- Low/medium-risk actions: confirm; high/critical: block
- Filesystem: no allowed paths (all writes confirmed); sensitive directories denied
- Bash: additionally blocks `sudo` and `docker`
- Network: no allowed hosts; every host confirmed
- Trust threshold: 5 approvals

**Use for:** Production environments, sensitive data, untrusted agents

### `minimal`

Low-friction policy for trusted environments.

```python
agent = Agent(provider=provider, policy="minimal")
```

**Characteristics:**
- Low/medium-risk actions: allow; high/critical: confirm
- Filesystem: `~/.ssh` and `~/.aws` denied; writes elsewhere confirmed
- Bash: blocks `rm -rf /` and fork bombs
- Network: outbound allowed
- Trust threshold: 1 approval

**Use for:** Development, personal use, trusted agents

---

## Custom Policies

### Creating a Policy

1. **Copy a preset:**
   ```bash
   cp policies/standard.json my-policy.json
   ```

2. **Edit the policy** (see [Policy Configuration](#policy-configuration)).

3. **Load in agent:**
   ```python
   agent = Agent(
       provider=provider,
       policy=Path("./my-policy.json")
   )
   ```

### Example: Coding Assistant

```yaml
level: standard

filesystem:
  allow:
    - "~/code/**"
    - "/tmp/**"
  deny:
    - "~/.ssh/**"
    - "~/.aws/**"
  confirm_write_outside_scope: false   # writes inside ~/code are allowed

bash:
  block: ["rm -rf /", "curl * | bash", "wget * | bash", "sudo"]
  confirm: ["rm", "git push", "pip install", "npm install"]
  allow: ["ls", "cat", "grep", "git status", "git diff", "git log", "pytest"]

network:
  allow_outbound: false
  allowed_hosts:
    - "api.anthropic.com"
    - "pypi.org"
  confirm_new_hosts: true

trust:
  auto_approve_after: 3
```

### Example: CI/CD Environment

In CI there is nobody to confirm, so design the policy to allow or block explicitly. Note that
with no `ui`, `agent.run()` auto-approves `CONFIRM` decisions — use `level: strict` and
explicit `block` rules for anything that must never happen.

```yaml
level: strict

filesystem:
  allow:
    - "/workspace/**"
    - "/tmp/**"
  deny:
    - "/etc/**"
    - "~/.ssh/**"
  confirm_write_outside_scope: false

bash:
  block: ["rm -rf", "sudo", "curl * | bash", "wget * | bash", "git push"]
  allow: ["ls", "cat", "pytest"]

network:
  allow_outbound: false
  allowed_hosts:
    - "api.anthropic.com"
  confirm_new_hosts: false   # block unknown hosts
```

---

## Risk Levels

The bash analyzer (`teotl/primitives/guardrails/bash_analyzer.py`) assigns each command one of
four risk levels:

### `LOW` - Read-only, no side effects

**Examples:** `ls`, `cat`, `grep`, `find`, reading files

### `MEDIUM` - Writes, network access, package installs

**Examples:** `echo > file.txt`, `cp`, `mv`, `curl https://...`, `pip install`, long pipelines;
file writes via write tools

### `HIGH` - Destructive, system-level, or sensitive paths

**Examples:** `rm file.txt`, `sudo ...`, `systemctl`, `reboot`; commands touching sensitive
paths such as `~/.ssh`; commands that can't be parsed

### `CRITICAL` - Catastrophic, irreversible

**Examples:** `rm -rf /`, `dd ...`, fork bombs, downloading and piping into a shell
(`curl ... | bash`)

The default decision for each level depends on the policy `level` (see the table above).

---

## Trust Building

Guardrails implement **progressive trust** - repeated approvals of the same action pattern
eventually auto-approve.

### How It Works

With `auto_approve_after: 3`:

1. **First time:** User confirms action
2. **Second time:** User confirms again
3. **Third time:** User confirms again
4. **Fourth+ time:** Auto-approved (no confirmation needed)

Trust only upgrades `CONFIRM` to `ALLOW`; it never overrides a `BLOCK`.

### Patterns

Approvals are counted per pattern:

- Bash: per primary command — `bash:git push`
- Reads/writes: per parent directory — `write:/home/me/project`
- Network: per host — `network:api.github.com`

### Example

```python
from teotl.ui.cli import CliUI

agent = Agent(provider=provider, policy="standard")
ui = CliUI()

await agent.run("Create notes/a.md", ui=ui)   # → Asks for confirmation
await agent.run("Create notes/b.md", ui=ui)   # → Asks for confirmation
await agent.run("Create notes/c.md", ui=ui)   # → Asks for confirmation
await agent.run("Create notes/d.md", ui=ui)   # → Auto-approved (same directory)
```

### Scope

Trust is held in memory by the agent's `GuardrailEngine` and resets when you create a new
`Agent`. Persistent trust across sessions is not implemented yet.

---

## Security Properties

> **Note:** These are design goals, not certified guarantees. Guardrails provide defense-in-depth but should be combined with other security measures for production use.

### What Guardrails Are Designed to Protect Against

✅ **Accidental destructive commands** - `rm -rf /` is blocked
✅ **Unauthorized file access** - Denied paths like `~/.ssh` are blocked
✅ **Network exfiltration** - Restricted outbound hosts (standard/strict)
✅ **Risky system changes** - `sudo`, package installs, etc. require confirmation or are blocked

### What Guardrails DON'T Protect Against

❌ **Prompt injection in user confirmations** - User might be tricked into approving
❌ **Auto-approved confirmations in headless mode** - Without a `ui`, confirmations are auto-approved
❌ **Malicious extensions** - Extensions can bypass guardrails
❌ **Process-level exploits** - Guardrails don't isolate processes
❌ **Runaway loops / costs** - Use `RateLimiter` and `max_turns`
❌ **Novel attack vectors** - Security is defense-in-depth, not perfect

### Defense-in-Depth

Guardrails are **one layer** of security:

1. **Prompt Injection Defense** - `Agent(enable_injection_defense=True)` (default)
2. **Guardrails** - Tool-layer protection (this document)
3. **Rate Limiting** - `RateLimiter` / `RateLimitedProvider` prevent cost explosions
4. **Encryption** - Credentials (`CredentialStore`) encrypted at rest
5. **Security policy & sandbox** - `SecurityPolicy`, `SecurityEnforcer`, `SandboxManager`
   (see [SECURITY_GUIDE.md](SECURITY_GUIDE.md))

**Use all layers for production deployments.**

---

## Best Practices

### 1. Start with `strict` for new agents

```python
# Start strict, relax as you build trust
agent = Agent(provider=provider, policy="strict")
```

After validating the agent behaves correctly, switch to `standard` or custom.

### 2. Use custom policies for specific use cases

Don't use `minimal` in production. Create a custom policy tailored to your agent's needs:

```yaml
# my-agent-policy.yaml
level: strict
filesystem:
  allow:
    - "/srv/agent-workspace/**"   # Only what agent needs
  deny:
    - "~/.ssh/**"
    - "/etc/**"
```

### 3. Review audit logs

```bash
# View recent guardrail decisions
tail -f ~/.teotl/audit.jsonl
```

Look for:
- Blocked actions (potential attacks or bugs)
- Frequently confirmed actions (consider auto-allowing)
- Unexpected tool calls

### 4. Test policies before deployment

```python
from teotl.core.types import Decision, ToolCall
from teotl.primitives.guardrails import Policy
from teotl.primitives.guardrails.classifier import classify

# Load policy
policy = Policy.from_file("my-policy.yaml")

# Test specific action
action = classify(ToolCall(
    id="test",
    name="bash",
    args={"command": "rm -rf /"}
))

decision = policy.decide(action)
assert decision == Decision.BLOCK
```

### 5. Use environment-specific policies

```python
import os
from pathlib import Path

env = os.getenv("ENV", "development")
policy_path = Path(f"./policies/{env}.yaml")

agent = Agent(provider=provider, policy=policy_path)
```

### 6. Document policy rationale

Unknown keys are ignored, so you can keep notes in the policy file:

```yaml
level: strict
notes:
  - "Network access restricted to APIs only (prevent exfiltration)"
  - "Filesystem limited to /app/data (prevent system modification)"
```

### 7. Combine with other security measures

```python
from teotl.core.rate_limited_provider import RateLimitedProvider
from teotl.primitives.guardrails.rate_limiter import RateLimiter

# Rate limiting + guardrails
limiter = RateLimiter(max_requests_per_minute=60, max_cost_per_hour=5.0)
provider = RateLimitedProvider(base_provider, limiter)

agent = Agent(
    provider=provider,
    policy="strict",
    enable_injection_defense=True  # Prompt injection defense
)
```

---

## API Reference

### `GuardrailEngine`

```python
from teotl.primitives.guardrails import GuardrailEngine

engine = GuardrailEngine(policy="standard")   # preset name, Policy, or Path

# The agent registers engine.evaluate as a "tool_call" event handler.
# It receives an EventResult whose data is the ToolCall:
event_result = await engine.evaluate(event, ui=ui)

if event_result.blocked:
    print(f"Blocked: {event_result.reason}")
```

The engine used by an agent is available as `agent.guardrails`.

### `Policy`

```python
from teotl.primitives.guardrails import Policy

# Load from preset
policy = Policy.from_preset("standard")

# Load from file
policy = Policy.from_file("policy.yaml")

# Load from dict
policy = Policy.from_dict({"level": "strict"})

# Evaluate action
decision = policy.decide(action)  # Decision.ALLOW / CONFIRM / BLOCK

# Get block reason
reason = policy.block_reason(action)
```

### `TrustTracker`

```python
from teotl.primitives.guardrails.trust import TrustTracker

trust = TrustTracker(auto_approve_after=3)

# Check if trusted
if trust.is_trusted(action):
    ...  # Auto-approve

# Record approval
trust.record_approval(action)

# Reset trust
trust.reset()
```

### `classify()`

```python
from teotl.core.types import ToolCall
from teotl.primitives.guardrails.classifier import classify

tool_call = ToolCall(
    id="1",
    name="bash",
    args={"command": "ls -la"}
)

action = classify(tool_call)
# Returns Action(type=ActionType.READ, target=..., risk=RiskLevel.LOW, details={...})
```

---

## Troubleshooting

### Guardrails not working

**Check initialization:**
```python
assert agent.guardrails is not None
```

If `None`, guardrails failed to initialize — look for a `Guardrails DISABLED` warning in the
logs (e.g. an unknown preset name or a policy file that failed to load).

### Actions being blocked unexpectedly

**Check audit log:**
```bash
tail ~/.teotl/audit.jsonl
```

Look for `"decision": "blocked"` (or `"blocked_no_ui"`) entries and check the `reason` field.

**Verify policy:**
```python
from teotl.primitives.guardrails import Policy
policy = Policy.from_file("my-policy.yaml")
print(policy.level, policy.filesystem, policy.bash, policy.network)
```

### Trust not building

**Check configuration:**
```yaml
trust:
  auto_approve_after: 3  # Should be > 0
```

**Check if actions are similar enough:** approvals are counted per pattern (bash primary
command, parent directory, or network host) — see [Trust Building](#trust-building).

### Policy file not loading

**Check file exists:**
```python
from pathlib import Path
assert Path("policy.yaml").exists()
```

**Check YAML syntax:**
```bash
python -c "import yaml; yaml.safe_load(open('policy.yaml'))"
```

**Check JSON syntax:**
```bash
python -c "import json; json.load(open('policy.json'))"
```

---

## Examples

See [`policies/`](../policies/) for JSON versions of the presets (`minimal.json`,
`standard.json`, `strict.json`) and `teotl/primitives/guardrails/presets.py` for the
authoritative definitions.

---

## Further Reading

- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - Security policies, sandboxing, and audit logging
- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall framework architecture

---

**Questions or feedback?** Open an issue on [GitHub](https://github.com/keithdit4e/teotl/issues).

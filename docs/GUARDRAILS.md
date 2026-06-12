# Guardrails System

**Declarative, zero-context-cost safety for AI agents.**

Teotl's guardrails system provides tool-layer protection that operates **before** any dangerous action is executed. Unlike prompt-based safety ("please don't do bad things"), guardrails are **un-bypassable** and consume **zero context tokens**.

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
✅ **Un-bypassable** - Tool handlers never execute without passing guardrails first
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
    risk=RiskLevel.MEDIUM,       # SAFE, MEDIUM, HIGH, CRITICAL
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

### 5. Execution or Blocking

If `ALLOW`: Tool handler executes
If `BLOCK`: Return error to LLM

---

## Quick Start

### Basic Usage

```python
from teotl import Agent
from teotl.providers import AnthropicProvider

# Use built-in "standard" policy (safe by default)
agent = Agent(
    provider=AnthropicProvider(),
    instructions="You are a helpful assistant.",
    policy="standard"  # or "strict", "permissive"
)

response = await agent.run("List files in current directory")
```

### Load Custom Policy

```python
from pathlib import Path

# From JSON file
agent = Agent(
    provider=provider,
    policy=Path("./policies/production.json")
)

# From YAML file
agent = Agent(
    provider=provider,
    policy=Path("./policies/custom.yaml")
)

# From dict
from teotl.primitives.guardrails.policy import Policy

policy = Policy.from_dict({
    "level": "custom",
    "default_risk": {
        "safe": "allow",
        "medium": "confirm",
        "high": "block",
        "critical": "block"
    }
})

agent = Agent(provider=provider, policy=policy)
```

---

## Policy Configuration

A policy is a JSON or YAML file that defines rules for different types of actions.

### Basic Structure

```yaml
# policy.yaml
level: custom           # Policy name
description: "..."      # Human-readable description

# Default decisions by risk level
default_risk:
  safe: allow
  medium: confirm
  high: confirm
  critical: block

# Filesystem rules
filesystem:
  allow:
    - "~/Documents/**"
    - "/tmp/**"
  deny:
    - "~/.ssh/**"
    - "/etc/**"

# Bash command rules
bash:
  allow: [read]
  confirm: [write]
  block: [destructive, network, install]

# Network access rules
network:
  allow_by_default: false
  allow_hosts:
    - "api.anthropic.com"
  deny_hosts:
    - "localhost:22"

# Trust settings
trust:
  auto_approve_after: 3
  session_scoped: true
```

### Configuration Options

#### `default_risk`

Default decisions for each risk level:

```yaml
default_risk:
  safe: allow       # Read-only operations
  medium: confirm   # Write operations
  high: confirm     # Potentially dangerous
  critical: block   # Never allow
```

Options: `allow`, `confirm`, `block`

#### `filesystem`

Control file access:

```yaml
filesystem:
  # Allowed paths (glob patterns supported)
  allow:
    - "~/code/**"
    - "./project/**"
    - "/tmp/**"

  # Denied paths (takes priority over allow)
  deny:
    - "~/.ssh/**"
    - "~/.gnupg/**"
    - "/etc/**"
    - "node_modules/**"
```

**Pattern Syntax:**
- `**` - Match any number of directories
- `*` - Match any characters in a single path component
- `~` - Expands to user home directory

**Priority:** `deny` rules take precedence over `allow` rules

#### `bash`

Control bash command execution:

```yaml
bash:
  # Commands allowed without confirmation
  allow:
    - read    # ls, cat, grep, find, etc.

  # Commands requiring confirmation
  confirm:
    - write   # echo >, cp, mv, etc.

  # Commands that are blocked
  block:
    - destructive          # rm -rf, dd, etc.
    - network             # curl, wget, ssh, etc.
    - install             # apt, brew, pip, etc.
    - system_modification # systemctl, etc.
```

**Categories:**
- `read` - Read-only commands (ls, cat, grep, find, head, tail)
- `write` - File modification (echo >, cp, mv, touch, mkdir)
- `destructive` - Dangerous deletions (rm -rf, dd, shred, mkfs)
- `network` - Network access (curl, wget, ssh, nc, telnet)
- `install` - Package installation (apt, brew, pip, npm install)
- `system_modification` - System changes (systemctl, service, reboot)

#### `network`

Control network access:

```yaml
network:
  # Allow all network by default
  allow_by_default: false

  # Specific hosts to allow (supports wildcards)
  allow_hosts:
    - "api.anthropic.com"
    - "api.openai.com"
    - "*.mycompany.com"

  # Hosts to block (overrides allow)
  deny_hosts:
    - "localhost:22"
    - "127.0.0.1:*"
```

#### `trust`

Configure progressive trust building:

```yaml
trust:
  # Number of approvals before auto-approving
  auto_approve_after: 3

  # Reset trust at end of session
  session_scoped: true

  # Remember specific action patterns
  persist_patterns: false
```

#### `integrations`

Rules for specific integrations:

```yaml
integrations:
  github:
    allow: ["read_repos", "read_issues"]
    confirm: ["create_issue", "create_pr"]
    block: ["delete_repo", "push_force"]

  gmail:
    allow: ["read_email"]
    confirm: ["send_email"]
    block: ["delete_email"]
```

---

## Built-in Policies

Teotl includes three preset policies:

### `standard` (Default)

Balanced policy suitable for most use cases.

```python
agent = Agent(provider=provider, policy="standard")
```

**Characteristics:**
- Safe actions: Allow automatically
- Medium actions: Require confirmation
- High/Critical actions: Block or confirm with strong warnings
- Trust threshold: 3 approvals
- Filesystem: User directories allowed, system directories blocked
- Network: Allow by default

**Use for:** General-purpose assistants, development work

### `strict`

High-security policy that requires confirmation for most actions.

```python
agent = Agent(provider=provider, policy="strict")
```

**Characteristics:**
- Safe actions: Require confirmation
- Medium actions: Require confirmation
- High actions: Block
- Critical actions: Block
- Trust threshold: 5 approvals
- Filesystem: Minimal access
- Network: Allowlist only

**Use for:** Production environments, sensitive data, untrusted agents

### `permissive`

Low-friction policy for trusted environments.

```python
agent = Agent(provider=provider, policy="permissive")
```

**Characteristics:**
- Safe actions: Allow
- Medium actions: Allow
- High actions: Confirm
- Critical actions: Block
- Trust threshold: 2 approvals
- Filesystem: Broad access
- Network: Allow all

**Use for:** Development, personal use, trusted agents

---

## Custom Policies

### Creating a Policy

1. **Copy a template:**
   ```bash
   cp examples/policies/custom-example.yaml my-policy.yaml
   ```

2. **Edit the policy:**
   ```yaml
   level: my-custom-policy
   description: "Policy for X use case"

   default_risk:
     safe: allow
     medium: confirm
     high: block
     critical: block

   # ... customize rules
   ```

3. **Load in agent:**
   ```python
   agent = Agent(
       provider=provider,
       policy=Path("./my-policy.yaml")
   )
   ```

### Example: Coding Assistant

```yaml
level: coding-assistant
description: "Policy for a coding assistant that can modify code files"

default_risk:
  safe: allow
  medium: confirm
  high: confirm
  critical: block

filesystem:
  allow:
    - "~/code/**"
    - "./src/**"
    - "./tests/**"
  deny:
    - "node_modules/**"
    - ".git/**"
    - "~/.ssh/**"

bash:
  allow: [read]
  confirm: [write]
  block: [destructive, network, install, system_modification]

network:
  allow_by_default: false
  allow_hosts:
    - "api.anthropic.com"
    - "api.openai.com"

trust:
  auto_approve_after: 3
  session_scoped: true
```

### Example: CI/CD Environment

```yaml
level: ci-cd
description: "Non-interactive policy for CI/CD (no confirmations)"

default_risk:
  safe: allow
  medium: block    # No UI for confirmations
  high: block
  critical: block

filesystem:
  allow:
    - "./**"
    - "/tmp/**"
    - "/workspace/**"
  deny:
    - "../**"      # No escaping workspace
    - "/etc/**"
    - "~/.ssh/**"

bash:
  allow: [read]
  confirm: []      # No confirmations possible
  block: [write, destructive, network, install]

network:
  allow_by_default: false
  allow_hosts:
    - "api.anthropic.com"

trust:
  auto_approve_after: 999  # Effectively disabled
  session_scoped: true
```

---

## Risk Levels

Actions are classified into four risk levels:

### `SAFE` - Read-only, no side effects

**Examples:**
- `ls`, `cat`, `grep`, `find`
- Reading files
- Checking status

**Default:** Allow without confirmation

### `MEDIUM` - Write operations, reversible

**Examples:**
- `echo > file.txt`
- `mkdir`, `touch`
- Copying files
- Creating directories

**Default:** Require confirmation

### `HIGH` - Potentially dangerous, hard to reverse

**Examples:**
- `rm file.txt` (specific file)
- `mv /important/file /tmp/`
- Modifying system configuration
- Network requests

**Default:** Require confirmation with warnings

### `CRITICAL` - Catastrophic, irreversible

**Examples:**
- `rm -rf /`
- `dd if=/dev/zero of=/dev/sda`
- `DROP DATABASE`
- Force push to main branch

**Default:** Block entirely

---

## Trust Building

Guardrails implement **progressive trust** - repeated approvals of the same action type build trust and eventually auto-approve.

### How It Works

1. **First time:** User confirms action
2. **Second time:** User confirms again
3. **Third time:** User confirms again
4. **Fourth+ time:** Auto-approved (no confirmation needed)

### Configuration

```yaml
trust:
  # Number of approvals before auto-approving
  auto_approve_after: 3

  # Reset trust at end of session
  session_scoped: true

  # Remember specific patterns (e.g., "write to README.md")
  persist_patterns: false
```

### Example

```python
agent = Agent(provider=provider, policy="standard")

# First time writing to a file
await agent.run("Create config.json")  # → Asks for confirmation

# Second time
await agent.run("Update config.json")  # → Asks for confirmation

# Third time
await agent.run("Fix config.json")     # → Asks for confirmation

# Fourth time
await agent.run("Modify config.json")  # → Auto-approved!
```

### Trust Scopes

**Session-scoped** (`session_scoped: true`):
- Trust resets when agent session ends
- Each new Agent instance starts fresh
- Safer for short-lived agents

**Persistent** (`session_scoped: false`):
- Trust persists across sessions
- Stored in `~/.teotl/trust.json`
- Useful for long-running assistants

### Pattern Matching

**Pattern matching** (`persist_patterns: true`):
- Remembers specific action patterns
- "Write to README.md" vs "Write to config.json"
- More granular, but more memory

**Action type matching** (`persist_patterns: false`):
- Remembers action types only
- "Write file" (any file)
- Less granular, but simpler

---

## Security Properties

> **Note:** These are design goals, not certified guarantees. Guardrails provide defense-in-depth but should be combined with other security measures for production use.

### What Guardrails Are Designed to Protect Against

✅ **Accidental destructive commands** - `rm -rf /` is blocked
✅ **Unauthorized file access** - Can't read `~/.ssh/id_rsa`
✅ **Network exfiltration** - Restricted network access
✅ **System modification** - Can't install packages or modify system
✅ **Runaway loops** - Rate limiting prevents infinite tool calls

### What Guardrails DON'T Protect Against

❌ **Prompt injection in user confirmations** - User might be tricked into approving
❌ **Malicious extensions** - Extensions can bypass guardrails
❌ **Process-level exploits** - No process isolation (see [SANDBOXING_PLAN.md](SANDBOXING_PLAN.md))
❌ **Resource exhaustion** - No CPU/memory limits (yet)
❌ **Novel attack vectors** - Security is defense-in-depth, not perfect

### Defense-in-Depth

Guardrails are **one layer** of security:

1. **Prompt Injection Defense** - Detect and mitigate malicious prompts
2. **Guardrails** - Tool-layer protection (this document)
3. **Rate Limiting** - Prevent cost explosions and runaway loops
4. **Encryption** - Credentials and memories encrypted at rest
5. **Sandboxing** - Process isolation (planned, see [SANDBOXING_PLAN.md](SANDBOXING_PLAN.md))

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

Don't use `permissive` in production. Create a custom policy tailored to your agent's needs:

```yaml
# my-agent-policy.yaml
level: my-agent
filesystem:
  allow:
    - "./agent-workspace/**"  # Only what agent needs
  deny:
    - "/**"                   # Everything else
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
from teotl.primitives.guardrails.policy import Policy
from teotl.primitives.guardrails.classifier import classify
from teotl.core.types import ToolCall, ActionType

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

env = os.getenv("ENV", "development")
policy_path = Path(f"./policies/{env}.yaml")

agent = Agent(provider=provider, policy=policy_path)
```

### 6. Document policy rationale

Add notes to your policy files:

```yaml
level: production
notes:
  - "Network access restricted to APIs only (prevent exfiltration)"
  - "Filesystem limited to /app/data (prevent system modification)"
  - "Trust threshold high (10) for production safety"
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
from teotl.primitives.guardrails.engine import GuardrailEngine

engine = GuardrailEngine(policy="standard")

# Evaluate an action
event_result = await engine.evaluate(event, ui=ui)

if event_result.blocked:
    print(f"Blocked: {event_result.reason}")
```

### `Policy`

```python
from teotl.primitives.guardrails.policy import Policy

# Load from preset
policy = Policy.from_preset("standard")

# Load from file
policy = Policy.from_file("policy.yaml")

# Load from dict
policy = Policy.from_dict({...})

# Evaluate action
decision = policy.decide(action)  # Decision.ALLOW / CONFIRM / BLOCK

# Get block reason
reason = policy.block_reason(action)
```

### `TrustTracker`

```python
from teotl.primitives.guardrails.trust import TrustTracker

trust = TrustTracker(
    auto_approve_after=3,
    session_scoped=True
)

# Check if trusted
if trust.is_trusted(action):
    # Auto-approve

# Record approval
trust.record_approval(action)

# Reset trust
trust.reset()
```

### `classify()`

```python
from teotl.primitives.guardrails.classifier import classify
from teotl.core.types import ToolCall

tool_call = ToolCall(
    id="1",
    name="bash",
    args={"command": "ls -la"}
)

action = classify(tool_call)
# Returns Action(type=ActionType.EXECUTE, risk=RiskLevel.SAFE, ...)
```

---

## Troubleshooting

### Guardrails not working

**Check initialization:**
```python
assert agent.guardrails is not None
```

If `None`, guardrails failed to initialize (check logs).

### Actions being blocked unexpectedly

**Check audit log:**
```bash
tail ~/.teotl/audit.jsonl
```

Look for `"decision": "blocked"` entries and check the `reason` field.

**Verify policy:**
```python
from teotl.primitives.guardrails.policy import Policy
policy = Policy.from_file("my-policy.yaml")
print(policy.config)
```

### Trust not building

**Check configuration:**
```yaml
trust:
  auto_approve_after: 3  # Should be > 0
  session_scoped: true   # Check if appropriate for your use case
```

**Check if actions are similar enough:**
- Pattern matching requires exact matches if `persist_patterns: true`
- Action type matching only cares about type if `persist_patterns: false`

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

See [`examples/policies/`](../examples/policies/) for complete policy examples:

- `development.json` - Permissive for development
- `production.json` - Strict for production
- `ci-cd.json` - Non-interactive for CI/CD
- `custom-example.yaml` - Fully documented template

---

## Further Reading

- [SECURITY_AUDIT.md](SECURITY_AUDIT.md) - Complete security analysis
- [SANDBOXING_PLAN.md](SANDBOXING_PLAN.md) - Future process isolation plans
- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall framework architecture

---

**Questions or feedback?** Open an issue on GitHub!

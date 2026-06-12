# Teotl Security & Compliance Guide

Complete guide to securing your Teotl agents with features designed for compliance frameworks.

> **Note:** Teotl has not undergone formal compliance audits. The features described here are designed with GDPR, SOC2, and HIPAA practices in mind, but users requiring certified compliance should conduct their own assessments.

## Table of Contents

- [Quick Start](#quick-start)
- [Security Architecture](#security-architecture)
- [Security Presets](#security-presets)
- [Policy Configuration](#policy-configuration)
- [Sandbox Configuration](#sandbox-configuration)
- [Audit Logging](#audit-logging)
- [Compliance Features](#compliance-features)
- [Management Tools](#management-tools)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

### During Setup (Wizard)

When you run `teotl onboard`, you'll be prompted to configure security:

```bash
teotl onboard
```

The wizard will ask you to:
1. **Choose a security preset** (moderate recommended)
2. **Enable compliance features** (GDPR, SOC2, HIPAA)
3. **Set audit log level** (standard recommended)

### After Setup

Your agent workspace will contain a `security.yaml` file:

```
~/.teotl/agents/my-agent/
├── security.yaml          # Security policy
├── audit/                 # Audit logs (JSONL)
│   └── 2026-03.jsonl
└── security/              # Security data
    └── costs.json
```

## Security Architecture

Teotl provides **defense-in-depth security** with three layers:

### 1. Policy Layer (Intent Validation)

**What it does:** Defines what the agent *should* be allowed to do
- Network access control (domain allowlists/denylists)
- Filesystem access control (path restrictions)
- Tool usage control (allowed/blocked tools)
- Cost and rate limiting

**When it runs:** Before every tool call

### 2. Sandbox Layer (OS-level Enforcement)

**What it does:** Enforces what the agent *can* do at the operating system level
- Filesystem isolation (blocks access to sensitive paths)
- Network filtering (validates connections and IPs)
- Resource limits (CPU, memory, file descriptors via OS rlimit)

**When it runs:** After policy checks pass, validates at OS level

### 3. Audit Layer (Compliance & Monitoring)

**What it does:** Logs all operations for compliance and debugging
- JSONL audit logs (one event per line)
- Compliance frameworks (GDPR, SOC2, HIPAA)
- PII redaction
- Cost tracking

**When it runs:** For every security event

### Defense-in-Depth Example

When an agent tries to read `/etc/passwd`:

```
1. Policy Layer checks filesystem.allowed_paths
   → Blocked (not in allowed paths)

2. Sandbox Layer would also check (if enabled)
   → Blocked (in blocked_patterns: ["/etc/**"])

3. Audit Layer logs the violation
   → {"event_type": "policy_violation", "path": "/etc/passwd"}
```

Both layers must approve for an operation to succeed. This prevents bypasses and provides multiple security controls.

## Security Presets

Teotl provides three security presets to get you started quickly.

### Moderate (Recommended)

**Best for:** Most users, small businesses, personal use

**Policy Layer:**
- ✅ Common domains allowed (GitHub, Google, Wikipedia, AI providers)
- ✅ Agent workspace + Documents (read-only)
- ✅ File tools + web search allowed
- ✅ Cost limits: $5/hour, $50/day

**Sandbox Layer:**
- ✅ Filesystem isolation (agent workspace + /tmp + ~/Documents)
- ✅ Network filtering (domain allowlist)
- ✅ Resource limits: 1GB RAM, 5min CPU, 256 file descriptors

**Audit Layer:**
- ✅ Standard logging (violations + tool calls + costs)

**Example security.yaml:**
```yaml
version: "1.0"
agent_id: "my-agent"
log_level: "standard"

network:
  mode: "allowlist"
  allowed_domains:
    - "*.anthropic.com"
    - "*.openai.com"
    - "api.github.com"
    - "*.google.com"
    - "*.wikipedia.org"

filesystem:
  mode: "restricted"
  allowed_paths:
    - "~/.teotl/agents/my-agent/**"
    - "/tmp/**"
  readonly_paths:
    - "~/Documents/**"
  blocked_paths:
    - "~/.ssh/**"
    - "~/.aws/**"
    - "/etc/**"

tools:
  allowed:
    - "read_file"
    - "write_file"
    - "web_search"
    - "list_directory"
  blocked:
    - "execute_shell"

cost_limits:
  max_per_hour: 5.00
  max_per_day: 50.00
  max_per_month: 500.00

rate_limits:
  max_api_calls_per_minute: 20
```

### Strict

**Best for:** Sensitive data, regulated environments, maximum security

**Policy Layer:**
- 🔒 Minimal network access (AI providers only)
- 🔒 Agent workspace + /tmp only (no Documents access)
- 🔒 Basic file operations only
- 🔒 Lower cost limits: $1/hour, $10/day

**Sandbox Layer:**
- 🔒 Strict filesystem isolation (workspace + /tmp only)
- 🔒 Strict network filtering (AI providers only)
- 🔒 Lower resource limits: 512MB RAM, 3min CPU, 128 file descriptors

**Audit Layer:**
- 🔒 Detailed logging (includes PII redaction)

**When to use:**
- Handling sensitive customer data
- Regulatory requirements (healthcare, finance)
- Untrusted environments
- Development/testing

### Permissive

**Best for:** Development, trusted environments, power users

**Policy Layer:**
- ✓ Most domains allowed
- ✓ Broader filesystem access
- ✓ More tools available
- ✓ Higher cost limits: $10/hour, $100/day

**Sandbox Layer:**
- ✓ Filesystem sandbox: **disabled** (policy-only protection)
- ✓ Network sandbox: **disabled** (policy-only protection)
- ✓ Resource limits: **enabled** (2GB RAM, 10min CPU for safety)

**Audit Layer:**
- ✓ Minimal logging (violations only)

**When to use:**
- Local development
- Trusted networks
- Experimentation
- Power users who understand the risks

## Policy Configuration

### Network Policy

Control which domains your agent can access:

```yaml
network:
  mode: "allowlist"  # or "denylist", "permissive"

  # Only these domains allowed
  allowed_domains:
    - "*.github.com"
    - "api.slack.com"

  # Explicitly blocked
  blocked_domains:
    - "*.facebook.com"
    - "*.twitter.com"

  # Require user approval (interactive mode only)
  require_approval:
    - "*.amazonaws.com"
```

**Wildcards:**
- `*.github.com` - Matches api.github.com, raw.githubusercontent.com
- `github.*` - Matches github.com, github.io

### Filesystem Policy

Control file operations:

```yaml
filesystem:
  mode: "restricted"  # or "permissive"

  # Read and write access
  allowed_paths:
    - "~/.teotl/agents/my-agent/**"
    - "/tmp/**"
    - "~/projects/**"

  # Read-only access
  readonly_paths:
    - "~/Documents/**"
    - "~/Downloads/**"

  # Never accessible
  blocked_paths:
    - "~/.ssh/**"      # SSH keys
    - "~/.aws/**"      # AWS credentials
    - "/etc/**"        # System config
    - "~/.config/**"   # User config

  max_file_size_mb: 10
```

**Path patterns:**
- `/exact/path` - Exact match
- `~/config/**` - Recursive (all subdirectories)
- `/tmp/*.txt` - Single-level wildcard

### Tool Policy

Control which tools the agent can use:

```yaml
tools:
  # Only these tools allowed
  allowed:
    - "read_file"
    - "write_file"
    - "web_search"
    - "list_directory"
    - "send_email"

  # Explicitly blocked
  blocked:
    - "execute_shell"  # Too dangerous
    - "delete_file"    # Prevent accidents

  # Require approval (interactive mode)
  require_approval:
    - "send_email"
    - "create_pull_request"
```

### Cost Limits

Prevent runaway costs:

```yaml
cost_limits:
  max_per_hour: 5.00     # $5/hour
  max_per_day: 50.00     # $50/day
  max_per_month: 500.00  # $500/month
  currency: "USD"
```

**How it works:**
- Estimates cost before executing tools
- Blocks execution if limit would be exceeded
- Tracks actual costs in `security/costs.json`
- Resets automatically (hourly, daily, monthly)

### Rate Limits

Prevent API abuse:

```yaml
rate_limits:
  max_api_calls_per_minute: 20      # 20 calls/min
  max_tokens_per_hour: 100000       # 100k tokens/hour
```

**How it works:**
- Tracks calls per minute
- Blocks execution if limit exceeded
- Prevents API throttling from providers

### Data Privacy

Configure privacy settings:

```yaml
data_privacy:
  redact_pii: true          # Redact PII from logs
  encrypt_logs: false       # Encrypt audit logs (future)
  retention_days: 90        # Delete logs after 90 days
```

**PII Patterns Redacted:**
- Social Security Numbers (SSN)
- Credit card numbers
- Email addresses
- Phone numbers

## Sandbox Configuration

The sandbox layer provides OS-level enforcement to complement policy-based access control. This creates defense-in-depth where both policy AND sandbox must approve operations.

### Enabling Sandbox

```yaml
sandbox:
  enabled: true                 # Master switch
  filesystem_enabled: true      # Enable filesystem isolation
  network_enabled: true         # Enable network filtering
  resources_enabled: true       # Enable resource limits
```

### Filesystem Sandbox

Validates all file operations against allowed paths and blocked patterns:

```yaml
sandbox:
  filesystem_enabled: true

  # Paths accessible by the agent (OS-level enforcement)
  allowed_paths:
    - "~/.teotl/agents/my-agent/**"
    - "/tmp/**"
    - "~/Documents/**"

  # Maximum file size
  max_file_size_mb: 100
```

**How it works:**
1. Agent tries to read/write a file
2. Policy layer checks `filesystem.allowed_paths`
3. Sandbox layer checks `sandbox.allowed_paths` against OS-level blocked patterns
4. Sandbox blocks access to:
   - `/etc/**` (system config)
   - `/var/**` (system data)
   - `/usr/**` (system binaries)
   - `/boot/**` (boot files)
   - `~/.ssh/**` (SSH keys)
   - `~/.gnupg/**` (GPG keys)
   - `~/.aws/**` (AWS credentials)
   - `~/.config/**` (sensitive config)
5. Only if both layers approve, file access is allowed

**Pattern matching:**
- `**` - Recursive (all subdirectories): `/etc/**` blocks `/etc/passwd`, `/etc/ssh/config`, etc.
- `*` - Single-level wildcard: `~/.ssh/*.pub` blocks public keys only
- Exact paths: `/etc/passwd` blocks that specific file

### Network Sandbox

Validates all network connections against domain allowlists and IP blocklists:

```yaml
sandbox:
  network_enabled: true

  # Only these domains allowed (OS-level check)
  allowed_domains:
    - "*.anthropic.com"
    - "*.openai.com"
    - "api.github.com"
    - "*.google.com"
    - "*.wikipedia.org"

  # Block private networks (10.x, 172.16.x, 192.168.x)
  block_private_networks: false
```

**How it works:**
1. Agent tries to connect to a domain
2. Policy layer checks `network.allowed_domains`
3. Sandbox layer:
   - Checks domain against `sandbox.allowed_domains`
   - Resolves domain to IP address
   - Validates IP is not in blocked ranges:
     - `169.254.0.0/16` (link-local, always blocked)
     - `10.0.0.0/8` (if block_private_networks: true)
     - `172.16.0.0/12` (if block_private_networks: true)
     - `192.168.0.0/16` (if block_private_networks: true)
4. Only if both layers approve, connection is allowed

**Domain patterns:**
- `*.example.com` - Matches subdomains: `api.example.com`, `www.example.com`
- `example.com` - Exact match only
- `example.*` - Matches TLDs: `example.com`, `example.io`

**Use block_private_networks for:**
- Preventing access to internal networks
- Blocking SSRF attacks
- Enterprise environments
- Cloud deployments

### Resource Limits

Enforces OS-level resource limits using rlimit:

```yaml
sandbox:
  resources_enabled: true

  max_memory_mb: 1024         # 1GB RAM limit
  max_cpu_seconds: 300        # 5 minutes CPU time
  max_file_descriptors: 256   # Max open files/sockets
```

**How it works:**
- Uses Unix `resource.setrlimit()` to enforce hard limits
- Limits are applied when the agent process starts
- OS will kill the process if limits are exceeded
- Prevents:
  - Memory bombs
  - CPU exhaustion
  - File descriptor leaks
  - Fork bombs (via FD limits)

**Resource limits by preset:**

| Preset | RAM | CPU Time | File Descriptors |
|--------|-----|----------|------------------|
| Strict | 512MB | 3 min | 128 |
| Moderate | 1GB | 5 min | 256 |
| Permissive | 2GB | 10 min | 512 |

**Platform support:**
- ✅ Linux: Full support
- ✅ macOS: Full support (may require elevated privileges)
- ⚠️ Windows: Limited support (uses different mechanisms)

### Sandbox Status

Check sandbox enforcement status:

```python
from teotl.core.security import create_enforcer

enforcer = create_enforcer(workspace_dir)

if enforcer:
    status = enforcer.get_security_status()

    if "sandbox" in status:
        print(f"Filesystem sandbox: {status['sandbox']['enabled']['filesystem']}")
        print(f"Network sandbox: {status['sandbox']['enabled']['network']}")
        print(f"Resource limits: {status['sandbox']['enabled']['resources']}")

        if "resource_usage" in status['sandbox']:
            usage = status['sandbox']['resource_usage']
            print(f"CPU time: {usage['cpu_time_seconds']}s")
            print(f"Memory: {usage['memory_mb']}MB")
            print(f"File descriptors: {usage['file_descriptors']}")
```

### Sandbox Violations

When sandbox blocks an operation:

```jsonl
{
  "timestamp": "2026-03-26T14:30:00Z",
  "event_type": "policy_violation",
  "violation_type": "sandbox",
  "tool": "read_file",
  "path": "/etc/passwd",
  "reason": "Sandbox violation: Access to '/etc/passwd' blocked by pattern '/etc/**'"
}
```

Violations are logged in audit logs and counted in security reports.

### Example: Full Sandbox Configuration

```yaml
# Moderate preset with full sandbox
sandbox:
  enabled: true
  filesystem_enabled: true
  network_enabled: true
  resources_enabled: true

  # Filesystem
  allowed_paths:
    - "~/.teotl/agents/my-agent/**"
    - "/tmp/**"
    - "~/Documents/**"
  max_file_size_mb: 100

  # Network
  allowed_domains:
    - "*.anthropic.com"
    - "*.openai.com"
    - "api.github.com"
    - "*.google.com"
    - "*.wikipedia.org"
  block_private_networks: false

  # Resources
  max_memory_mb: 1024
  max_cpu_seconds: 300
  max_file_descriptors: 256
```

## Audit Logging

### Log Levels

Choose how much detail to log:

```yaml
log_level: "standard"  # minimal, standard, detailed, paranoid
```

**Minimal:**
- Only security violations
- Smallest log files
- Use for: Production, long-term storage

**Standard (Recommended):**
- Violations + tool calls + costs
- Balanced detail and size
- Use for: Most agents

**Detailed:**
- Standard + LLM prompts (PII redacted)
- Larger log files
- Use for: Debugging, compliance

**Paranoid:**
- Everything including full prompts
- Very large log files
- Use for: Security audits, investigations

### Log Format

Logs are stored as JSONL (one JSON object per line):

```jsonl
{"timestamp":"2026-03-26T14:30:00Z","agent_id":"my-agent","event_type":"tool_call","tool":"web_search","args":{"query":"AI news"},"allowed":true,"cost":0.001,"duration_ms":1500}
{"timestamp":"2026-03-26T14:31:00Z","agent_id":"my-agent","event_type":"policy_violation","policy_violated":"network","violation_reason":"Domain 'facebook.com' blocked","allowed":false}
```

### Log Location

```
~/.teotl/agents/my-agent/audit/
├── 2026-01.jsonl    # January logs
├── 2026-02.jsonl    # February logs
└── 2026-03.jsonl    # March logs
```

Logs rotate monthly automatically.

## Compliance Features

### GDPR (EU Data Privacy)

Enable GDPR compliance:

```yaml
compliance:
  gdpr_enabled: true
```

**What it provides:**
- Data subject tracking
- Purpose logging for all operations
- Legal basis tracking
- PII redaction
- Right to erasure (log cleanup)
- Data retention controls

**Audit fields:**
- `gdpr_data_subject` - Who's data was accessed
- `gdpr_purpose` - Why it was accessed
- `gdpr_legal_basis` - Legal justification

### SOC2 (Security Controls)

Enable SOC2 compliance:

```yaml
compliance:
  soc2_enabled: true
```

**What it provides:**
- Access control logging
- Authentication tracking
- Security event logging
- Audit trail for all operations

**Audit fields:**
- `soc2_auth_method` - How user authenticated
- `soc2_access_granted` - Whether access was allowed

### HIPAA (Healthcare Data)

Enable HIPAA compliance:

```yaml
compliance:
  hipaa_enabled: true
```

**What it provides:**
- PHI (Protected Health Information) access logging
- Access justification tracking
- Audit trail for healthcare data
- Retention controls

**Audit fields:**
- `hipaa_phi_accessed` - Whether PHI was accessed
- `hipaa_access_justification` - Reason for access

## Management Tools

### View Audit Logs

```bash
# View recent logs
teotl security logs --workspace ~/.teotl/agents/my-agent

# Last 7 days
teotl security logs --days 7

# Violations only
teotl security logs --violations-only

# Detailed view
teotl security logs --verbose

# Date range
teotl security logs --start 2026-03-01 --end 2026-03-26

# Filter by event type
teotl security logs --type tool_call,policy_violation
```

### Generate Compliance Report

```bash
# Last 30 days (default)
teotl security report --workspace ~/.teotl/agents/my-agent

# Last 7 days
teotl security report --days 7

# Save to file
teotl security report --output report.json
```

**Report includes:**
- Total events and violations
- Cost summary
- Top tools used
- Violations breakdown
- Compliance status

### Check Security Status

```bash
teotl security status --workspace ~/.teotl/agents/my-agent
```

**Shows:**
- Current cost usage (hourly, daily, monthly)
- Rate limit status
- Compliance features enabled
- Policy version and log level

### Programmatic Access

```python
from pathlib import Path
from teotl.ui import show_security_status, show_security_logs

# Show status in rich terminal UI
show_security_status("~/.teotl/agents/my-agent")

# Show recent logs
show_security_logs("~/.teotl/agents/my-agent", limit=20)

# Show summary
from teotl.ui import show_security_summary
show_security_summary("~/.teotl/agents/my-agent", days=7)
```

## Best Practices

### 1. Start with Moderate

Unless you have specific requirements, start with the **moderate** preset:
- ✅ Good balance of security and functionality
- ✅ Reasonable cost limits
- ✅ Standard logging (not too much, not too little)

### 2. Enable Compliance Early

If you handle regulated data, enable compliance features from the start:
- GDPR for EU user data
- SOC2 for enterprise/SaaS
- HIPAA for healthcare data

It's much harder to add compliance later.

### 3. Review Logs Regularly

```bash
# Weekly check for violations
teotl security logs --violations-only --days 7

# Monthly cost review
teotl security report --days 30
```

Set a calendar reminder!

### 4. Adjust Costs for Your Use Case

**Personal use:**
```yaml
cost_limits:
  max_per_hour: 1.00
  max_per_day: 10.00
  max_per_month: 100.00
```

**Business use:**
```yaml
cost_limits:
  max_per_hour: 10.00
  max_per_day: 100.00
  max_per_month: 1000.00
```

### 5. Use Strict for Untrusted Environments

If running agents on:
- Shared servers
- Cloud instances
- Untrusted networks

Always use **strict** preset.

### 6. Test Security Policies

Before deploying, test your policy:

1. Try accessing blocked domains
2. Try writing to blocked paths
3. Verify cost limits work
4. Check audit logs are created

### 7. Backup Audit Logs

```bash
# Backup audit logs
tar -czf audit-backup-$(date +%Y%m%d).tar.gz ~/.teotl/agents/*/audit/
```

Store backups securely for compliance.

### 8. Rotate Logs

Configure retention based on requirements:

```yaml
data_privacy:
  retention_days: 90    # GDPR: 90 days typical
  # retention_days: 2555  # HIPAA: 7 years
  # retention_days: 365   # SOC2: 1 year minimum
```

### 9. Enable Sandbox for Production

Always enable sandbox layer in production environments:

```yaml
sandbox:
  enabled: true
  filesystem_enabled: true
  network_enabled: true
  resources_enabled: true
```

Even if your policy is permissive, sandbox provides OS-level safety:
- Prevents accidental access to system files
- Blocks SSRF attacks to private networks
- Limits resource consumption (prevents OOM)

### 10. Test Sandbox in Development

Before deploying, test sandbox enforcement:

```bash
# Try accessing blocked path
teotl test-security read-file /etc/passwd

# Try accessing private network
teotl test-security http-request http://192.168.1.1

# Try exceeding resource limits
teotl test-security allocate-memory 2048  # MB
```

Verify sandbox blocks these operations.

## Troubleshooting

### Agent blocked from accessing domain

**Error:** `Domain 'example.com' is blocked by network policy`

**Solution:**
1. Open `security.yaml`
2. Add domain to `allowed_domains`:
   ```yaml
   network:
     allowed_domains:
       - "example.com"
   ```
3. Or use wildcard: `*.example.com`

### Agent blocked from writing file

**Error:** `Path '/path/to/file' is blocked by filesystem policy`

**Solution:**
1. Check if path is in `blocked_paths` (sensitive paths like ~/.ssh)
2. Add path to `allowed_paths`:
   ```yaml
   filesystem:
     allowed_paths:
       - "/path/to/directory/**"
   ```
3. Or add to `readonly_paths` if only reading

### Cost limit exceeded

**Error:** `Cost limit exceeded. Remaining: hourly=$0.00, daily=$5.23`

**Solution:**
1. Check current costs:
   ```bash
   teotl security status
   ```
2. Wait for period to reset (hourly limits reset every hour)
3. Or increase limits in `security.yaml`:
   ```yaml
   cost_limits:
     max_per_hour: 10.00  # Increased from 5.00
   ```

### Rate limit exceeded

**Error:** `Rate limit exceeded: 21 calls/min (limit: 20)`

**Solution:**
1. Wait 60 seconds for rate limit to reset
2. Or increase limit:
   ```yaml
   rate_limits:
     max_api_calls_per_minute: 30
   ```

### Audit logs not created

**Issue:** No `audit/` directory in workspace

**Solution:**
1. Check if `security.yaml` exists
2. Verify agent has write permissions:
   ```bash
   ls -la ~/.teotl/agents/my-agent/
   ```
3. Check log level isn't `minimal` (might not log much)

### PII not being redacted

**Issue:** Seeing emails/SSNs in logs

**Solution:**
1. Enable PII redaction:
   ```yaml
   data_privacy:
     redact_pii: true
   ```
2. Check log level - only works in `detailed` mode:
   ```yaml
   log_level: "detailed"
   ```

### Security policy not loading

**Error:** `Security policy not found`

**Solution:**
1. Check file exists:
   ```bash
   ls ~/.teotl/agents/my-agent/security.yaml
   ```
2. Verify YAML syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('security.yaml'))"
   ```
3. Re-run wizard to regenerate:
   ```bash
   teotl onboard
   ```

### Sandbox blocked access to allowed path

**Error:** `Sandbox violation: Access to '/home/user/data.txt' blocked`

**Issue:** Path is in policy allowed_paths but sandbox still blocks it

**Solution:**
1. Check sandbox configuration - it has its own allowed_paths:
   ```yaml
   sandbox:
     allowed_paths:
       - "/home/user/**"  # Add this
   ```
2. Sandbox blocked patterns override allowed paths - check for conflicts:
   ```yaml
   # Bad: Pattern blocks more than intended
   blocked_patterns:
     - "/home/**"  # Blocks everything in /home

   # Good: Specific pattern
   blocked_patterns:
     - "/home/*/.ssh/**"  # Only blocks SSH directories
   ```

### Sandbox blocking private network needed for development

**Error:** `Sandbox violation: Connection to 192.168.1.100 blocked (in network 192.168.0.0/16)`

**Solution:**
1. Disable private network blocking in development:
   ```yaml
   sandbox:
     block_private_networks: false  # Allow local network
   ```
2. Or add specific domain to allowed list (sandbox uses DNS):
   ```yaml
   sandbox:
     allowed_domains:
       - "*.local"  # Internal domain
   ```

### Resource limit exceeded (memory)

**Error:** `Process killed - memory limit exceeded`

**Solution:**
1. Check current resource limits:
   ```python
   status = enforcer.get_security_status()
   print(status['sandbox']['resource_usage'])
   ```
2. Increase memory limit:
   ```yaml
   sandbox:
     max_memory_mb: 2048  # Increase from 1024
   ```
3. Or disable resource limits (not recommended):
   ```yaml
   sandbox:
     resources_enabled: false
   ```

### Resource limit exceeded (CPU time)

**Error:** `Process killed - CPU time limit exceeded`

**Solution:**
1. Increase CPU time limit:
   ```yaml
   sandbox:
     max_cpu_seconds: 600  # 10 minutes (from 5 minutes)
   ```
2. Or check if agent has infinite loop - review audit logs

### File descriptor limit exceeded

**Error:** `Too many open files`

**Solution:**
1. Increase file descriptor limit:
   ```yaml
   sandbox:
     max_file_descriptors: 512  # Increase from 256
   ```
2. Or check for file descriptor leak - agent not closing files properly

### Sandbox enforcement varies by platform

**Issue:** Sandbox works on Linux but not on macOS/Windows

**Explanation:**
- Filesystem and network sandboxes work on all platforms
- Resource limits (rlimit) have platform differences:
  - **Linux:** Full support for all limits
  - **macOS:** Full support, may require elevated privileges for some limits
  - **Windows:** Limited support (uses different mechanisms)

**Solution:**
- Test sandbox on your target deployment platform
- Consider using containers (Docker) for consistent enforcement across platforms

## Advanced Configuration

### Custom Policy from Scratch

```python
from pathlib import Path
from teotl.core.security import SecurityPolicy

# Create custom policy
policy = SecurityPolicy.create_default("my-agent", preset="moderate")

# Customize
policy.network.allowed_domains.append("custom-api.com")
policy.cost_limits.max_per_hour = 10.0
policy.compliance.gdpr_enabled = True

# Save
workspace = Path("~/.teotl/agents/my-agent").expanduser()
policy.to_yaml(workspace / "security.yaml")
```

### Programmatic Enforcement

```python
from pathlib import Path
from teotl.core.security import (
    SecurityEnforcer,
    SecurityPolicy,
    SandboxManager,
    FilesystemSandbox,
    FilesystemSandboxConfig,
    NetworkSandbox,
    NetworkSandboxConfig,
    ResourceLimits,
    ResourceLimitsConfig,
)

# Load policy
policy = SecurityPolicy.from_file("security.yaml")
workspace = Path("~/.teotl/agents/my-agent").expanduser()

# Option 1: Auto-create enforcer with sandbox from policy
from teotl.core.security.enforcement import create_enforcer
enforcer = create_enforcer(workspace)  # Reads security.yaml, builds sandbox automatically

# Option 2: Manual enforcer + sandbox creation
policy = SecurityPolicy.from_file(workspace / "security.yaml")

# Build sandbox components
filesystem = FilesystemSandbox(FilesystemSandboxConfig(
    allowed_paths=[str(workspace)],
    enforce=True,
))

network = NetworkSandbox(NetworkSandboxConfig(
    allowed_domains=["*.anthropic.com"],
    enforce=True,
))

resources = ResourceLimits(ResourceLimitsConfig(
    max_memory_mb=1024,
    max_cpu_seconds=300,
    enforce=True,
))

sandbox = SandboxManager(filesystem=filesystem, network=network, resources=resources)

# Create enforcer with sandbox
enforcer = SecurityEnforcer(policy, workspace, sandbox=sandbox)

# Apply resource limits (should be called early)
sandbox.apply_resource_limits()

# Check if tool call allowed (checks both policy AND sandbox)
allowed, reason = await enforcer.enforce_tool_call(
    "web_search",
    {"query": "AI news", "url": "https://example.com"}
)

if not allowed:
    print(f"Blocked: {reason}")
    # Reason could be from policy OR sandbox layer
else:
    # Execute tool...
    result = execute_web_search()

    # Record execution
    await enforcer.record_execution(
        "web_search",
        result,
        duration_ms=1500,
        actual_cost=0.001
    )
```

### Multiple Agents with Different Policies

```bash
# Agent 1: Strict (handles sensitive data)
~/.teotl/agents/secure-agent/
├── security.yaml    # preset: strict

# Agent 2: Permissive (development)
~/.teotl/agents/dev-agent/
├── security.yaml    # preset: permissive

# Agent 3: Custom (specific requirements)
~/.teotl/agents/custom-agent/
├── security.yaml    # custom configuration
```

Each agent has its own independent security policy.

## Resources

- **Architecture:** See `docs/SECURITY_ARCHITECTURE.md` for technical details
- **Policy Reference:** See `teotl/core/security/policy.py` for all options
- **Audit Reference:** See `teotl/core/security/audit.py` for log fields
- **Examples:** See `examples/security/` for complete examples

## Support

Questions? Issues?

1. Check the [FAQ](docs/FAQ.md)
2. Review audit logs: `teotl security logs`
3. Report issues: [GitHub Issues](https://github.com/yourusername/teotl/issues)

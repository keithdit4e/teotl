# Teotl Security & Compliance Architecture

Security-first design for autonomous agents with security practices informed by GDPR, SOC2, and HIPAA frameworks.

> **Note:** Teotl has not undergone formal compliance audits. The security features described here are designed with these frameworks in mind, but users requiring certified compliance should conduct their own assessments.

## Design Principles

1. **Security by Default** - Wizard generates safe security.yaml
2. **Configurable** - Users choose security level and logging
3. **Transparent** - All security events logged and auditable
4. **Non-Intrusive** - Security enforcement happens automatically
5. **Compliance-Informed** - Security practices aligned with GDPR, SOC2, HIPAA frameworks

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Agent Executor                      │
│                                                      │
│  ┌──────────────┐         ┌──────────────┐         │
│  │   Policy     │────────▶│  Enforcement │         │
│  │   Loader     │         │    Engine    │         │
│  └──────────────┘         └───────┬──────┘         │
│         │                         │                 │
│         │                         ▼                 │
│         │                 ┌──────────────┐         │
│         │                 │   Audit      │         │
│         └────────────────▶│   Logger     │         │
│                           └──────────────┘         │
└─────────────────────────────────────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────┐
                        │  audit_YYYY-MM.  │
                        │    jsonl         │
                        └──────────────────┘
```

## Components

### 1. Policy System (`teotl/core/security/policy.py`)

**Purpose:** Define and load security policies

**Policy Structure:**
```yaml
# security.yaml
version: "1.0"
agent_id: "my-agent"

# Log level: minimal, standard, detailed, paranoid
log_level: "standard"

network:
  mode: "allowlist"  # allowlist, denylist, permissive
  allowed_domains:
    - "*.anthropic.com"
    - "*.openai.com"
    - "api.github.com"
  blocked_domains:
    - "*.facebook.com"
  require_approval:  # Interactive mode only
    - "*.amazonaws.com"

filesystem:
  mode: "restricted"  # restricted, permissive
  allowed_paths:
    - "~/.teotl/agents/{agent_id}/**"
    - "/tmp/**"
  readonly_paths:
    - "~/Documents/**"
  blocked_paths:
    - "~/.ssh/**"
    - "~/.aws/**"
    - "/etc/**"
  max_file_size_mb: 10

tools:
  allowed:
    - "read_file"
    - "write_file"
    - "web_search"
    - "list_directory"
  blocked:
    - "execute_shell"  # Too dangerous
  require_approval:
    - "send_email"
    - "create_pull_request"

cost_limits:
  max_per_hour: 5.00
  max_per_day: 50.00
  max_per_month: 500.00
  currency: "USD"

rate_limits:
  max_api_calls_per_minute: 20
  max_tokens_per_hour: 100000

data_privacy:
  redact_pii: true  # Redact PII from logs
  encrypt_logs: false  # Future: encrypt audit logs
  retention_days: 90  # Auto-delete old logs

compliance:
  gdpr_enabled: true
  soc2_enabled: true
  hipaa_enabled: false
```

**Policy Class:**
```python
class SecurityPolicy:
    """Loaded security policy."""

    def __init__(self, config: dict):
        self.version = config.get("version", "1.0")
        self.agent_id = config.get("agent_id")
        self.log_level = LogLevel(config.get("log_level", "standard"))

        # Parse sections
        self.network = NetworkPolicy(config.get("network", {}))
        self.filesystem = FilesystemPolicy(config.get("filesystem", {}))
        self.tools = ToolPolicy(config.get("tools", {}))
        self.cost_limits = CostLimits(config.get("cost_limits", {}))
        self.rate_limits = RateLimits(config.get("rate_limits", {}))
        self.data_privacy = DataPrivacy(config.get("data_privacy", {}))
        self.compliance = Compliance(config.get("compliance", {}))
```

### 2. Audit Logger (`teotl/core/security/audit.py`)

**Purpose:** Log all security-relevant events

**Log Levels:**

- **minimal** - Only security violations
- **standard** - Violations + tool calls + costs
- **detailed** - Standard + LLM prompts/responses (PII redacted)
- **paranoid** - Everything including full prompts

**JSONL Format:**
```jsonl
{"timestamp":"2026-03-26T14:30:00Z","agent_id":"my-agent","event":"tool_call","tool":"web_search","args":{"query":"AI news"},"allowed":true,"cost":0.001,"duration_ms":1500}
{"timestamp":"2026-03-26T14:31:00Z","agent_id":"my-agent","event":"policy_violation","policy":"network","violation":"blocked domain: facebook.com","tool":"fetch_url","allowed":false}
{"timestamp":"2026-03-26T14:32:00Z","agent_id":"my-agent","event":"cost_limit","limit_type":"hourly","current":4.95,"limit":5.00,"remaining":0.05}
```

**Compliance Fields:**

**GDPR:**
- Data subject ID (user)
- Purpose of processing
- Legal basis
- Data retention period
- PII redaction flag

**SOC2:**
- Access controls applied
- Authentication method
- Authorization checks
- Audit trail integrity

**HIPAA:**
- PHI access logged
- Encryption status
- Access justification
- Audit log integrity

**Audit Entry:**
```python
@dataclass
class AuditEntry:
    timestamp: datetime
    agent_id: str
    event_type: str  # tool_call, policy_violation, cost_limit, etc.

    # Event details
    tool: str | None = None
    args: dict | None = None
    result: Any | None = None

    # Security
    allowed: bool = True
    policy_violated: str | None = None
    violation_reason: str | None = None

    # Performance
    duration_ms: int | None = None
    cost: float | None = None
    tokens_used: int | None = None

    # Compliance
    gdpr_data_subject: str | None = None
    gdpr_purpose: str | None = None
    soc2_auth_method: str | None = None
    hipaa_phi_accessed: bool = False

    # Privacy
    pii_redacted: bool = False

    def to_json(self) -> dict:
        """Convert to JSON for JSONL storage."""
        # Redact PII if configured
        # Convert to flat dict
        pass
```

### 3. Enforcement Engine (`teotl/core/security/enforcement.py`)

**Purpose:** Enforce policies at runtime

**Enforcement Points:**

1. **Before Tool Execution** - Check if tool call is allowed
2. **Network Requests** - Validate domains
3. **File Operations** - Check paths
4. **Cost Tracking** - Enforce limits
5. **Rate Limiting** - Prevent abuse

**Enforcer Class:**
```python
class SecurityEnforcer:
    """Enforces security policies at runtime."""

    def __init__(
        self,
        policy: SecurityPolicy,
        audit_logger: AuditLogger,
        cost_tracker: CostTracker,
    ):
        self.policy = policy
        self.audit = audit_logger
        self.cost_tracker = cost_tracker

    async def enforce_tool_call(
        self,
        tool_name: str,
        args: dict,
    ) -> tuple[bool, str | None]:
        """
        Check if tool call is allowed.

        Returns:
            (allowed, reason_if_blocked)
        """
        # 1. Check tool policy
        if not self.policy.tools.allows(tool_name):
            reason = f"Tool '{tool_name}' blocked by policy"
            await self.audit.log_violation("tool", tool_name, reason)
            return False, reason

        # 2. Check network policy (if applicable)
        if tool_name in ["web_search", "fetch_url"]:
            domain = self._extract_domain(args)
            if not self.policy.network.allows(domain):
                reason = f"Domain '{domain}' blocked by network policy"
                await self.audit.log_violation("network", domain, reason)
                return False, reason

        # 3. Check filesystem policy (if applicable)
        if tool_name in ["read_file", "write_file"]:
            path = args.get("path") or args.get("file_path")
            if not self.policy.filesystem.allows(path, write=(tool_name == "write_file")):
                reason = f"Path '{path}' blocked by filesystem policy"
                await self.audit.log_violation("filesystem", path, reason)
                return False, reason

        # 4. Check cost limits
        estimated_cost = self._estimate_cost(tool_name, args)
        if not self.cost_tracker.would_allow(estimated_cost):
            reason = f"Cost limit exceeded (estimated: ${estimated_cost})"
            await self.audit.log_violation("cost_limit", tool_name, reason)
            return False, reason

        # 5. Check rate limits
        if not self.rate_limiter.would_allow():
            reason = "Rate limit exceeded"
            await self.audit.log_violation("rate_limit", tool_name, reason)
            return False, reason

        # Allowed!
        await self.audit.log_tool_call(tool_name, args, allowed=True)
        return True, None
```

### 4. Cost Tracker (`teotl/core/security/cost_tracker.py`)

**Purpose:** Track and limit costs

```python
class CostTracker:
    """Track API costs and enforce limits."""

    def __init__(self, policy: CostLimits, storage: Path):
        self.policy = policy
        self.storage = storage
        self.current_hour = 0.0
        self.current_day = 0.0
        self.current_month = 0.0

    def would_allow(self, estimated_cost: float) -> bool:
        """Check if cost would exceed limits."""
        if self.current_hour + estimated_cost > self.policy.max_per_hour:
            return False
        if self.current_day + estimated_cost > self.policy.max_per_day:
            return False
        if self.current_month + estimated_cost > self.policy.max_per_month:
            return False
        return True

    def record_cost(self, actual_cost: float):
        """Record actual cost after execution."""
        self.current_hour += actual_cost
        self.current_day += actual_cost
        self.current_month += actual_cost
        self._persist()
```

## Integration with Executor

**Modified Executor Flow:**

```python
class AgentExecutor:
    def __init__(self, ..., security_policy: SecurityPolicy | None = None):
        # Load security policy
        if security_policy:
            self.enforcer = SecurityEnforcer(
                policy=security_policy,
                audit_logger=AuditLogger(policy),
                cost_tracker=CostTracker(policy.cost_limits),
            )
        else:
            self.enforcer = None  # No security

    async def execute_tool(self, tool_name: str, args: dict):
        # Security check
        if self.enforcer:
            allowed, reason = await self.enforcer.enforce_tool_call(tool_name, args)
            if not allowed:
                raise SecurityError(reason)

        # Execute
        start = time.time()
        result = await tool.execute(args)
        duration_ms = (time.time() - start) * 1000

        # Log execution
        if self.enforcer:
            await self.enforcer.audit.log_execution(
                tool_name, args, result, duration_ms
            )

        return result
```

## Wizard Integration

**Security Configuration Step:**

```python
def _setup_security(self) -> None:
    """Configure security settings."""
    print_header("Step 7: Security & Compliance")

    print("\nTeotl includes built-in security and compliance features.")
    print("We recommend starting with 'Moderate' security for most users.")

    preset = ask_choice(
        "Choose security preset",
        [
            "Strict - Maximum security, minimal network access",
            "Moderate - Balanced security (recommended)",
            "Permissive - Minimal restrictions, maximum flexibility",
            "Custom - Configure manually",
        ],
        default="Moderate - Balanced security (recommended)"
    )

    if "Strict" in preset:
        self._apply_strict_security()
    elif "Moderate" in preset:
        self._apply_moderate_security()
    elif "Permissive" in preset:
        self._apply_permissive_security()
    else:
        self._configure_custom_security()

    # Compliance
    print("\n" + Color.CYAN + "Compliance Requirements" + Color.END)
    print("Enable compliance features if you handle regulated data.")

    self.config["security"]["compliance"] = {
        "gdpr_enabled": ask_yes_no("Enable GDPR compliance?", default=False),
        "soc2_enabled": ask_yes_no("Enable SOC2 compliance?", default=False),
        "hipaa_enabled": ask_yes_no("Enable HIPAA compliance?", default=False),
    }

def _apply_moderate_security(self):
    """Apply moderate security preset."""
    self.config["security"] = {
        "log_level": "standard",
        "network": {
            "mode": "allowlist",
            "allowed_domains": [
                "*.anthropic.com",
                "*.openai.com",
                "api.github.com",
                "*.google.com",
            ],
        },
        "filesystem": {
            "mode": "restricted",
            "allowed_paths": [
                f"~/.teotl/agents/{self.config['agent']['agent_id']}/**",
                "/tmp/**",
            ],
            "readonly_paths": ["~/Documents/**"],
            "blocked_paths": ["~/.ssh/**", "~/.aws/**"],
        },
        "tools": {
            "allowed": ["read_file", "write_file", "web_search", "list_directory"],
            "blocked": ["execute_shell"],
        },
        "cost_limits": {
            "max_per_hour": 5.00,
            "max_per_day": 50.00,
            "max_per_month": 500.00,
        },
        "rate_limits": {
            "max_api_calls_per_minute": 20,
        },
        "data_privacy": {
            "redact_pii": True,
            "retention_days": 90,
        },
    }
```

## Management Tools

### 1. Audit Log Viewer (`teotl/cli/audit_viewer.py`)

```bash
# View recent audit logs
teotl audit --agent my-agent --last 24h

# Search for violations
teotl audit --agent my-agent --violations-only

# Export for compliance
teotl audit --agent my-agent --export compliance_report.csv
```

### 2. Compliance Report Generator

```bash
# Generate GDPR report
teotl compliance gdpr --agent my-agent --start 2026-01-01 --end 2026-03-31

# Generate SOC2 report
teotl compliance soc2 --agent my-agent --month 2026-03
```

### 3. Policy Validator

```bash
# Validate security.yaml
teotl security validate --config security.yaml

# Test policy against hypothetical actions
teotl security test --config security.yaml --action "web_search facebook.com"
```

## Dashboard Integration

**Security Tab in Dashboard:**

- Real-time policy violations
- Cost usage graphs
- Audit log search
- Compliance status

**API Endpoints:**
```
GET /api/security/violations?agent_id=my-agent&since=24h
GET /api/security/costs?agent_id=my-agent&period=daily
GET /api/security/audit?agent_id=my-agent&limit=100
GET /api/security/compliance?agent_id=my-agent
```

## File Structure

```
teotl/
├── core/
│   └── security/
│       ├── __init__.py
│       ├── policy.py          # Policy loading and definitions
│       ├── audit.py            # Audit logging
│       ├── enforcement.py      # Runtime enforcement
│       ├── cost_tracker.py     # Cost tracking
│       └── compliance.py       # Compliance helpers
├── cli/
│   ├── audit_viewer.py         # CLI audit tool
│   └── compliance_report.py    # Compliance reports
└── web/
    └── security.py             # Dashboard security endpoints

~/.teotl/agents/my-agent/
├── security.yaml               # Security policy
├── audit/
│   ├── 2026-03.jsonl          # Monthly audit logs
│   └── 2026-04.jsonl
└── compliance/
    └── reports/                # Generated reports
```

## Testing Strategy

**Unit Tests:**
- Policy parsing
- Policy evaluation (allow/deny)
- Audit log writing
- Cost tracking
- PII redaction

**Integration Tests:**
- Tool call enforcement
- Network request blocking
- File operation blocking
- Cost limit enforcement
- Audit log generation

**Compliance Tests:**
- GDPR data subject rights
- SOC2 access control logging
- HIPAA audit trail requirements

## Security Recommendations

**For Users:**

1. **Start with Moderate** - Good balance for most use cases
2. **Enable compliance** - If handling regulated data
3. **Review audit logs** - Regularly check for violations
4. **Adjust as needed** - Loosen/tighten based on experience

**For Developers:**

1. **Never bypass security** - Always go through enforcer
2. **Log everything** - When in doubt, log it
3. **Fail secure** - Default to denying, not allowing
4. **Test violations** - Ensure policies actually work

## Future Enhancements

**Phase 2:**
- Interactive approval workflows (for require_approval items)
- Real-time policy updates without restart
- Policy templates library
- Encryption for audit logs

**Phase 3:**
- Sandboxing (Linux only)
- Network namespace isolation
- Resource limits (CPU, memory)
- Multi-tenancy support

**Phase 4:**
- Distributed audit log aggregation
- Centralized policy management
- Anomaly detection
- Security alerts/notifications

---

This architecture provides enterprise-grade security while remaining simple enough for individual developers to use.

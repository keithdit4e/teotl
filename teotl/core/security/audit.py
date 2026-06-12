"""Audit logging for security and compliance.

Logs all security-relevant events to JSONL files for:
- GDPR compliance (data access tracking)
- SOC2 compliance (access control logging)
- HIPAA compliance (PHI access audit trails)
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from teotl.core.security.policy import LogLevel, SecurityPolicy

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class AuditEntry:
    """Single audit log entry."""

    timestamp: str  # ISO 8601 format
    agent_id: str
    event_type: str  # tool_call, policy_violation, cost_limit, etc.

    # Event details
    tool: str | None = None
    args: dict | None = None
    result_summary: str | None = None

    # Security
    allowed: bool = True
    policy_violated: str | None = None
    violation_reason: str | None = None

    # Performance
    duration_ms: int | None = None
    cost: float | None = None
    tokens_used: int | None = None

    # Compliance (GDPR)
    gdpr_data_subject: str | None = None
    gdpr_purpose: str | None = None
    gdpr_legal_basis: str | None = None

    # Compliance (SOC2)
    soc2_auth_method: str | None = None
    soc2_access_granted: bool | None = None

    # Compliance (HIPAA)
    hipaa_phi_accessed: bool = False
    hipaa_access_justification: str | None = None

    # Privacy
    pii_redacted: bool = False

    def to_json(self) -> str:
        """Convert to JSON string for JSONL storage."""
        data = asdict(self)
        # Remove None values to keep logs compact
        data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data, separators=(",", ":"))

    @classmethod
    def from_json(cls, json_str: str) -> AuditEntry:
        """Parse from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


class AuditLogger:
    """Audit logger for security and compliance.

    Logs all security-relevant events to monthly JSONL files.
    Supports GDPR, SOC2, and HIPAA compliance requirements.
    """

    # PII patterns for redaction
    PII_PATTERNS = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****"),  # SSN
        (r"\b\d{16}\b", "####-####-####-####"),  # Credit card
        (r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "[EMAIL]"),  # Email
        (r"\b\d{3}-\d{3}-\d{4}\b", "###-###-####"),  # Phone
    ]

    def __init__(self, policy: SecurityPolicy, workspace_dir: Path):
        """Initialize audit logger.

        Args:
            policy: Security policy (for log level and compliance settings)
            workspace_dir: Agent workspace directory
        """
        self.policy = policy
        self.workspace_dir = workspace_dir
        self.audit_dir = workspace_dir / "audit"
        self.audit_dir.mkdir(exist_ok=True)

        # Current log file (rotated monthly)
        self.current_file = self._get_current_log_file()

    def _get_current_log_file(self) -> Path:
        """Get current month's log file."""
        now = datetime.now()
        filename = f"{now.year}-{now.month:02d}.jsonl"
        return self.audit_dir / filename

    def _should_log_event(self, event_type: str) -> bool:
        """Check if event should be logged based on log level.

        Args:
            event_type: Type of event

        Returns:
            True if should be logged
        """
        if self.policy.log_level == LogLevel.MINIMAL:
            # Only violations
            return event_type in ["policy_violation", "cost_limit", "rate_limit"]

        elif self.policy.log_level == LogLevel.STANDARD:
            # Violations + tool calls + costs
            return event_type in [
                "policy_violation",
                "cost_limit",
                "rate_limit",
                "tool_call",
                "tool_result",
            ]

        elif self.policy.log_level == LogLevel.DETAILED:
            # Standard + LLM prompts (PII redacted)
            return True

        elif self.policy.log_level == LogLevel.PARANOID:
            # Everything
            return True

        return True  # Default: log everything

    def _redact_pii(self, text: str) -> str:
        """Redact PII from text.

        Args:
            text: Text that may contain PII

        Returns:
            Text with PII redacted
        """
        if not self.policy.data_privacy.redact_pii:
            return text

        for pattern, replacement in self.PII_PATTERNS:
            text = re.sub(pattern, replacement, text)

        return text

    def _redact_dict(self, data: dict) -> dict:
        """Redact PII from dictionary values.

        Args:
            data: Dictionary that may contain PII

        Returns:
            Dictionary with PII redacted
        """
        if not self.policy.data_privacy.redact_pii:
            return data

        redacted = {}
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = self._redact_pii(value)
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [self._redact_pii(v) if isinstance(v, str) else v for v in value]
            else:
                redacted[key] = value

        return redacted

    async def log_entry(self, entry: AuditEntry) -> None:
        """Write audit entry to log.

        Args:
            entry: Audit entry to log
        """
        # Check if should log
        if not self._should_log_event(entry.event_type):
            return

        # Redact PII if needed
        if self.policy.data_privacy.redact_pii and entry.args:
            entry.args = self._redact_dict(entry.args)
            entry.pii_redacted = True

        # Rotate log file if needed (new month)
        current_file = self._get_current_log_file()
        if current_file != self.current_file:
            self.current_file = current_file

        # Append to JSONL file
        with open(self.current_file, "a") as f:
            f.write(entry.to_json() + "\n")

    async def log_tool_call(
        self,
        tool_name: str,
        args: dict,
        allowed: bool = True,
        cost: float | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Log tool call.

        Args:
            tool_name: Name of tool called
            args: Tool arguments
            allowed: Whether call was allowed
            cost: Estimated cost in USD
            duration_ms: Execution duration in milliseconds
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            agent_id=self.policy.agent_id,
            event_type="tool_call",
            tool=tool_name,
            args=args,
            allowed=allowed,
            cost=cost,
            duration_ms=duration_ms,
        )

        # Add compliance fields if enabled
        if self.policy.compliance.gdpr_enabled:
            entry.gdpr_purpose = f"Tool execution: {tool_name}"
            entry.gdpr_legal_basis = "legitimate_interest"

        if self.policy.compliance.soc2_enabled:
            entry.soc2_access_granted = allowed

        await self.log_entry(entry)

    async def log_tool_result(
        self,
        tool_name: str,
        result: Any,
        duration_ms: int,
        tokens_used: int | None = None,
    ) -> None:
        """Log tool execution result.

        Args:
            tool_name: Name of tool
            result: Execution result
            duration_ms: Execution duration
            tokens_used: Tokens used (if LLM call)
        """
        # Summarize result (don't log full result for privacy)
        result_summary = f"Success ({type(result).__name__})"
        if isinstance(result, str):
            result_summary = f"String ({len(result)} chars)"
        elif isinstance(result, list):
            result_summary = f"List ({len(result)} items)"

        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            agent_id=self.policy.agent_id,
            event_type="tool_result",
            tool=tool_name,
            result_summary=result_summary,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
        )

        await self.log_entry(entry)

    async def log_violation(
        self,
        policy_type: str,
        tool_or_resource: str,
        reason: str,
    ) -> None:
        """Log policy violation.

        Args:
            policy_type: Type of policy violated (network, filesystem, tool, cost)
            tool_or_resource: Tool name or resource being accessed
            reason: Reason for violation
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            agent_id=self.policy.agent_id,
            event_type="policy_violation",
            tool=tool_or_resource,
            allowed=False,
            policy_violated=policy_type,
            violation_reason=reason,
        )

        # Add compliance fields
        if self.policy.compliance.soc2_enabled:
            entry.soc2_access_granted = False

        await self.log_entry(entry)

    async def log_cost_limit(
        self,
        limit_type: str,
        current: float,
        limit: float,
        tool_name: str | None = None,
    ) -> None:
        """Log cost limit event.

        Args:
            limit_type: Type of limit (hourly, daily, monthly)
            current: Current cost
            limit: Limit value
            tool_name: Tool that would exceed limit
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            agent_id=self.policy.agent_id,
            event_type="cost_limit",
            tool=tool_name,
            allowed=False,
            violation_reason=f"{limit_type} limit exceeded: ${current:.2f} / ${limit:.2f}",
            cost=current,
        )

        await self.log_entry(entry)

    async def log_rate_limit(
        self,
        limit_type: str,
        current: int,
        limit: int,
        tool_name: str | None = None,
    ) -> None:
        """Log rate limit event.

        Args:
            limit_type: Type of limit (per_minute, per_hour)
            current: Current count
            limit: Limit value
            tool_name: Tool that would exceed limit
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            agent_id=self.policy.agent_id,
            event_type="rate_limit",
            tool=tool_name,
            allowed=False,
            violation_reason=f"{limit_type} rate limit exceeded: {current} / {limit}",
        )

        await self.log_entry(entry)

    async def log_llm_prompt(
        self,
        prompt: str,
        tokens_used: int,
        cost: float | None = None,
    ) -> None:
        """Log LLM prompt (only if detailed/paranoid mode).

        Args:
            prompt: Prompt sent to LLM
            tokens_used: Tokens in prompt
            cost: Estimated cost
        """
        # Only log in detailed/paranoid mode
        if self.policy.log_level not in [LogLevel.DETAILED, LogLevel.PARANOID]:
            return

        # Redact for detailed mode, full text for paranoid
        if self.policy.log_level == LogLevel.DETAILED:
            prompt = self._redact_pii(prompt)

        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            agent_id=self.policy.agent_id,
            event_type="llm_prompt",
            args={"prompt": prompt[:1000]},  # Truncate for storage
            tokens_used=tokens_used,
            cost=cost,
            pii_redacted=(self.policy.log_level == LogLevel.DETAILED),
        )

        await self.log_entry(entry)

    async def log_hipaa_access(
        self,
        resource: str,
        justification: str,
    ) -> None:
        """Log HIPAA PHI access.

        Args:
            resource: PHI resource accessed
            justification: Justification for access
        """
        if not self.policy.compliance.hipaa_enabled:
            return

        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            agent_id=self.policy.agent_id,
            event_type="hipaa_access",
            tool=resource,
            hipaa_phi_accessed=True,
            hipaa_access_justification=justification,
        )

        await self.log_entry(entry)

    def read_logs(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        event_types: list[str] | None = None,
        violations_only: bool = False,
    ) -> list[AuditEntry]:
        """Read audit logs with filtering.

        Args:
            start_date: Start date filter
            end_date: End date filter
            event_types: Filter by event types
            violations_only: Only return violations

        Returns:
            List of matching audit entries
        """
        entries = []

        # Get all JSONL files in date range
        for log_file in sorted(self.audit_dir.glob("*.jsonl")):
            # Parse date from filename (YYYY-MM.jsonl)
            try:
                year, month = log_file.stem.split("-")
                file_date = datetime(int(year), int(month), 1)

                # Check if in range
                if start_date and file_date < start_date:
                    continue
                if end_date and file_date > end_date:
                    continue

                # Read entries
                with open(log_file) as f:
                    for line in f:
                        try:
                            entry = AuditEntry.from_json(line.strip())

                            # Apply filters
                            if violations_only and entry.allowed:
                                continue

                            if event_types and entry.event_type not in event_types:
                                continue

                            entries.append(entry)

                        except Exception:
                            # Skip malformed lines
                            continue

            except Exception:
                # Skip malformed filenames
                continue

        return entries

    def cleanup_old_logs(self) -> int:
        """Delete logs older than retention period.

        Returns:
            Number of files deleted
        """
        retention_days = self.policy.data_privacy.retention_days
        cutoff_date = datetime.now()
        cutoff_date = cutoff_date.replace(day=1)  # First of month
        cutoff_date = cutoff_date.replace(month=cutoff_date.month - (retention_days // 30))

        deleted = 0
        for log_file in self.audit_dir.glob("*.jsonl"):
            try:
                year, month = log_file.stem.split("-")
                file_date = datetime(int(year), int(month), 1)

                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted += 1

            except Exception:
                continue

        return deleted

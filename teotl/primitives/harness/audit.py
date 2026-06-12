"""Comprehensive audit logging for autonomous agent execution.

Logs every turn with prompts, responses, tool calls, costs, and security events
to AUDIT_LOG.jsonl for compliance, debugging, and post-mortem analysis.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AuditEvent:
    """Single audit log event."""

    timestamp: datetime
    event_type: str  # "turn", "planning", "execution", "evaluation", "security", "cost"
    agent_id: str
    cycle: int | None = None
    step: int | None = None

    # Content
    prompt: str | None = None
    response: str | None = None
    tool_calls: list[dict] = field(default_factory=list)

    # Metadata
    model: str | None = None
    cost: float | None = None
    duration_ms: int | None = None
    success: bool = True
    error: str | None = None

    # Security
    security_events: list[dict] = field(default_factory=list)
    policy_violations: list[dict] = field(default_factory=list)

    # Additional context
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "agent_id": self.agent_id,
            "cycle": self.cycle,
            "step": self.step,
            "prompt": self.prompt,
            "response": self.response,
            "tool_calls": self.tool_calls,
            "model": self.model,
            "cost": self.cost,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "security_events": self.security_events,
            "policy_violations": self.policy_violations,
            "metadata": self.metadata,
        }


class AuditLogger:
    """Comprehensive audit logger for autonomous agents.

    Logs all execution events to AUDIT_LOG.jsonl with configurable
    detail levels and PII redaction.

    Usage:
        audit = AuditLogger(
            workspace_dir=Path("~/.forge/agents/my-agent"),
            redact_pii=True,
        )

        # Log planning event
        audit.log_planning(
            prompt="Create execution plan for...",
            response="Step 1: ...",
            model="claude-sonnet-4",
            cost=0.15,
            cycle=1,
        )

        # Log execution event
        audit.log_execution(
            step=5,
            prompt="Execute step 5...",
            response="Step complete",
            tool_calls=[{"tool": "write_file", "args": {"path": "..."}}],
            model="claude-3-haiku-20240307",
            cost=0.05,
            success=True,
        )

        # Log security event
        audit.log_security_event(
            event_type="policy_violation",
            description="Attempted access to blocked path",
            severity="critical",
        )
    """

    def __init__(
        self,
        workspace_dir: Path,
        agent_id: str,
        log_file_name: str = "AUDIT_LOG.jsonl",
        redact_pii: bool = True,
        max_prompt_length: int = 5000,
        max_response_length: int = 10000,
    ):
        """Initialize audit logger.

        Args:
            workspace_dir: Workspace directory for audit log
            agent_id: Agent identifier
            log_file_name: Name of audit log file (default: AUDIT_LOG.jsonl)
            redact_pii: Redact PII from prompts/responses
            max_prompt_length: Max prompt length to log (truncate longer)
            max_response_length: Max response length to log (truncate longer)
        """
        self.workspace_dir = Path(workspace_dir)
        self.agent_id = agent_id
        self.log_file = self.workspace_dir / log_file_name
        self.redact_pii = redact_pii
        self.max_prompt_length = max_prompt_length
        self.max_response_length = max_response_length

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Audit logger initialized: {self.log_file}")

    def _truncate_text(self, text: str | None, max_length: int) -> str | None:
        """Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text or None
        """
        if not text:
            return text

        if len(text) <= max_length:
            return text

        return text[:max_length] + f"\n... [truncated, {len(text) - max_length} chars omitted]"

    def _redact_pii_simple(self, text: str | None) -> str | None:
        """Simple PII redaction (basic patterns).

        Args:
            text: Text to redact

        Returns:
            Redacted text or None

        Note:
            This is a basic implementation. For production use, consider
            more sophisticated PII detection (e.g., presidio, spacy).
        """
        if not text or not self.redact_pii:
            return text

        import re

        # Redact email addresses
        text = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "[EMAIL_REDACTED]",
            text,
        )

        # Redact phone numbers (US format)
        text = re.sub(
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "[PHONE_REDACTED]",
            text,
        )

        # Redact SSN patterns
        text = re.sub(
            r"\b\d{3}-\d{2}-\d{4}\b",
            "[SSN_REDACTED]",
            text,
        )

        # Redact credit card numbers (basic)
        text = re.sub(
            r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
            "[CARD_REDACTED]",
            text,
        )

        return text

    def _write_event(self, event: AuditEvent) -> None:
        """Write audit event to log file.

        Args:
            event: AuditEvent to log
        """
        try:
            # Convert to dict
            event_dict = event.to_dict()

            # Redact PII if enabled
            if self.redact_pii:
                if event_dict.get("prompt"):
                    event_dict["prompt"] = self._redact_pii_simple(event_dict["prompt"])
                if event_dict.get("response"):
                    event_dict["response"] = self._redact_pii_simple(event_dict["response"])

            # Truncate long text
            if event_dict.get("prompt"):
                event_dict["prompt"] = self._truncate_text(
                    event_dict["prompt"],
                    self.max_prompt_length,
                )
            if event_dict.get("response"):
                event_dict["response"] = self._truncate_text(
                    event_dict["response"],
                    self.max_response_length,
                )

            # Write to JSONL
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event_dict) + "\n")

        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")

    def log_planning(
        self,
        prompt: str,
        response: str,
        model: str,
        cost: float,
        cycle: int,
        duration_ms: int | None = None,
        success: bool = True,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Log planning event.

        Args:
            prompt: Planning prompt
            response: Planner response
            model: Model used
            cost: Cost in USD
            cycle: Cycle number
            duration_ms: Duration in milliseconds
            success: Whether planning succeeded
            error: Error message if failed
            metadata: Additional metadata
        """
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="planning",
            agent_id=self.agent_id,
            cycle=cycle,
            prompt=prompt,
            response=response,
            model=model,
            cost=cost,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata or {},
        )

        self._write_event(event)

    def log_execution(
        self,
        step: int,
        prompt: str,
        response: str,
        model: str,
        cost: float,
        tool_calls: list[dict],
        cycle: int | None = None,
        duration_ms: int | None = None,
        success: bool = True,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Log execution event.

        Args:
            step: Step number
            prompt: Execution prompt
            response: Worker response
            model: Model used
            cost: Cost in USD
            tool_calls: List of tool calls made
            cycle: Cycle number
            duration_ms: Duration in milliseconds
            success: Whether execution succeeded
            error: Error message if failed
            metadata: Additional metadata
        """
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="execution",
            agent_id=self.agent_id,
            cycle=cycle,
            step=step,
            prompt=prompt,
            response=response,
            tool_calls=tool_calls,
            model=model,
            cost=cost,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata or {},
        )

        self._write_event(event)

    def log_evaluation(
        self,
        prompt: str,
        response: str,
        model: str,
        cost: float,
        cycle: int,
        goals_achieved: bool,
        confidence: float,
        duration_ms: int | None = None,
        success: bool = True,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Log evaluation event.

        Args:
            prompt: Evaluation prompt
            response: Evaluator response
            model: Model used
            cost: Cost in USD
            cycle: Cycle number
            goals_achieved: Whether goals were achieved
            confidence: Confidence score (0.0-1.0)
            duration_ms: Duration in milliseconds
            success: Whether evaluation succeeded
            error: Error message if failed
            metadata: Additional metadata
        """
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="evaluation",
            agent_id=self.agent_id,
            cycle=cycle,
            prompt=prompt,
            response=response,
            model=model,
            cost=cost,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata={
                **(metadata or {}),
                "goals_achieved": goals_achieved,
                "confidence": confidence,
            },
        )

        self._write_event(event)

    def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str,
        resource: str | None = None,
        action: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Log security event.

        Args:
            event_type: Type of security event (e.g., "policy_violation", "blocked_access")
            description: Event description
            severity: Severity level (info, warning, critical)
            resource: Resource affected
            action: Action attempted
            metadata: Additional metadata
        """
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="security",
            agent_id=self.agent_id,
            response=description,
            success=severity != "critical",
            security_events=[
                {
                    "type": event_type,
                    "severity": severity,
                    "resource": resource,
                    "action": action,
                }
            ],
            metadata=metadata or {},
        )

        self._write_event(event)

    def log_cost_event(
        self,
        operation: str,
        cost: float,
        budget_status: dict,
        metadata: dict | None = None,
    ) -> None:
        """Log cost tracking event.

        Args:
            operation: Operation type (planning, execution, evaluation)
            cost: Cost in USD
            budget_status: Current budget status
            metadata: Additional metadata
        """
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="cost",
            agent_id=self.agent_id,
            cost=cost,
            metadata={
                **(metadata or {}),
                "operation": operation,
                "budget_status": budget_status,
            },
        )

        self._write_event(event)

    def log_agent_turn(
        self,
        turn: int,
        prompt: str,
        response: str,
        model: str,
        cost: float,
        tool_calls: list[dict],
        success: bool = True,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Log a general agent turn (for non-planner/worker agents).

        Args:
            turn: Turn number
            prompt: User prompt or continuation marker
            response: Agent response
            model: Model used
            cost: Cost in USD
            tool_calls: List of tool calls made
            success: Whether turn succeeded
            error: Error message if failed
            metadata: Additional metadata
        """
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="agent_turn",
            agent_id=self.agent_id,
            step=turn,
            prompt=prompt,
            response=response,
            tool_calls=tool_calls,
            model=model,
            cost=cost,
            success=success,
            error=error,
            metadata=metadata or {},
        )

        self._write_event(event)

    def get_log_summary(self) -> dict:
        """Get summary of audit log.

        Returns:
            Dictionary with log statistics
        """
        if not self.log_file.exists():
            return {
                "total_events": 0,
                "by_type": {},
                "total_cost": 0.0,
                "errors": 0,
            }

        try:
            event_counts = {}
            total_cost = 0.0
            errors = 0

            with open(self.log_file) as f:
                for line in f:
                    if not line.strip():
                        continue

                    event = json.loads(line)
                    event_type = event.get("event_type", "unknown")

                    # Count by type
                    event_counts[event_type] = event_counts.get(event_type, 0) + 1

                    # Sum costs
                    if event.get("cost"):
                        total_cost += event["cost"]

                    # Count errors
                    if not event.get("success", True):
                        errors += 1

            return {
                "total_events": sum(event_counts.values()),
                "by_type": event_counts,
                "total_cost": total_cost,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Failed to get log summary: {e}")
            return {
                "error": str(e),
            }

    def __repr__(self) -> str:
        """String representation."""
        return f"AuditLogger(agent={self.agent_id}, log={self.log_file})"

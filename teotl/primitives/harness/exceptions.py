"""Exceptions for harness execution.

Custom exceptions used by the PlannerWorkerHarness for error handling
and execution control.
"""


class HarnessError(Exception):
    """Base exception for harness-related errors."""

    pass


class ExecutionHaltedError(HarnessError):
    """Raised when execution is halted due to critical issues.

    This exception is raised when health checks detect critical problems
    that require execution to stop immediately, such as:
    - Agent stuck (no progress for N turns)
    - Too many consecutive errors
    - Resource exhaustion
    - Policy violations

    Attributes:
        message: Human-readable error message
        escalations: List of EscalationEvent objects that triggered halt
        turn: Turn number when halt occurred
        recoverable: Whether execution can be resumed after fixing issue
    """

    def __init__(
        self,
        message: str,
        escalations: list | None = None,
        turn: int = 0,
        recoverable: bool = True,
    ):
        """Initialize execution halted error.

        Args:
            message: Error message
            escalations: List of escalation events
            turn: Turn number when halted
            recoverable: Whether execution can be resumed
        """
        super().__init__(message)
        self.escalations = escalations or []
        self.turn = turn
        self.recoverable = recoverable

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "type": "ExecutionHaltedError",
            "message": str(self),
            "turn": self.turn,
            "recoverable": self.recoverable,
            "escalation_count": len(self.escalations),
            "escalations": [
                {
                    "title": e.title,
                    "severity": e.severity,
                    "message": e.message,
                }
                for e in self.escalations
            ],
        }


class BudgetExceededError(HarnessError):
    """Raised when cost budget is exceeded.

    Attributes:
        spent: Amount spent so far
        limit: Budget limit that was exceeded
        limit_type: Type of limit (hourly, daily, monthly)
        operation: Operation that would exceed budget
    """

    def __init__(
        self,
        spent: float,
        limit: float,
        limit_type: str,
        operation: str | None = None,
    ):
        """Initialize budget exceeded error.

        Args:
            spent: Amount already spent
            limit: Budget limit
            limit_type: Type of limit (hourly/daily/monthly)
            operation: Operation that would exceed budget
        """
        message = f"Budget exceeded: ${spent:.2f} spent, ${limit:.2f} {limit_type} limit"
        if operation:
            message += f" (operation: {operation})"

        super().__init__(message)
        self.spent = spent
        self.limit = limit
        self.limit_type = limit_type
        self.operation = operation

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "type": "BudgetExceededError",
            "message": str(self),
            "spent": self.spent,
            "limit": self.limit,
            "limit_type": self.limit_type,
            "operation": self.operation,
        }


class PolicyViolationError(HarnessError):
    """Raised when a security policy is violated.

    Attributes:
        policy_type: Type of policy violated (filesystem, network, tool)
        resource: Resource that violated policy
        action: Action that was blocked
        reason: Human-readable reason for violation
    """

    def __init__(
        self,
        policy_type: str,
        resource: str,
        action: str,
        reason: str,
    ):
        """Initialize policy violation error.

        Args:
            policy_type: Type of policy (filesystem/network/tool)
            resource: Resource that was accessed
            action: Action that was attempted
            reason: Reason for blocking
        """
        message = f"{policy_type} policy violation: {action} on {resource} - {reason}"
        super().__init__(message)
        self.policy_type = policy_type
        self.resource = resource
        self.action = action
        self.reason = reason

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "type": "PolicyViolationError",
            "message": str(self),
            "policy_type": self.policy_type,
            "resource": self.resource,
            "action": self.action,
            "reason": self.reason,
        }


class PlanValidationError(HarnessError):
    """Raised when execution plan fails validation.

    Attributes:
        step_number: Step that failed validation
        reason: Reason for validation failure
    """

    def __init__(self, step_number: int, reason: str):
        """Initialize plan validation error.

        Args:
            step_number: Step number that failed
            reason: Validation failure reason
        """
        message = f"Plan validation failed at step {step_number}: {reason}"
        super().__init__(message)
        self.step_number = step_number
        self.reason = reason


class ApprovalDeniedError(HarnessError):
    """Raised when user denies approval to continue.

    Attributes:
        cycle: Cycle number when approval was denied
        reason: Optional reason for denial
    """

    def __init__(self, cycle: int, reason: str | None = None):
        """Initialize approval denied error.

        Args:
            cycle: Cycle number
            reason: Optional denial reason
        """
        message = f"User denied approval to continue at cycle {cycle}"
        if reason:
            message += f": {reason}"

        super().__init__(message)
        self.cycle = cycle
        self.reason = reason

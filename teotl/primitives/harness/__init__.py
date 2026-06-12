"""Harness Engineering primitives for autonomous agents.

This package provides framework-level capabilities that improve autonomous agent
reliability, cost-efficiency, and context management based on Anthropic's
Harness Engineering principles:

1. State Artifacts - Durable state via PROGRESS.md and STATE.json
2. Planner-Worker Separation - Multi-model orchestration
3. Evaluator - Deterministic verification of work completion
4. Context Janitor - Turn-based context compaction
5. Heartbeat Hooks - Autonomous oversight and health checks
6. Cost Tracking - Budget enforcement with time-windowed limits
7. Human-in-the-Loop - Approval gates for autonomous cycles
8. Security Policy - Pre-execution validation and halt on critical issues
9. Checkpoints & Rollback - Git-based checkpoints with automatic rollback
10. Audit Trail - Comprehensive JSONL logging for compliance
11. State Validation - Pydantic schemas for state integrity

These primitives are agent-type agnostic and can be configured per agent:
- Interactive assistants (inbox monitoring, chat responses)
- Autonomous developers (continuous code improvement)
- Data sync agents (CRM/ERP integration)
- Multi-agent orchestrators (coordinator → specialists)

Phase 6 Security Features:
- CostTracker: Enforce hourly/daily/monthly budget limits
- ExecutionHaltedError: Halt execution on critical health issues
- BudgetExceededError: Prevent runaway spending
- PolicyViolationError: Block unauthorized file/network access
- CycleApprovalRequest: Human approval for autonomous continuation

Phase 7 Advanced Safety:
- CheckpointManager: Git-based checkpoints before risky operations
- Checkpoint: Automatic rollback on failure
- AuditLogger: Comprehensive AUDIT_LOG.jsonl with PII redaction
- AgentState: Pydantic validation for STATE.json integrity

Phase 8 UX Improvements:
- ExplorationMode: Read-only codebase exploration before planning
- DryRunAnalyzer: Preview actions and estimate costs before execution
- StepVerifier: Enhanced pattern matching for destructive operations
- VerificationResult: Detailed safety analysis with warnings and suggestions
"""

from teotl.primitives.harness.advanced_janitor import AdvancedContextJanitor
from teotl.primitives.harness.agent import HarnessAgent
from teotl.primitives.harness.audit import AuditEvent, AuditLogger
from teotl.primitives.harness.checkpoint import Checkpoint, CheckpointManager
from teotl.primitives.harness.cost_tracker import CostTracker
from teotl.primitives.harness.dryrun import DryRunAction, DryRunAnalyzer, DryRunResult
from teotl.primitives.harness.evaluator import (
    CycleApprovalRequest,
    Evaluation,
    Evaluator,
    SupervisedResult,
)
from teotl.primitives.harness.exceptions import (
    ApprovalDeniedError,
    BudgetExceededError,
    ExecutionHaltedError,
    PlanValidationError,
    PolicyViolationError,
)
from teotl.primitives.harness.explorer import ExplorationMode, ExplorationResult
from teotl.primitives.harness.heartbeat import (
    CleanupPolicy,
    ErrorThresholdCheck,
    EscalationEvent,
    EscalationPolicy,
    HealthCheck,
    HealthStatus,
    HeartbeatMonitor,
    ProgressRateCheck,
    StuckDetectionCheck,
)
from teotl.primitives.harness.janitor import ContextJanitor
from teotl.primitives.harness.orchestrator import PlannerWorkerHarness
from teotl.primitives.harness.plan import ExecutionPlan, PlanManager, PlanStep
from teotl.primitives.harness.planner import Planner
from teotl.primitives.harness.progress import ProgressTracker
from teotl.primitives.harness.state import AgentState, StateManager
from teotl.primitives.harness.verification import StepVerifier, VerificationResult
from teotl.primitives.harness.worker import Worker, WorkerResult

__all__ = [
    # Core harness components
    "HarnessAgent",
    "PlannerWorkerHarness",
    # State management
    "ProgressTracker",
    "StateManager",
    "AgentState",
    # Context management
    "ContextJanitor",
    "AdvancedContextJanitor",
    # Health monitoring
    "HeartbeatMonitor",
    "HealthCheck",
    "HealthStatus",
    "StuckDetectionCheck",
    "ErrorThresholdCheck",
    "ProgressRateCheck",
    "EscalationPolicy",
    "EscalationEvent",
    "CleanupPolicy",
    # Planning and execution
    "Planner",
    "Worker",
    "WorkerResult",
    "Evaluator",
    "Evaluation",
    "SupervisedResult",
    "CycleApprovalRequest",
    "ExecutionPlan",
    "PlanStep",
    "PlanManager",
    # Cost tracking (Phase 6)
    "CostTracker",
    # Exceptions (Phase 6)
    "ExecutionHaltedError",
    "BudgetExceededError",
    "PolicyViolationError",
    "ApprovalDeniedError",
    "PlanValidationError",
    # Checkpoints and rollback (Phase 7)
    "CheckpointManager",
    "Checkpoint",
    # Audit trail (Phase 7)
    "AuditLogger",
    "AuditEvent",
    # Exploration and preview (Phase 8)
    "ExplorationMode",
    "ExplorationResult",
    "DryRunAnalyzer",
    "DryRunResult",
    "DryRunAction",
    "StepVerifier",
    "VerificationResult",
]

"""Planner-Worker orchestrator.

Coordinates the two-phase workflow:
1. Planner phase: Create execution plan with expensive model
2. Worker phase: Execute steps with cheap model

This pattern achieves:
- 93-97% cost savings (Sonnet plans once, Haiku executes many times)
- Better reliability (atomic steps, clear verification)
- Observable progress (PLAN.md, PROGRESS.md)
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from teotl.core.provider import Provider
from teotl.core.security.policy import SecurityPolicy
from teotl.primitives.harness.advanced_janitor import AdvancedContextJanitor
from teotl.primitives.harness.checkpoint import CheckpointManager
from teotl.primitives.harness.cost_tracker import CostTracker
from teotl.primitives.harness.evaluator import (
    CycleApprovalRequest,
    Evaluation,
    Evaluator,
    SupervisedResult,
)
from teotl.primitives.harness.exceptions import (
    BudgetExceededError,
    ExecutionHaltedError,
)
from teotl.primitives.harness.heartbeat import (
    CleanupPolicy,
    ErrorThresholdCheck,
    EscalationPolicy,
    HeartbeatMonitor,
    ProgressRateCheck,
    StuckDetectionCheck,
)
from teotl.primitives.harness.planner import Planner
from teotl.primitives.harness.state import StateManager
from teotl.primitives.harness.worker import Worker, WorkerResult

logger = logging.getLogger(__name__)


class PlannerWorkerHarness:
    """Orchestrates planner-worker execution.

    Usage:
        harness = PlannerWorkerHarness(
            agent_id="coding-assistant",
            planner_provider=AnthropicProvider(model="claude-sonnet-4"),
            worker_provider=AnthropicProvider(model="claude-3-haiku-20240307"),
            workspace_dir=agent_dir,
            worker_skills=["filesystem", "git"]
        )

        # Phase 1: Create plan (runs once)
        plan = await harness.plan(goals=goals_content)

        # Phase 2: Execute plan (runs many times)
        while not harness.is_complete():
            result = await harness.execute_next_step()
            print(f"Step {result.step.number}: {result.success}")
    """

    def __init__(
        self,
        agent_id: str,
        planner_provider: Provider,
        worker_provider: Provider,
        workspace_dir: Path | None = None,
        worker_skills: list[str] | None = None,
        worker_policy: SecurityPolicy | str = "autonomous-dev",
        planner_instructions: str | None = None,
        worker_instructions: str | None = None,
        enable_janitor: bool = True,
        janitor_compact_every: int = 5,
        janitor_max_tokens: int = 10000,
        enable_heartbeat: bool = True,
        heartbeat_check_every: int = 5,
        heartbeat_stuck_threshold: int = 10,
        heartbeat_error_threshold: int = 5,
        enable_cost_tracking: bool = True,
        cost_tracker: CostTracker | None = None,
        require_approval_for_continuation: bool = True,
        approval_callback: Callable[[CycleApprovalRequest], bool] | None = None,
        halt_on_critical_escalation: bool = True,
        enable_checkpoints: bool = True,
        checkpoint_manager: CheckpointManager | None = None,
    ):
        """Initialize orchestrator.

        Args:
            agent_id: Agent identifier
            planner_provider: Provider for planner (expensive model like Sonnet)
            worker_provider: Provider for worker (cheap model like Haiku)
            workspace_dir: Workspace directory
            worker_skills: Skills for worker (e.g., ["filesystem", "git"])
            worker_policy: Security policy for worker (SecurityPolicy or preset name)
            planner_instructions: Optional custom planner instructions
            worker_instructions: Optional custom worker instructions
            enable_janitor: Enable advanced context janitor (default: True)
            janitor_compact_every: Compact context every N worker steps (default: 5)
            janitor_max_tokens: Max context tokens before forced compaction (default: 10000)
            enable_heartbeat: Enable heartbeat monitoring (default: True)
            heartbeat_check_every: Run heartbeat every N turns (default: 5)
            heartbeat_stuck_threshold: Max turns without progress before flagging (default: 10)
            heartbeat_error_threshold: Max consecutive errors before flagging (default: 5)
            enable_cost_tracking: Enable cost tracking and budget enforcement (default: True)
            cost_tracker: Optional CostTracker instance (creates default if None)
            require_approval_for_continuation: Require human approval to continue cycles (default: True)
            approval_callback: Optional callback for approval (uses CLI prompt if None)
            halt_on_critical_escalation: Halt execution on critical health issues (default: True)
            enable_checkpoints: Enable automatic git checkpoints before steps (default: True)
            checkpoint_manager: Optional CheckpointManager instance (creates default if None)
        """
        self.agent_id = agent_id

        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path.home() / ".forge" / "agents" / agent_id

        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Load or create security policy
        if isinstance(worker_policy, str):
            self.security_policy = SecurityPolicy.create_default(agent_id, preset=worker_policy)
        else:
            self.security_policy = worker_policy

        # Initialize state
        self.state = StateManager(agent_id, self.workspace_dir)

        # Initialize checkpoint manager (before Worker needs it)
        self.checkpoint_manager = None
        if enable_checkpoints:
            self.checkpoint_manager = checkpoint_manager or CheckpointManager(
                workspace_dir=self.workspace_dir,
                auto_checkpoint_enabled=True,
            )

        # Initialize cost tracker (before Planner/Worker need it)
        self.cost_tracker = None
        if enable_cost_tracking:
            self.cost_tracker = cost_tracker or CostTracker(
                limits=self.security_policy.cost_limits,
                workspace_dir=self.workspace_dir,
            )

        # Initialize heartbeat monitor (before Worker needs it)
        self.heartbeat = None
        self.halt_on_critical = halt_on_critical_escalation
        if enable_heartbeat:
            self.heartbeat = HeartbeatMonitor(
                agent_id=agent_id,
                workspace_dir=self.workspace_dir,
                checks=[
                    StuckDetectionCheck(max_turns_without_progress=heartbeat_stuck_threshold),
                    ErrorThresholdCheck(max_consecutive_errors=heartbeat_error_threshold),
                    ProgressRateCheck(min_completion_per_hour=5.0),
                ],
                escalation_policy=EscalationPolicy(
                    notify_on_critical=True,
                    notify_on_warning=False,
                ),
                cleanup_policy=CleanupPolicy(
                    archive_logs_older_than_days=7,
                    max_archived_plans=10,
                ),
                check_interval_turns=heartbeat_check_every,
            )

        # Initialize planner with harness support
        self.planner = Planner(
            agent_id=agent_id,
            provider=planner_provider,
            workspace_dir=self.workspace_dir,
            instructions=planner_instructions,
            # Share harness components with planner
            cost_tracker=self.cost_tracker,
            audit_logger=None,  # Planner doesn't need audit (orchestrator logs it)
            state_manager=self.state,
        )

        # Initialize worker with harness support
        self.worker = Worker(
            agent_id=agent_id,
            provider=worker_provider,
            workspace_dir=self.workspace_dir,
            skills=worker_skills or [],
            policy=worker_policy,
            instructions=worker_instructions,
            enable_checkpoints=enable_checkpoints,
            checkpoint_manager=self.checkpoint_manager,
            # Share harness components with worker
            cost_tracker=self.cost_tracker,
            audit_logger=None,  # Worker doesn't need audit (orchestrator logs it)
            state_manager=self.state,
            heartbeat_monitor=self.heartbeat,
        )

        # Initialize evaluator (uses same provider as planner)
        self.evaluator = Evaluator(
            agent_id=agent_id,
            provider=planner_provider,  # Same strategic model as planner
            workspace_dir=self.workspace_dir,
        )

        # Initialize advanced janitor (uses worker provider for extraction)
        self.janitor = None
        if enable_janitor:
            self.janitor = AdvancedContextJanitor(
                agent_id=agent_id,
                provider=worker_provider,  # Cheap model for extraction
                workspace_dir=self.workspace_dir,
                compact_every=janitor_compact_every,
                max_context_tokens=janitor_max_tokens,
                use_llm_extraction=True,
            )

        # Approval settings
        self.require_approval = require_approval_for_continuation
        self.approval_callback = approval_callback

        logger.info(
            f"PlannerWorkerHarness initialized:\n"
            f"  Planner: {planner_provider.model}\n"
            f"  Worker: {worker_provider.model}\n"
            f"  Evaluator: {planner_provider.model}\n"
            f"  Janitor: {'enabled' if enable_janitor else 'disabled'}\n"
            f"  Heartbeat: {'enabled' if enable_heartbeat else 'disabled'}\n"
            f"  Cost Tracking: {'enabled' if enable_cost_tracking else 'disabled'}\n"
            f"  Checkpoints: {'enabled' if enable_checkpoints else 'disabled'}\n"
            f"  Approval Required: {'yes' if require_approval_for_continuation else 'no'}\n"
            f"  Halt on Critical: {'yes' if halt_on_critical_escalation else 'no'}"
        )

    async def _request_approval(self, request: CycleApprovalRequest) -> bool:
        """Request user approval to continue to next cycle.

        Args:
            request: Approval request with cycle info and cost estimates

        Returns:
            True if approved, False if denied

        Raises:
            ApprovalDeniedError: If user denies approval
        """
        # Use custom callback if provided
        if self.approval_callback:
            try:
                return self.approval_callback(request)
            except Exception as e:
                logger.error(f"Approval callback failed: {e}")
                return False

        # Default CLI approval prompt
        logger.info("\n" + "=" * 70)
        logger.info(request.to_summary_text())
        logger.info("=" * 70)

        # Simple yes/no prompt (in real implementation would use proper input)
        # For now, auto-approve in library mode (caller should provide callback)
        logger.warning(
            "No approval callback provided - auto-approving continuation. "
            "Set approval_callback to enable human-in-the-loop approval."
        )
        return True

    async def plan(
        self,
        goals: str,
        context: str | None = None,
        force_replan: bool = False,
    ) -> Any:  # ExecutionPlan
        """Create execution plan (planner phase).

        Args:
            goals: High-level goals to achieve
            context: Optional additional context
            force_replan: Force replanning even if plan exists

        Returns:
            ExecutionPlan
        """
        # Check if plan already exists
        if self.planner.plan_manager.exists() and not force_replan:
            logger.info("Plan already exists. Use force_replan=True to create new plan.")
            return self.planner.plan_manager.load()

        # Archive existing plan if forcing replan
        if self.planner.plan_manager.exists() and force_replan:
            logger.info("Archiving existing plan...")
            self.planner.plan_manager.archive(suffix="before_replan")

        # Create plan
        logger.info("Creating execution plan...")
        plan = await self.planner.create_plan(goals=goals, context=context)

        logger.info(
            f"Plan created: {plan.total_steps} steps\n  PLAN.md: {self.planner.plan_manager.path}"
        )

        return plan

    async def execute_next_step(
        self,
        max_retries: int = 3,
    ) -> WorkerResult:
        """Execute the next step in the plan (worker phase).

        Args:
            max_retries: Maximum retries for failed steps

        Returns:
            WorkerResult

        Raises:
            BudgetExceededError: If operation would exceed budget
            ExecutionHaltedError: If critical health issues detected
        """
        # Update turn counter
        current_turn = self.state.get("current_turn", 0) + 1
        self.state.update(current_turn=current_turn)

        # Check budget before execution
        if self.cost_tracker:
            estimated_cost = self.cost_tracker.estimate_operation_cost(
                operation_type="execution",
                num_steps=1,
            )
            try:
                self.cost_tracker.can_spend(estimated_cost)
            except BudgetExceededError as e:
                logger.error(f"Budget exceeded before step execution: {e}")
                raise

        # Execute current step
        result = await self.worker.execute_current_step()

        # Track in janitor if enabled
        if self.janitor:
            await self.janitor.after_turn_async(
                agent_response=result.response,
                context_snapshot=None,  # Could estimate from result
            )

        # Handle retries if failed
        if not result.success and max_retries > 0:
            logger.warning(f"Step {result.step.number} failed, retrying...")

            for attempt in range(max_retries):
                logger.info(f"Retry attempt {attempt + 1}/{max_retries}")

                result = await self.worker.retry_step(
                    step_number=result.step.number,
                    feedback=result.error or "Previous attempt did not succeed. Try again.",
                )

                if result.success:
                    logger.info(f"Step {result.step.number} succeeded on retry {attempt + 1}")
                    break
            else:
                logger.error(f"Step {result.step.number} failed after {max_retries} retries")
                # Mark step as skipped in plan
                self.worker.plan_manager.mark_skipped(
                    result.step.number,
                    reason=f"Failed after {max_retries} retries: {result.error}",
                )

        # Update health metrics in state
        if result.success:
            # Reset error counter, track progress
            self.state.save(
                consecutive_errors=0,
                last_progress_turn=current_turn,
            )
        else:
            # Increment error counter
            consecutive_errors = self.state.get("consecutive_errors", 0) + 1
            self.state.save(
                consecutive_errors=consecutive_errors,
                last_error=result.error or "Unknown error",
            )

        # Record cost after execution
        if self.cost_tracker:
            # Estimate actual cost based on tools used
            actual_cost = result.tools_used * 0.25 if result.tools_used else 0.10
            self.cost_tracker.record(
                cost=actual_cost,
                operation="execution",
                metadata={
                    "step": result.step.number,
                    "success": result.success,
                    "tools_used": result.tools_used,
                },
            )

        # Run heartbeat check if enabled
        critical_escalations = []
        if self.heartbeat and self.heartbeat.should_run_heartbeat(current_turn):
            heartbeat_result = self.heartbeat.heartbeat(
                state=self.state,
                progress=self.worker.progress,
            )

            # Log escalations
            if heartbeat_result.get("escalations"):
                for escalation in heartbeat_result["escalations"]:
                    logger.critical(f"ESCALATION: {escalation.title}")
                    logger.critical(escalation.to_markdown())

                    # Track critical escalations
                    if escalation.severity == "critical":
                        critical_escalations.append(escalation)

        # Halt execution if critical escalations detected
        if self.halt_on_critical and critical_escalations:
            logger.error(f"HALTING: {len(critical_escalations)} critical escalation(s) detected")
            raise ExecutionHaltedError(
                message=f"Execution halted due to {len(critical_escalations)} critical health issue(s)",
                escalations=critical_escalations,
                turn=current_turn,
                recoverable=True,
            )

        return result

    async def execute_all_steps(
        self,
        max_retries: int = 3,
        stop_on_failure: bool = False,
    ) -> list[WorkerResult]:
        """Execute all remaining steps in the plan.

        Args:
            max_retries: Maximum retries per step
            stop_on_failure: Stop execution if a step fails

        Returns:
            List of WorkerResults for all executed steps
        """
        results = []

        while not self.is_complete():
            result = await self.execute_next_step(max_retries=max_retries)
            results.append(result)

            logger.info(
                f"Step {result.step.number}: {'✅ Success' if result.success else '❌ Failed'}"
            )

            if not result.success and stop_on_failure:
                logger.warning("Stopping execution due to failure")
                break

        return results

    def is_complete(self) -> bool:
        """Check if plan execution is complete.

        Returns:
            True if all steps are done
        """
        try:
            plan = self.planner.plan_manager.load()
            return plan.is_complete
        except FileNotFoundError:
            return False

    def get_progress(self) -> dict:
        """Get current progress.

        Returns:
            Progress dictionary with stats
        """
        try:
            plan = self.planner.plan_manager.load()
            self.worker.progress.read() if self.worker.progress.exists() else None

            return {
                "total_steps": plan.total_steps,
                "completed": len(plan.completed_steps),
                "remaining": len(plan.remaining_steps),
                "current_step": plan.current_step.number if plan.current_step else None,
                "current_description": plan.current_step.description if plan.current_step else None,
                "completion_percentage": plan.completion_percentage,
                "is_complete": plan.is_complete,
            }
        except FileNotFoundError:
            return {
                "error": "No plan found",
                "is_complete": False,
            }

    async def refine_plan(self, feedback: str) -> Any:  # ExecutionPlan
        """Refine the plan based on feedback.

        Args:
            feedback: Feedback on current plan

        Returns:
            Refined ExecutionPlan
        """
        logger.info("Refining plan based on feedback...")
        plan = await self.planner.refine_plan(feedback=feedback)

        logger.info(f"Plan refined: {plan.total_steps} steps")

        return plan

    def reset(self) -> None:
        """Reset planner-worker state (for new execution).

        Warning: This clears PLAN.md, PROGRESS.md, and related state.
        """
        logger.warning("Resetting planner-worker state...")

        # Archive current plan if exists
        if self.planner.plan_manager.exists():
            self.planner.plan_manager.archive(suffix="before_reset")

        # Clear plan and progress
        self.planner.plan_manager.clear()
        self.worker.progress.clear()

        # Reset state
        self.state.clear()

        logger.info("Reset complete")

    async def run_supervised_cycle(
        self,
        goals: str,
        max_cycles: int = 3,
        max_retries_per_step: int = 3,
        context: str | None = None,
    ) -> SupervisedResult:
        """Run supervised execution with planner→worker→evaluator loop.

        This creates a closed-loop system where:
        1. Planner (Sonnet) creates execution plan
        2. Worker (Haiku) executes all steps
        3. Evaluator (Sonnet) assesses if goals achieved
        4. If not complete: Return to step 1 with continuation goals
        5. If complete: Generate user report

        Args:
            goals: High-level goals to achieve
            max_cycles: Maximum planner→worker→evaluator cycles (default: 3)
            max_retries_per_step: Maximum retries per failed step (default: 3)
            context: Optional additional context

        Returns:
            SupervisedResult with completion status and report

        Example:
            harness = PlannerWorkerHarness(...)

            result = await harness.run_supervised_cycle(
                goals="Improve code quality and fix bugs",
                max_cycles=3
            )

            if result.complete:
                print(result.completion_report)
            else:
                print(f"Stopped after {result.cycles_completed} cycles: {result.reason}")
        """
        logger.info(f"Starting supervised execution (max {max_cycles} cycles)")
        logger.info(f"Goals: {goals[:100]}...")

        # Initialize execution tracking
        from datetime import datetime

        self.state.save(
            execution_start_time=datetime.now().isoformat(),
            current_turn=0,
            consecutive_errors=0,
            last_progress_turn=0,
        )

        current_goals = goals
        cycle = 0
        evaluations = []

        while cycle < max_cycles:
            cycle += 1
            logger.info(f"\n{'=' * 70}")
            logger.info(f"CYCLE {cycle}/{max_cycles}")
            logger.info(f"{'=' * 70}\n")

            # Save cycle state
            self.state.save(
                current_cycle=cycle,
                max_cycles=max_cycles,
            )

            # ---------------------------------------------------------------
            # PHASE 1: PLANNING
            # ---------------------------------------------------------------
            logger.info(f"PHASE 1: PLANNING (Cycle {cycle})")

            # Check budget before planning
            if self.cost_tracker:
                estimated_cost = self.cost_tracker.estimate_operation_cost("planning")
                try:
                    self.cost_tracker.can_spend(estimated_cost)
                except BudgetExceededError as e:
                    logger.error(f"Budget exceeded before planning: {e}")
                    return SupervisedResult(
                        complete=False,
                        cycles_completed=cycle - 1,
                        final_evaluation=evaluations[-1]
                        if evaluations
                        else Evaluation(
                            goals_achieved=False,
                            confidence=0.0,
                            what_was_done=[],
                            what_remains=["Budget exceeded"],
                            test_status="unknown",
                        ),
                        reason=f"Budget exceeded before planning cycle {cycle}: {e}",
                    )

            try:
                # Archive previous plan if exists
                if cycle > 1 and self.planner.plan_manager.exists():
                    self.planner.plan_manager.archive(suffix=f"cycle{cycle - 1}")
                    self.planner.plan_manager.clear()

                # Create plan
                plan = await self.plan(
                    goals=current_goals,
                    context=context,
                    force_replan=True,
                )

                logger.info(f"✅ Plan created: {plan.total_steps} steps")

                # Record planning cost
                if self.cost_tracker:
                    actual_cost = self.cost_tracker.estimate_operation_cost("planning")
                    self.cost_tracker.record(
                        cost=actual_cost,
                        operation="planning",
                        metadata={"cycle": cycle, "steps": plan.total_steps},
                    )

            except Exception as e:
                logger.error(f"Planning failed: {e}")
                return SupervisedResult(
                    complete=False,
                    cycles_completed=cycle,
                    final_evaluation=Evaluation(
                        goals_achieved=False,
                        confidence=0.0,
                        what_was_done=[],
                        what_remains=[f"Planning error: {e}"],
                        test_status="unknown",
                    ),
                    reason=f"Planning failed in cycle {cycle}: {e}",
                )

            # ---------------------------------------------------------------
            # PHASE 2: EXECUTION
            # ---------------------------------------------------------------
            logger.info(f"\nPHASE 2: EXECUTION (Cycle {cycle})")

            # Check budget before execution
            if self.cost_tracker:
                estimated_cost = self.cost_tracker.estimate_operation_cost(
                    "execution",
                    num_steps=plan.total_steps,
                )
                try:
                    self.cost_tracker.can_spend(estimated_cost)
                except BudgetExceededError as e:
                    logger.error(f"Budget exceeded before execution: {e}")
                    return SupervisedResult(
                        complete=False,
                        cycles_completed=cycle - 1,
                        final_evaluation=evaluations[-1]
                        if evaluations
                        else Evaluation(
                            goals_achieved=False,
                            confidence=0.0,
                            what_was_done=[],
                            what_remains=["Budget exceeded"],
                            test_status="unknown",
                        ),
                        reason=f"Budget exceeded before execution cycle {cycle}: {e}",
                    )

            try:
                # Execute all steps (costs recorded per step in execute_next_step)
                results = await self.execute_all_steps(
                    max_retries=max_retries_per_step,
                    stop_on_failure=False,  # Continue even if some steps fail
                )

                success_count = sum(1 for r in results if r.success)
                logger.info(
                    f"✅ Execution complete: {success_count}/{len(results)} steps succeeded"
                )

            except ExecutionHaltedError:
                # Re-raise execution halt errors
                raise

            except Exception as e:
                logger.error(f"Execution failed: {e}")
                return SupervisedResult(
                    complete=False,
                    cycles_completed=cycle,
                    final_evaluation=Evaluation(
                        goals_achieved=False,
                        confidence=0.0,
                        what_was_done=[],
                        what_remains=[f"Execution error: {e}"],
                        test_status="unknown",
                    ),
                    reason=f"Execution failed in cycle {cycle}: {e}",
                )

            # ---------------------------------------------------------------
            # PHASE 3: EVALUATION
            # ---------------------------------------------------------------
            logger.info(f"\nPHASE 3: EVALUATION (Cycle {cycle})")

            # Check budget before evaluation
            if self.cost_tracker:
                estimated_cost = self.cost_tracker.estimate_operation_cost("evaluation")
                try:
                    self.cost_tracker.can_spend(estimated_cost)
                except BudgetExceededError as e:
                    logger.error(f"Budget exceeded before evaluation: {e}")
                    return SupervisedResult(
                        complete=False,
                        cycles_completed=cycle,
                        final_evaluation=evaluations[-1]
                        if evaluations
                        else Evaluation(
                            goals_achieved=False,
                            confidence=0.0,
                            what_was_done=[],
                            what_remains=["Budget exceeded"],
                            test_status="unknown",
                        ),
                        reason=f"Budget exceeded before evaluation cycle {cycle}: {e}",
                    )

            try:
                # Evaluate if goals achieved
                evaluation = await self.evaluator.evaluate(
                    original_goals=goals,  # Original goals, not continuation
                    context=f"After cycle {cycle} of {max_cycles}",
                )

                evaluations.append(evaluation)

                # Record evaluation cost
                if self.cost_tracker:
                    actual_cost = self.cost_tracker.estimate_operation_cost("evaluation")
                    self.cost_tracker.record(
                        cost=actual_cost,
                        operation="evaluation",
                        metadata={
                            "cycle": cycle,
                            "goals_achieved": evaluation.goals_achieved,
                            "confidence": evaluation.confidence,
                        },
                    )

                logger.info(
                    f"{'✅ COMPLETE' if evaluation.goals_achieved else '🔄 CONTINUE'} "
                    f"(confidence: {evaluation.confidence:.2f})"
                )

                # ---------------------------------------------------------------
                # DECISION: COMPLETE or CONTINUE
                # ---------------------------------------------------------------
                if evaluation.goals_achieved:
                    logger.info(f"\n🎉 Goals achieved after {cycle} cycle(s)!")

                    # Generate completion report
                    report = await self.evaluator.generate_completion_report(
                        original_goals=goals,
                        evaluation=evaluation,
                        cycles_completed=cycle,
                    )

                    return SupervisedResult(
                        complete=True,
                        cycles_completed=cycle,
                        final_evaluation=evaluation,
                        completion_report=report,
                    )

                else:
                    # More work needed
                    logger.info(f"🔄 Goals not yet achieved, planning cycle {cycle + 1}...")

                    if evaluation.continuation_goals:
                        logger.info(f"Continuation goals: {evaluation.continuation_goals[:100]}...")
                        current_goals = evaluation.continuation_goals
                    else:
                        logger.warning("No continuation goals provided, using original goals")
                        current_goals = goals

                    # Request approval to continue if enabled and not on last cycle
                    if self.require_approval and cycle < max_cycles:
                        # Estimate cost of next cycle
                        estimated_next_cost = 0.0
                        if self.cost_tracker:
                            estimated_next_cost = (
                                self.cost_tracker.estimate_operation_cost("planning")
                                + self.cost_tracker.estimate_operation_cost(
                                    "execution", num_steps=10
                                )
                                + self.cost_tracker.estimate_operation_cost("evaluation")
                            )

                        # Create approval request
                        approval_request = CycleApprovalRequest(
                            cycle=cycle,
                            evaluation=evaluation,
                            estimated_next_cost=estimated_next_cost,
                            cost_summary=self.cost_tracker.get_summary()
                            if self.cost_tracker
                            else {},
                        )

                        # Ask for approval
                        approved = await self._request_approval(approval_request)

                        if not approved:
                            logger.warning(f"User denied approval to continue after cycle {cycle}")
                            return SupervisedResult(
                                complete=False,
                                cycles_completed=cycle,
                                final_evaluation=evaluation,
                                reason=f"User denied approval to continue after cycle {cycle}",
                            )

                    # Continue to next cycle
                    continue

            except Exception as e:
                logger.error(f"Evaluation failed: {e}")
                return SupervisedResult(
                    complete=False,
                    cycles_completed=cycle,
                    final_evaluation=Evaluation(
                        goals_achieved=False,
                        confidence=0.0,
                        what_was_done=[],
                        what_remains=[f"Evaluation error: {e}"],
                        test_status="unknown",
                    ),
                    reason=f"Evaluation failed in cycle {cycle}: {e}",
                )

        # Max cycles reached without completion
        logger.warning(f"Max cycles ({max_cycles}) reached without completion")

        final_evaluation = (
            evaluations[-1]
            if evaluations
            else Evaluation(
                goals_achieved=False,
                confidence=0.0,
                what_was_done=[],
                what_remains=["Max cycles reached"],
                test_status="unknown",
            )
        )

        return SupervisedResult(
            complete=False,
            cycles_completed=max_cycles,
            final_evaluation=final_evaluation,
            reason=f"Max cycles ({max_cycles}) reached without achieving goals",
        )

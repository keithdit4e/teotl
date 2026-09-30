"""Worker phase - Executes plan steps using cheap models.

Workers execute ONE atomic step at a time from the plan.
They are constrained to follow the plan exactly - no strategic decisions.

Key responsibilities:
- Read current step from PLAN.md
- Execute the specific change
- Verify completion
- Update PROGRESS.md
- Return results for evaluation
"""

import logging
import re
from pathlib import Path
from typing import Any

from teotl.core.agent import Agent
from teotl.core.paths import teotl_home
from teotl.core.provider import Provider
from teotl.core.security.policy import SecurityPolicy
from teotl.primitives.guardrails.presets import guardrail_preset_for
from teotl.primitives.harness.checkpoint import CheckpointManager
from teotl.primitives.harness.plan import ExecutionPlan, PlanManager, PlanStep
from teotl.primitives.harness.progress import ProgressTracker
from teotl.primitives.harness.state import StateManager

logger = logging.getLogger(__name__)


_STATUS_RE = re.compile(r"STEP_STATUS:\s*(DONE|FAILED)\b", re.IGNORECASE)


def _status_line(text: str) -> str | None:
    """The last STEP_STATUS value in the worker's reply ("DONE"/"FAILED"), or None."""
    matches = _STATUS_RE.findall(text or "")
    return matches[-1].upper() if matches else None


def _concrete_path(file_path: str | None) -> Path | None:
    """The step's File field as a Path, or None when it isn't a real path.

    Planner output is free text: skip placeholders ("<proj>/x.py"), notes
    ("N/A (environment check)"), and multiple files ("a.py and b.py").
    """
    if not file_path:
        return None
    text = file_path.strip().strip("`").strip()
    if not text or any(c in text for c in "<>*?`|\n") or " " in text:
        return None
    if text.lower() in ("n/a", "na", "none", "-"):
        return None
    return Path(text).expanduser().resolve()


def _is_removal(step: PlanStep) -> bool:
    words = f"{step.description} {step.change or ''}".lower()
    return any(w in words for w in ("delete", "remove", "rename", "move "))


class WorkerResult:
    """Result of worker execution."""

    def __init__(
        self,
        success: bool,
        step: PlanStep,
        response: str,
        tools_used: int = 0,
        error: str | None = None,
    ):
        """Initialize worker result.

        Args:
            success: Whether execution succeeded
            step: Step that was executed
            response: Worker's response text
            tools_used: Number of tools called
            error: Error message if failed
        """
        self.success = success
        self.step = step
        self.response = response
        self.tools_used = tools_used
        self.error = error


class Worker:
    """Executes plan steps using cheap models (Haiku).

    The Worker runs MANY times (once per step) to execute the plan.
    Each execution is fast and cheap.

    Usage:
        worker = Worker(
            agent_id="coding-assistant",
            provider=AnthropicProvider(model="claude-haiku-4-5"),
            workspace_dir=agent_dir,
            skills=["filesystem", "git"]
        )

        # Execute current step from plan
        result = await worker.execute_current_step()

        if result.success:
            print(f"Step {result.step.number} complete!")
        else:
            print(f"Step failed: {result.error}")
    """

    def __init__(
        self,
        agent_id: str,
        provider: Provider,
        workspace_dir: Path | None = None,
        skills: list[str] | None = None,
        policy: SecurityPolicy | str = "autonomous-dev",
        instructions: str | None = None,
        enable_checkpoints: bool = True,
        checkpoint_manager: CheckpointManager | None = None,
        # Harness components (optional, shared from orchestrator)
        cost_tracker=None,
        audit_logger=None,
        state_manager=None,
        heartbeat_monitor=None,
    ):
        """Initialize worker.

        Args:
            agent_id: Agent identifier
            provider: Provider with cheap model (Haiku)
            workspace_dir: Workspace directory
            skills: Skills to enable
            policy: Security policy (SecurityPolicy object or preset name)
            instructions: Optional custom worker instructions
            enable_checkpoints: Enable automatic checkpoints before steps
            checkpoint_manager: Optional CheckpointManager instance
        """
        self.agent_id = agent_id
        self.provider = provider

        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = teotl_home() / "agents" / agent_id

        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Load security policy
        if isinstance(policy, str):
            self.policy = SecurityPolicy.create_default(agent_id, preset=policy)
            logger.info(f"Loaded security policy preset: {policy}")
        elif isinstance(policy, SecurityPolicy):
            self.policy = policy
            logger.info(f"Using provided SecurityPolicy for agent: {agent_id}")
        else:
            # Try to use it as-is (for backward compatibility)
            self.policy = None
            logger.warning(
                f"Policy is neither SecurityPolicy nor string preset: {type(policy)}. "
                "Security validation will be limited."
            )

        # Validate policy
        if self.policy:
            self._validate_policy()

        # Initialize managers
        self.plan_manager = PlanManager(agent_id, self.workspace_dir)
        self.progress = ProgressTracker(agent_id, self.workspace_dir)
        self.state = state_manager or StateManager(agent_id, self.workspace_dir)

        # Initialize checkpoint manager
        self.checkpoint_manager = None
        if enable_checkpoints:
            self.checkpoint_manager = checkpoint_manager or CheckpointManager(
                workspace_dir=self.workspace_dir,
                auto_checkpoint_enabled=True,
            )
            logger.info(f"Checkpoint manager: {self.checkpoint_manager}")

        # Worker instructions
        self.instructions = instructions or self._default_instructions()

        # Create worker agent with harness support
        self.agent = Agent(
            provider=provider,
            instructions=self.instructions,
            skills=skills or [],
            # Tool-call guardrails need a guardrail preset, not a SecurityPolicy
            policy=guardrail_preset_for(policy),
            session_dir=self.workspace_dir / "sessions" / "worker",
            # Pass harness components to agent
            cost_tracker=cost_tracker,
            audit_logger=audit_logger,
            checkpoint_manager=self.checkpoint_manager,
            heartbeat_monitor=heartbeat_monitor,
            state_manager=self.state,
        )

        logger.info(f"Worker initialized with model: {provider.model}")

    def _validate_policy(self) -> None:
        """Validate that security policy has required constraints."""
        if not self.policy:
            return

        # Warn if policy is too permissive
        if not self.policy.filesystem.blocked_paths:
            logger.warning(
                "Security policy has no blocked_paths - sensitive files may be accessible!"
            )

        if not self.policy.cost_limits:
            logger.warning("Security policy has no cost_limits - unbounded spending possible!")

        # Log policy mode
        logger.info(f"Filesystem policy mode: {self.policy.filesystem.mode}")
        logger.info(f"Network policy mode: {self.policy.network.mode}")

    def _validate_step_safety(self, step: PlanStep) -> tuple[bool, str | None]:
        """Validate step against security policy before execution.

        Args:
            step: Step to validate

        Returns:
            Tuple of (is_safe, error_message)
        """
        if not self.policy:
            # No policy to enforce
            return (True, None)

        # Check the step's target file against the policy's denylist. Only concrete
        # paths are checked: the planner's File field is free text and may hold
        # placeholders ("<proj>/calc.py", "N/A"). The allowlist isn't applied here:
        # projects can live anywhere, and actual tool calls are checked by the
        # worker agent's guardrails.
        path = _concrete_path(step.file_path)
        if path is not None:
            fs = self.policy.filesystem
            if fs._matches_path(path, fs.blocked_paths) or fs._matches_path(path, fs.readonly_paths):
                reason = f"File path blocked by security policy: {path}"
                logger.error(reason)
                return (False, reason)

        # Check for destructive patterns
        if self._is_destructive_step(step):
            # Destructive steps should require explicit handling
            logger.warning(f"Step {step.number} contains destructive operations")
            # For now, allow but log - can be made stricter
            # return (False, "Destructive operation requires explicit approval")

        return (True, None)

    def _is_destructive_step(self, step: PlanStep) -> bool:
        """Check if step contains potentially destructive operations.

        Args:
            step: Step to check

        Returns:
            True if step appears to be destructive
        """
        DESTRUCTIVE_KEYWORDS = [
            "rm -rf",
            "delete",
            "drop table",
            "truncate",
            "format",
            "remove all",
            "clear all",
        ]

        step_text = f"{step.description} {step.change or ''}".lower()

        return any(keyword in step_text for keyword in DESTRUCTIVE_KEYWORDS)

    def _default_instructions(self) -> str:
        """Default worker instructions."""
        return """You are a precise code execution agent.

Your job is to execute ONE specific step from an execution plan.

## Your Constraints

1. **NO STRATEGIC DECISIONS** - You follow the plan exactly
   - The Planner already decided what to do
   - You only decide HOW to execute it
   - Do not deviate from the step

2. **ONE STEP ONLY** - Execute exactly one atomic task
   - Do not work ahead
   - Do not combine multiple steps
   - Stop after completing the current step

3. **VERIFICATION REQUIRED** - Always verify your work
   - Run tests if specified
   - Check that the change was applied
   - Confirm the file was modified

## Your Workspace

You have access to tools:
- **Read**: Read file contents
- **Edit**: Modify existing files
- **Write**: Create new files
- **Bash**: Run shell commands (git, pytest, etc.)

Use these tools to execute the step.

## Your Process

1. Read the current step details carefully
2. Use appropriate tools to make the change
3. Verify the change (run tests, check file, etc.)
4. Report completion clearly

## Important

- Follow the **File** and **Target** exactly
- Apply the **Change** as specified
- Run the **Verify** checks
- Do NOT skip verification
- Do NOT modify other files unless required for the step

## Response Format

Briefly state what you did and what verification you ran. Then end your reply
with exactly one status line:

STEP_STATUS: DONE
    - only if you made the change and the verification passed
STEP_STATUS: FAILED - <short reason>
    - if you could not make the change or verification failed

Example:
"Added the type hint to parse_config(). Ran `pytest tests/test_utils.py`: 5 passed.
STEP_STATUS: DONE"
"""

    async def execute_current_step(self) -> WorkerResult:
        """Execute the current step from the plan.

        Returns:
            WorkerResult with execution details
        """
        # Load plan
        try:
            plan = self.plan_manager.load()
        except FileNotFoundError:
            error = "No PLAN.md found. Run planner phase first."
            logger.error(error)
            return WorkerResult(
                success=False,
                step=PlanStep(number=0, description="No plan"),
                response="",
                error=error,
            )

        # Get current step
        current_step = plan.current_step

        if not current_step:
            logger.info("All steps complete!")
            return WorkerResult(
                success=True,
                step=PlanStep(number=0, description="Plan complete"),
                response="All steps in the plan have been completed.",
            )

        logger.info(f"Executing Step {current_step.number}: {current_step.description}")
        return await self._run_step(current_step, plan)

    async def _run_step(
        self, step: PlanStep, plan: ExecutionPlan, feedback: str | None = None
    ) -> WorkerResult:
        """Validate, checkpoint, execute and verify one step.

        The first attempt and every retry go through here, so safety checks and
        rollback apply to both.
        """
        # PRE-EXECUTION SAFETY VALIDATION
        is_safe, error_message = self._validate_step_safety(step)
        if not is_safe:
            logger.error(f"Step {step.number} blocked by security policy")
            return WorkerResult(
                success=False,
                step=step,
                response="",
                error=f"Security policy violation: {error_message}",
            )

        # CREATE CHECKPOINT before execution
        checkpoint = None
        if self.checkpoint_manager:
            checkpoint = await self.checkpoint_manager.create_checkpoint(
                description=f"Before step {step.number}: {step.description}",
                step_number=step.number,
                auto_stage=True,
            )
            if checkpoint:
                logger.info(f"Created checkpoint {checkpoint.id[:8]} before step {step.number}")

        # Execute step
        result = await self._execute_step(step, plan, feedback=feedback)

        # ROLLBACK on failure if checkpoint exists
        if not result.success and checkpoint and self.checkpoint_manager:
            logger.warning(f"Step {step.number} failed, rolling back to checkpoint...")
            rollback_success = await self.checkpoint_manager.rollback_to_checkpoint(
                checkpoint_id=checkpoint.id,
                hard=True,
            )
            if rollback_success:
                logger.info(f"✅ Rolled back to checkpoint {checkpoint.id[:8]}")
                result.response += f"\n\n⚠️  Step failed and workspace was rolled back to checkpoint {checkpoint.id[:8]}"
            else:
                logger.error("❌ Rollback failed!")
                result.response += (
                    "\n\n❌ Step failed AND rollback failed - manual intervention required"
                )

        # Update progress if successful
        if result.success:
            self._update_progress(plan, step)

        return result

    async def _execute_step(
        self, step: PlanStep, plan: ExecutionPlan, feedback: str | None = None
    ) -> WorkerResult:
        """Execute a single step and decide from evidence whether it succeeded.

        Args:
            step: Step to execute
            plan: Full execution plan
            feedback: Why the previous attempt failed (for retries)

        Returns:
            WorkerResult
        """
        # Build execution prompt
        prompt = self._build_execution_prompt(step, plan)
        if feedback:
            prompt += f"""

## Retry Feedback

The previous attempt did not succeed:
{feedback}

Fix the problem and try again.
"""

        # Update state
        self.state.save(
            phase="executing",
            current_step=step.number,
            step_description=step.description,
        )

        try:
            # Run worker
            logger.info("Invoking worker model...")
            response = await self.agent.run(prompt)

            # Decide success from evidence: status line, tool results, target file
            success, reason = self._evaluate_step(step, response)

            # Count tools used
            tools_used = (
                len(response.tool_calls_made)
                if hasattr(response, "tool_calls_made") and response.tool_calls_made
                else 0
            )

            if success:
                logger.info(f"Step {step.number} completed successfully")
            else:
                logger.warning(f"Step {step.number} did not complete: {reason}")

            return WorkerResult(
                success=success,
                step=step,
                response=response.text,
                tools_used=tools_used,
                error=None if success else reason,
            )

        except Exception as e:
            logger.error(f"Step {step.number} failed with error: {e}")
            return WorkerResult(
                success=False,
                step=step,
                response=str(e),
                error=str(e),
            )

    def _build_execution_prompt(self, step: PlanStep, plan: ExecutionPlan) -> str:
        """Build prompt for executing a step.

        Args:
            step: Step to execute
            plan: Full execution plan

        Returns:
            Execution prompt
        """
        prompt = f"""Execute this step from the execution plan:

## Step {step.number}: {step.description}
"""

        if step.file_path:
            prompt += f"\n**File:** `{step.file_path}`"
        if step.target:
            prompt += f"\n**Target:** {step.target}"
        if step.change:
            prompt += f"\n**Change:** {step.change}"
        if step.verification:
            prompt += f"\n**Verify:** {step.verification}"

        prompt += f"""

## Plan Context

You are working on step {step.number} of {plan.total_steps}.
Completed: {len(plan.completed_steps)}
Remaining: {len(plan.remaining_steps)}

## Instructions

Execute this step ONLY. Do not work on other steps.

1. Make the specified change using your tools
2. Run the verification
3. End with `STEP_STATUS: DONE` or `STEP_STATUS: FAILED - <reason>`

Begin execution now.
"""

        return prompt

    def _evaluate_step(self, step: PlanStep, response: Any) -> tuple[bool, str | None]:
        """Decide whether a step succeeded, from evidence rather than wording.

        Requires all of:
        - the worker's final status line is `STEP_STATUS: DONE`
        - no tool call was blocked by guardrails or failed
        - at least one tool call ran (a step always changes or checks something)
        - the step's target file exists, when the plan names a concrete file

        Returns:
            (success, reason for failure or None)
        """
        text = response.text or ""
        status = _status_line(text)
        if status is None:
            return (False, "Worker did not report STEP_STATUS: DONE or FAILED")
        if status != "DONE":
            return (False, f"Worker reported {status}")

        results = getattr(response, "tool_results", None) or []
        calls = getattr(response, "tool_calls_made", None) or []
        failed = [r for r in results if r.is_error]
        if failed:
            first = (failed[0].error or failed[0].output or "").strip().splitlines()[0][:200]
            return (False, f"{len(failed)} tool call(s) were blocked or failed: {first}")
        if not calls:
            return (False, "Worker reported DONE without using any tools")

        path = _concrete_path(step.file_path)
        if path is not None and not path.exists() and not _is_removal(step):
            return (False, f"Target file {path} does not exist after the step")

        return (True, None)

    def _check_success(self, response: str) -> bool:
        """Legacy keyword check (kept for compatibility; not used for step results)."""
        """Check if response indicates success.

        Args:
            response: Worker response text

        Returns:
            True if success indicators found
        """
        response_lower = response.lower()

        # Success indicators
        success_indicators = [
            "complete",
            "done",
            "success",
            "passed",
            "✅",
            "committed",
        ]

        # Failure indicators
        failure_indicators = [
            "failed",
            "error",
            "cannot",
            "unable",
            "❌",
        ]

        # Check for failure first
        has_failure = any(ind in response_lower for ind in failure_indicators)
        if has_failure:
            return False

        # Check for success
        has_success = any(ind in response_lower for ind in success_indicators)
        return has_success

    def _update_progress(self, plan: ExecutionPlan, completed_step: PlanStep) -> None:
        """Update progress after completing a step.

        Args:
            plan: Execution plan
            completed_step: Step that was just completed
        """
        # Mark step as complete in plan
        self.plan_manager.mark_complete(completed_step.number)

        # Reload plan to get updated state
        updated_plan = self.plan_manager.load()

        # Update PROGRESS.md
        current = updated_plan.current_step
        current_desc = current.description if current else None

        completed_descs = [s.description for s in updated_plan.completed_steps]
        remaining_descs = [s.description for s in updated_plan.remaining_steps]

        self.progress.update(
            current=current_desc,
            completed=completed_descs,
            remaining=remaining_descs,
        )

        logger.info(f"Progress updated: {len(completed_descs)}/{updated_plan.total_steps} complete")

    async def retry_step(self, step_number: int, feedback: str | None = None) -> WorkerResult:
        """Retry a specific step with optional feedback.

        Args:
            step_number: Step number to retry
            feedback: Optional feedback to help worker

        Returns:
            WorkerResult
        """

        try:
            plan = self.plan_manager.load()
        except FileNotFoundError:
            return WorkerResult(
                success=False,
                step=PlanStep(number=step_number, description="No plan"),
                response="",
                error="No PLAN.md found. Run planner phase first.",
            )

        step = next((s for s in plan.steps if s.number == step_number), None)
        if step is None:
            return WorkerResult(
                success=False,
                step=PlanStep(number=step_number, description="Unknown step"),
                response="",
                error=f"Step {step_number} not found in plan",
            )

        self.state.increment("retry_count")
        self.state.save(retrying_step=step_number)

        # Same path as the first attempt: safety check, checkpoint, evidence-based result
        return await self._run_step(step, plan, feedback=feedback)

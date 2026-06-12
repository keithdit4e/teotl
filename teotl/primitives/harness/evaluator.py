"""Evaluator phase - Assesses if goals achieved and decides next steps.

The Evaluator uses the same expensive model as the Planner (Sonnet) to:
1. Review completed work
2. Assess if original goals were achieved
3. Decide: COMPLETE (report to user) or CONTINUE (plan next cycle)

This creates a closed-loop system where the agent autonomously works
until goals are fully achieved.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from teotl.core.agent import Agent
from teotl.core.provider import Provider
from teotl.primitives.harness.plan import PlanManager
from teotl.primitives.harness.progress import ProgressTracker
from teotl.primitives.harness.state import StateManager

logger = logging.getLogger(__name__)


@dataclass
class Evaluation:
    """Result of evaluation phase."""

    goals_achieved: bool
    confidence: float  # 0.0 - 1.0
    what_was_done: list[str]
    what_remains: list[str]
    test_status: str  # "passing" | "failing" | "unknown"
    continuation_goals: str | None = None
    completion_summary: str | None = None
    timestamp: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "goals_achieved": self.goals_achieved,
            "confidence": self.confidence,
            "what_was_done": self.what_was_done,
            "what_remains": self.what_remains,
            "test_status": self.test_status,
            "continuation_goals": self.continuation_goals,
            "completion_summary": self.completion_summary,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class SupervisedResult:
    """Result of supervised execution cycle."""

    complete: bool
    cycles_completed: int
    final_evaluation: Evaluation
    completion_report: str | None = None
    reason: str | None = None  # If incomplete, why stopped

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "complete": self.complete,
            "cycles_completed": self.cycles_completed,
            "final_evaluation": self.final_evaluation.to_dict(),
            "completion_report": self.completion_report,
            "reason": self.reason,
        }


@dataclass
class CycleApprovalRequest:
    """Request for user approval to continue to next cycle.

    Presented to user (or approval callback) to decide whether
    autonomous execution should continue to next cycle.
    """

    cycle: int
    evaluation: Evaluation
    estimated_next_cost: float
    cost_summary: dict

    def to_summary_text(self) -> str:
        """Generate human-readable summary for approval prompt.

        Returns:
            Formatted text summary
        """
        lines = []
        lines.append(f"Cycle {self.cycle} Complete - Approval Required")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Confidence: {self.evaluation.confidence * 100:.0f}%")
        lines.append(f"Test Status: {self.evaluation.test_status}")
        lines.append("")

        if self.evaluation.what_was_done:
            lines.append("What was accomplished:")
            for item in self.evaluation.what_was_done:
                lines.append(f"  ✅ {item}")
            lines.append("")

        if self.evaluation.what_remains:
            lines.append("What remains:")
            for item in self.evaluation.what_remains:
                lines.append(f"  ⏳ {item}")
            lines.append("")

        lines.append("Cost Summary:")
        lines.append(f"  Spent so far: ${self.cost_summary.get('total_spent', 0):.2f}")
        lines.append(f"  Estimated next cycle: ${self.estimated_next_cost:.2f}")
        lines.append(f"  Daily remaining: ${self.cost_summary.get('daily_remaining', 0):.2f}")
        lines.append("")

        return "\n".join(lines)


class Evaluator:
    """Evaluates completed work and decides if goals achieved.

    Uses expensive model (Sonnet) to make strategic assessment.

    Usage:
        evaluator = Evaluator(
            agent_id="coding-assistant",
            provider=AnthropicProvider(model="claude-sonnet-4"),
            workspace_dir=agent_dir
        )

        # Evaluate if goals achieved
        evaluation = await evaluator.evaluate(
            original_goals="Improve code quality",
            context="After completing 20 improvements"
        )

        if evaluation.goals_achieved:
            print("Work complete!")
        else:
            print(f"Continue with: {evaluation.continuation_goals}")
    """

    def __init__(
        self,
        agent_id: str,
        provider: Provider,
        workspace_dir: Path | None = None,
        instructions: str | None = None,
    ):
        """Initialize evaluator.

        Args:
            agent_id: Agent identifier
            provider: Provider with expensive model (Sonnet, Opus)
            workspace_dir: Workspace directory
            instructions: Optional custom evaluation instructions
        """
        self.agent_id = agent_id
        self.provider = provider

        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path.home() / ".forge" / "agents" / agent_id

        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize managers
        self.plan_manager = PlanManager(agent_id, self.workspace_dir)
        self.progress = ProgressTracker(agent_id, self.workspace_dir)
        self.state = StateManager(agent_id, self.workspace_dir)

        # Evaluation instructions
        self.instructions = instructions or self._default_instructions()

        # Create evaluator agent
        self.agent = Agent(
            provider=provider,
            instructions=self.instructions,
            session_dir=self.workspace_dir / "sessions" / "evaluator",
        )

        logger.info(f"Evaluator initialized with model: {provider.model}")

    def _default_instructions(self) -> str:
        """Default evaluation instructions."""
        return """You are an expert work evaluator.

Your job is to assess if the original goals have been fully achieved.

## Your Task

Review the completed work and decide:
- ✅ **COMPLETE**: Goals fully achieved, report to user
- 🔄 **CONTINUE**: More work needed, plan next cycle

## Evaluation Criteria

1. **Goal Alignment** - Does completed work address all stated goals?
2. **Quality** - Is the work done well (tests pass, no regressions)?
3. **Completeness** - Are there edge cases or follow-ups needed?
4. **Verification** - Can we verify the goals were met?

## Your Output Format

You must respond with a JSON-like structure:

```
DECISION: COMPLETE | CONTINUE

CONFIDENCE: 0.0-1.0 (how confident in this decision)

WHAT_WAS_DONE:
- Improvement 1
- Improvement 2
- ...

WHAT_REMAINS: (if CONTINUE)
- Issue 1 found during review
- Follow-up task 2
- ...

TEST_STATUS: passing | failing | unknown

COMPLETION_SUMMARY: (if COMPLETE)
Clear summary of what was accomplished for the user

CONTINUATION_GOALS: (if CONTINUE)
Refined goals for the next planning cycle
```

## Important

- Be thorough - check for issues, edge cases, regressions
- If tests are failing, DECISION must be CONTINUE
- If goals partially met, DECISION should be CONTINUE with specific continuation goals
- Only mark COMPLETE if you're confident (>0.8) goals are fully achieved
- CONTINUATION_GOALS should be specific, not just "fix issues"

## Examples

GOOD EVALUATION (Complete):
```
DECISION: COMPLETE
CONFIDENCE: 0.95
WHAT_WAS_DONE:
- Added type hints to 20 functions
- All tests pass (25/25)
- Mypy reports no errors
TEST_STATUS: passing
COMPLETION_SUMMARY: Successfully added type hints to all public functions. Code is now fully typed and all tests pass.
```

GOOD EVALUATION (Continue):
```
DECISION: CONTINUE
CONFIDENCE: 0.9
WHAT_WAS_DONE:
- Added type hints to 20 functions
- Fixed 3 initial bugs
WHAT_REMAINS:
- Mypy found 5 new type errors in edge cases
- Tests for error handling are missing
TEST_STATUS: passing
CONTINUATION_GOALS: Fix the 5 mypy type errors and add error handling tests for edge cases identified during type annotation.
```

BAD EVALUATION:
```
DECISION: COMPLETE
CONFIDENCE: 0.5
TEST_STATUS: failing
```
(Never mark COMPLETE with low confidence or failing tests!)
"""

    async def evaluate(
        self,
        original_goals: str,
        context: str | None = None,
    ) -> Evaluation:
        """Evaluate if goals achieved.

        Args:
            original_goals: The original high-level goals
            context: Optional additional context

        Returns:
            Evaluation with decision and details
        """
        logger.info("Starting evaluation...")

        # Gather evidence
        evidence = self._gather_evidence()

        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(original_goals, evidence, context)

        # Update state
        self.state.save(
            phase="evaluating",
            evaluation_started_at=datetime.now().isoformat(),
        )

        # Run evaluator
        logger.info("Invoking evaluator model...")
        response = await self.agent.run(prompt)

        # Parse evaluation
        evaluation = self._parse_evaluation(response.text)

        # Save evaluation
        self.state.save(
            phase="evaluated",
            evaluation_decision=evaluation.goals_achieved,
            evaluation_confidence=evaluation.confidence,
            evaluation_timestamp=evaluation.timestamp.isoformat() if evaluation.timestamp else None,
        )

        logger.info(
            f"Evaluation complete: {'COMPLETE' if evaluation.goals_achieved else 'CONTINUE'} "
            f"(confidence: {evaluation.confidence:.2f})"
        )

        return evaluation

    def _gather_evidence(self) -> dict:
        """Gather evidence for evaluation.

        Returns:
            Dictionary with plan, progress, state, git info
        """
        evidence = {}

        # Plan
        try:
            plan = self.plan_manager.load()
            evidence["plan"] = {
                "total_steps": plan.total_steps,
                "completed": len(plan.completed_steps),
                "remaining": len(plan.remaining_steps),
                "steps": [
                    {
                        "number": s.number,
                        "description": s.description,
                        "completed": s.completed,
                    }
                    for s in plan.steps
                ],
            }
        except FileNotFoundError:
            evidence["plan"] = None

        # Progress
        try:
            progress = self.progress.read()
            evidence["progress"] = {
                "current": progress.current,
                "completed": progress.completed,
                "remaining": progress.remaining,
                "percentage": progress.completion_percentage,
            }
        except FileNotFoundError:
            evidence["progress"] = None

        # State
        if self.state.exists():
            evidence["state"] = self.state.load()
        else:
            evidence["state"] = None

        return evidence

    def _build_evaluation_prompt(
        self,
        original_goals: str,
        evidence: dict,
        context: str | None = None,
    ) -> str:
        """Build evaluation prompt.

        Args:
            original_goals: Original goals
            evidence: Gathered evidence
            context: Optional context

        Returns:
            Evaluation prompt
        """
        prompt = f"""Evaluate if the original goals have been achieved.

## Original Goals

{original_goals}

## Completed Work

"""

        # Add plan info
        if evidence.get("plan"):
            plan_data = evidence["plan"]
            prompt += f"""
### Execution Plan
- Total steps: {plan_data["total_steps"]}
- Completed: {plan_data["completed"]}
- Remaining: {plan_data["remaining"]}

Completed steps:
"""
            for step in plan_data["steps"]:
                if step["completed"]:
                    prompt += f"- ✅ Step {step['number']}: {step['description']}\n"

        # Add progress info
        if evidence.get("progress"):
            progress_data = evidence["progress"]
            prompt += f"""
### Progress
- Completion: {progress_data["percentage"]:.1f}%
- Completed tasks: {len(progress_data["completed"])}
"""

        # Add context
        if context:
            prompt += f"""
### Additional Context

{context}
"""

        prompt += """

## Your Task

Evaluate this work and decide: COMPLETE or CONTINUE?

Provide your evaluation in the format specified in your instructions.
"""

        return prompt

    def _parse_evaluation(self, response: str) -> Evaluation:
        """Parse evaluator response.

        Args:
            response: Raw evaluator output

        Returns:
            Parsed Evaluation
        """
        lines = response.split("\n")

        # Default values
        decision = "CONTINUE"
        confidence = 0.5
        what_was_done = []
        what_remains = []
        test_status = "unknown"
        continuation_goals = None
        completion_summary = None

        current_section = None

        for line in lines:
            line = line.strip()

            # Parse decision
            if line.startswith("DECISION:"):
                decision = line.replace("DECISION:", "").strip().upper()

            # Parse confidence
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    confidence = 0.5

            # Parse test status
            elif line.startswith("TEST_STATUS:"):
                test_status = line.replace("TEST_STATUS:", "").strip().lower()

            # Parse completion summary
            elif line.startswith("COMPLETION_SUMMARY:"):
                completion_summary = line.replace("COMPLETION_SUMMARY:", "").strip()
                current_section = "summary"

            # Parse continuation goals
            elif line.startswith("CONTINUATION_GOALS:"):
                continuation_goals = line.replace("CONTINUATION_GOALS:", "").strip()
                current_section = "continuation"

            # Parse sections
            elif line.startswith("WHAT_WAS_DONE:"):
                current_section = "done"
            elif line.startswith("WHAT_REMAINS:"):
                current_section = "remains"

            # Parse list items
            elif line.startswith("-") or line.startswith("*"):
                item = line.lstrip("-*").strip()
                if current_section == "done":
                    what_was_done.append(item)
                elif current_section == "remains":
                    what_remains.append(item)

            # Continue multi-line sections
            elif current_section == "summary" and line:
                completion_summary += " " + line
            elif current_section == "continuation" and line:
                continuation_goals += " " + line

        # Determine if goals achieved
        goals_achieved = decision == "COMPLETE"

        return Evaluation(
            goals_achieved=goals_achieved,
            confidence=confidence,
            what_was_done=what_was_done,
            what_remains=what_remains,
            test_status=test_status,
            continuation_goals=continuation_goals,
            completion_summary=completion_summary,
            timestamp=datetime.now(),
        )

    async def generate_completion_report(
        self,
        original_goals: str,
        evaluation: Evaluation,
        cycles_completed: int,
    ) -> str:
        """Generate user-facing completion report.

        Args:
            original_goals: Original goals
            evaluation: Final evaluation
            cycles_completed: Number of cycles completed

        Returns:
            Formatted completion report
        """
        report = f"""# Work Completion Report

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Cycles:** {cycles_completed}
**Status:** ✅ COMPLETE

---

## Original Goals

{original_goals}

---

## What Was Accomplished

"""

        for item in evaluation.what_was_done:
            report += f"- ✅ {item}\n"

        report += f"""

---

## Summary

{evaluation.completion_summary or "Goals have been achieved successfully."}

---

## Verification

- **Tests:** {evaluation.test_status}
- **Confidence:** {evaluation.confidence * 100:.0f}%

"""

        # Add artifacts info
        report += """---

## Artifacts

Check these files for details:
- `PLAN.md` - Execution plan
- `PROGRESS.md` - Completed tasks
- `STATE.json` - Final state
- `DECISION_LOG.md` - Decision history

"""

        return report

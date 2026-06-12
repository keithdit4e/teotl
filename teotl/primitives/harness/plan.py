"""Execution plan data structures and parser.

Defines the format for PLAN.md and provides parsing/generation utilities.
Plans are created by the Planner (expensive model) and executed by Workers (cheap model).
"""

import contextlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class PlanStep:
    """A single atomic step in an execution plan.

    Each step should be:
    - Specific: Exactly what file/function/line to change
    - Testable: Clear success criteria
    - Independent: Can fail without blocking others
    - Atomic: One logical change (not bundled)
    """

    number: int
    description: str
    file_path: str | None = None
    target: str | None = None  # function name, line number, or section
    change: str | None = None  # What to change
    verification: str | None = None  # How to verify success
    completed: bool = False
    skipped: bool = False
    skip_reason: str | None = None

    def to_markdown(self) -> str:
        """Convert step to markdown format."""
        status = "✓" if self.completed else ("⊘" if self.skipped else "")
        header = f"## Step {self.number}: {self.description} {status}".strip()

        parts = [header, ""]

        if self.file_path:
            parts.append(f"**File:** `{self.file_path}`")
        if self.target:
            parts.append(f"**Target:** {self.target}")
        if self.change:
            parts.append(f"**Change:** {self.change}")
        if self.verification:
            parts.append(f"**Verify:** {self.verification}")
        if self.skipped and self.skip_reason:
            parts.append(f"**Skipped:** {self.skip_reason}")

        parts.append("")  # Blank line after step
        return "\n".join(parts)

    @classmethod
    def from_markdown(cls, text: str, number: int) -> "PlanStep":
        """Parse step from markdown section."""
        lines = text.strip().split("\n")

        # First line is the description
        description = lines[0].replace(f"## Step {number}:", "").strip()

        # Remove status markers
        for marker in ["✓", "⊘"]:
            description = description.replace(marker, "").strip()

        # Parse metadata
        file_path = None
        target = None
        change = None
        verification = None
        completed = "✓" in lines[0]
        skipped = "⊘" in lines[0]
        skip_reason = None

        for line in lines[1:]:
            line = line.strip()
            if line.startswith("**File:**"):
                file_path = line.replace("**File:**", "").strip().strip("`")
            elif line.startswith("**Target:**"):
                target = line.replace("**Target:**", "").strip()
            elif line.startswith("**Change:**"):
                change = line.replace("**Change:**", "").strip()
            elif line.startswith("**Verify:**"):
                verification = line.replace("**Verify:**", "").strip()
            elif line.startswith("**Skipped:**"):
                skip_reason = line.replace("**Skipped:**", "").strip()

        return cls(
            number=number,
            description=description,
            file_path=file_path,
            target=target,
            change=change,
            verification=verification,
            completed=completed,
            skipped=skipped,
            skip_reason=skip_reason,
        )


@dataclass
class ExecutionPlan:
    """Complete execution plan with metadata and steps."""

    goals: str
    steps: list[PlanStep]
    created_at: datetime
    created_by: str  # Model that created the plan
    total_steps: int

    @property
    def completed_steps(self) -> list[PlanStep]:
        """Get completed steps."""
        return [s for s in self.steps if s.completed]

    @property
    def remaining_steps(self) -> list[PlanStep]:
        """Get remaining (not completed, not skipped) steps."""
        return [s for s in self.steps if not s.completed and not s.skipped]

    @property
    def current_step(self) -> PlanStep | None:
        """Get the next step to work on."""
        remaining = self.remaining_steps
        return remaining[0] if remaining else None

    @property
    def is_complete(self) -> bool:
        """Check if all steps are done."""
        return len(self.remaining_steps) == 0

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_steps == 0:
            return 100.0
        return (len(self.completed_steps) / self.total_steps) * 100

    def to_markdown(self) -> str:
        """Convert plan to PLAN.md format."""
        content = f"""# Execution Plan

**Created:** {self.created_at.isoformat()}
**Model:** {self.created_by}
**Total Steps:** {self.total_steps}
**Completed:** {len(self.completed_steps)}
**Remaining:** {len(self.remaining_steps)}
**Progress:** {self.completion_percentage:.1f}%

---

## Goals

{self.goals}

---

## Steps

"""

        for step in self.steps:
            content += step.to_markdown() + "\n"

        return content


class PlanManager:
    """Manages PLAN.md creation, parsing, and updates."""

    def __init__(self, agent_id: str, workspace_dir: Path | None = None):
        """Initialize plan manager.

        Args:
            agent_id: Agent identifier
            workspace_dir: Workspace directory (defaults to ~/.forge/agents/{agent_id})
        """
        self.agent_id = agent_id

        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path.home() / ".forge" / "agents" / agent_id

        self.path = self.workspace_dir / "PLAN.md"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def create(self, goals: str, steps: list[PlanStep], created_by: str) -> ExecutionPlan:
        """Create new execution plan.

        Args:
            goals: High-level goals
            steps: List of plan steps
            created_by: Model identifier that created the plan

        Returns:
            ExecutionPlan instance
        """
        plan = ExecutionPlan(
            goals=goals,
            steps=steps,
            created_at=datetime.now(),
            created_by=created_by,
            total_steps=len(steps),
        )

        # Write to PLAN.md
        self.path.write_text(plan.to_markdown())

        return plan

    def load(self) -> ExecutionPlan:
        """Load plan from PLAN.md.

        Returns:
            ExecutionPlan instance

        Raises:
            FileNotFoundError: If PLAN.md doesn't exist
        """
        if not self.path.exists():
            raise FileNotFoundError(
                f"PLAN.md not found at {self.path}. Run planner phase first to create a plan."
            )

        content = self.path.read_text()
        return self._parse_plan(content)

    def _parse_plan(self, content: str) -> ExecutionPlan:
        """Parse PLAN.md markdown into ExecutionPlan.

        Args:
            content: Raw markdown content

        Returns:
            Parsed ExecutionPlan
        """
        lines = content.split("\n")

        # Parse metadata
        created_at = datetime.now()
        created_by = "unknown"
        total_steps = 0
        goals = ""

        in_goals = False
        in_steps = False
        current_step_lines = []
        steps = []
        step_number = 0

        for line in lines:
            stripped = line.strip()

            # Parse metadata
            if stripped.startswith("**Created:**"):
                timestamp_str = stripped.replace("**Created:**", "").strip()
                with contextlib.suppress(ValueError):
                    created_at = datetime.fromisoformat(timestamp_str)
            elif stripped.startswith("**Model:**"):
                created_by = stripped.replace("**Model:**", "").strip()
            elif stripped.startswith("**Total Steps:**"):
                with contextlib.suppress(ValueError):
                    total_steps = int(stripped.replace("**Total Steps:**", "").strip())

            # Parse goals section
            if stripped == "## Goals":
                in_goals = True
                continue
            elif in_goals and stripped == "---":
                in_goals = False
                continue
            elif in_goals and stripped:
                goals += line + "\n"

            # Parse steps section
            if stripped == "## Steps":
                in_steps = True
                continue

            if in_steps:
                # Detect step start
                if stripped.startswith("## Step "):
                    # Save previous step if exists
                    if current_step_lines:
                        step_text = "\n".join(current_step_lines)
                        step = PlanStep.from_markdown(step_text, step_number)
                        steps.append(step)

                    # Start new step
                    step_number += 1
                    current_step_lines = [line]
                elif current_step_lines:
                    # Continue current step
                    current_step_lines.append(line)

        # Save last step
        if current_step_lines:
            step_text = "\n".join(current_step_lines)
            step = PlanStep.from_markdown(step_text, step_number)
            steps.append(step)

        return ExecutionPlan(
            goals=goals.strip(),
            steps=steps,
            created_at=created_at,
            created_by=created_by,
            total_steps=total_steps or len(steps),
        )

    def update_step(
        self,
        step_number: int,
        completed: bool = False,
        skipped: bool = False,
        skip_reason: str | None = None,
    ) -> None:
        """Update step status.

        Args:
            step_number: Step number to update
            completed: Mark as completed
            skipped: Mark as skipped
            skip_reason: Reason for skipping
        """
        plan = self.load()

        # Find and update step
        for step in plan.steps:
            if step.number == step_number:
                step.completed = completed
                step.skipped = skipped
                step.skip_reason = skip_reason
                break

        # Write updated plan
        self.path.write_text(plan.to_markdown())

    def mark_complete(self, step_number: int) -> None:
        """Mark step as complete."""
        self.update_step(step_number, completed=True)

    def mark_skipped(self, step_number: int, reason: str) -> None:
        """Mark step as skipped."""
        self.update_step(step_number, skipped=True, skip_reason=reason)

    def exists(self) -> bool:
        """Check if PLAN.md exists."""
        return self.path.exists()

    def clear(self) -> None:
        """Remove PLAN.md."""
        if self.path.exists():
            self.path.unlink()

    def archive(self, suffix: str | None = None) -> Path:
        """Archive PLAN.md to timestamped file."""
        if not self.exists():
            raise FileNotFoundError("No plan to archive")

        if suffix:
            archive_name = f"PLAN_{suffix}.md"
        else:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            archive_name = f"PLAN_{timestamp}.md"

        archive_path = self.workspace_dir / archive_name
        archive_path.write_text(self.path.read_text())

        return archive_path

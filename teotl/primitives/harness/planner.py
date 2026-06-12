"""Planner phase - Creates execution plans using expensive models.

The Planner analyzes high-level goals and creates detailed, atomic execution plans
that Workers (cheap models) can reliably execute.

Key responsibilities:
- Strategic thinking and architectural decisions
- Breaking down goals into atomic steps
- Ordering steps by dependencies
- Defining verification criteria
"""

import logging
import re
from pathlib import Path

from teotl.core.agent import Agent
from teotl.core.provider import Provider
from teotl.primitives.harness.plan import ExecutionPlan, PlanManager, PlanStep
from teotl.primitives.harness.state import StateManager

logger = logging.getLogger(__name__)


class Planner:
    """Creates execution plans using expensive models (Sonnet, Opus).

    The Planner runs ONCE at the start to create a detailed plan.
    Workers then execute the plan step-by-step.

    Usage:
        planner = Planner(
            agent_id="coding-assistant",
            provider=AnthropicProvider(model="claude-sonnet-4"),
            workspace_dir=agent_dir
        )

        # Create plan from goals
        plan = await planner.create_plan(goals=goals_content)

        # Plan is saved to PLAN.md
        # Workers can now execute it
    """

    def __init__(
        self,
        agent_id: str,
        provider: Provider,
        workspace_dir: Path | None = None,
        instructions: str | None = None,
        # Harness components (optional, shared from orchestrator)
        cost_tracker=None,
        audit_logger=None,
        state_manager=None,
    ):
        """Initialize planner.

        Args:
            agent_id: Agent identifier
            provider: Provider with expensive model (Sonnet, Opus)
            workspace_dir: Workspace directory
            instructions: Optional custom planning instructions
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
        self.state = state_manager or StateManager(agent_id, self.workspace_dir)

        # Planning instructions
        self.instructions = instructions or self._default_instructions()

        # Create planner agent with harness support
        self.agent = Agent(
            provider=provider,
            instructions=self.instructions,
            session_dir=self.workspace_dir / "sessions" / "planner",
            # Pass harness components to agent
            cost_tracker=cost_tracker,
            audit_logger=audit_logger,
            state_manager=self.state,
        )

        logger.info(f"Planner initialized with model: {provider.model}")

    def _default_instructions(self) -> str:
        """Default planning instructions."""
        return """You are an expert execution planner.

Your job is to analyze high-level goals and create detailed, atomic execution plans.

## Your Task

Read the GOALS provided by the user and create a detailed execution plan.

## Plan Format

Create a plan with 10-20 atomic steps. Each step MUST follow this format:

## Step N: [Brief description]

**File:** `path/to/file.py`
**Target:** function_name or line number or section
**Change:** Specific change to make
**Verify:** How to verify success

## Guidelines

1. **Atomic Steps** - Each step is ONE logical change
   - Good: "Add type hint to parse_config() function"
   - Bad: "Add type hints to all functions in utils.py"

2. **Specific** - Exactly what file/function/line to change
   - Good: "Fix null check in parser.py line 45"
   - Bad: "Fix bugs in parser module"

3. **Testable** - Clear success criteria
   - Good: "Verify: Tests pass, mypy clean, no new warnings"
   - Bad: "Verify: Code looks better"

4. **Independent** - Can fail without blocking others
   - Steps should be loosely coupled
   - Don't create tight dependencies

5. **Ordered** - Consider dependencies
   - Tests should be written after implementation
   - Documentation after implementation

## Examples

GOOD PLAN:
```
## Step 1: Add type hint to utils.py::parse_config()

**File:** `forge/utils.py`
**Target:** parse_config function (line 23)
**Change:** Change signature from `def parse_config(data)` to `def parse_config(data: dict[str, Any]) -> Config`
**Verify:** Tests pass, mypy clean on utils.py

## Step 2: Add type hint to utils.py::validate_input()

**File:** `forge/utils.py`
**Target:** validate_input function (line 45)
**Change:** Change signature from `def validate_input(user_input)` to `def validate_input(user_input: str) -> bool`
**Verify:** Tests pass, mypy clean on utils.py
```

BAD PLAN:
```
## Step 1: Improve code quality

**Change:** Make the code better
**Verify:** Code is improved
```

## Output Format

Respond with ONLY the plan in markdown format. No introduction, no explanation, just the steps.

Start directly with:
## Step 1: ...

Do NOT include:
- "Here's the plan..."
- "I'll create..."
- "Let me break this down..."

Just output the steps directly.
"""

    async def create_plan(
        self,
        goals: str,
        context: str | None = None,
    ) -> ExecutionPlan:
        """Create execution plan from goals.

        Args:
            goals: High-level goals to achieve
            context: Optional additional context (codebase info, constraints, etc.)

        Returns:
            ExecutionPlan saved to PLAN.md
        """
        logger.info("Starting plan creation...")

        # Build planning prompt
        prompt = self._build_planning_prompt(goals, context)

        # Save planning state
        self.state.save(
            phase="planning",
            planning_started_at=str(logger.info),
        )

        # Run planner
        logger.info("Invoking planner model...")
        response = await self.agent.run(prompt)

        # Parse steps from response
        steps = self._parse_steps(response.text)

        logger.info(f"Plan created with {len(steps)} steps")

        # Create plan
        plan = self.plan_manager.create(
            goals=goals,
            steps=steps,
            created_by=self.provider.model,
        )

        # Update state
        self.state.save(
            phase="planned",
            plan_created_at=plan.created_at.isoformat(),
            total_steps=len(steps),
        )

        logger.info(f"PLAN.md saved to {self.plan_manager.path}")

        return plan

    def _build_planning_prompt(self, goals: str, context: str | None = None) -> str:
        """Build prompt for planner."""
        prompt = f"""Create an execution plan for these goals:

{goals}
"""

        if context:
            prompt += f"""
## Additional Context

{context}
"""

        prompt += """
Create a detailed execution plan with 10-20 atomic steps following the format in your instructions.

Output ONLY the steps in markdown format. Start directly with:
## Step 1: ...
"""

        return prompt

    def _parse_steps(self, plan_text: str) -> list[PlanStep]:
        """Parse steps from planner response.

        Args:
            plan_text: Raw planner output

        Returns:
            List of PlanStep objects
        """
        steps = []

        # Split by step headers
        step_pattern = r"## Step (\d+):"
        parts = re.split(step_pattern, plan_text)

        # parts[0] is text before first step (ignore)
        # parts[1] = number, parts[2] = content, parts[3] = number, parts[4] = content, ...
        for i in range(1, len(parts), 2):
            if i + 1 >= len(parts):
                break

            step_number = int(parts[i])
            step_content = parts[i + 1].strip()

            # Parse step
            step = self._parse_single_step(step_number, step_content)
            steps.append(step)

        return steps

    def _parse_single_step(self, number: int, content: str) -> PlanStep:
        """Parse a single step.

        Args:
            number: Step number
            content: Step content (everything after "## Step N:")

        Returns:
            PlanStep object
        """
        lines = content.split("\n")

        # First line is description
        description = lines[0].strip()

        # Parse metadata
        file_path = None
        target = None
        change = None
        verification = None

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

        return PlanStep(
            number=number,
            description=description,
            file_path=file_path,
            target=target,
            change=change,
            verification=verification,
        )

    async def refine_plan(
        self,
        feedback: str,
    ) -> ExecutionPlan:
        """Refine existing plan based on feedback.

        Args:
            feedback: Feedback on current plan

        Returns:
            Updated ExecutionPlan
        """
        # Load current plan
        current_plan = self.plan_manager.load()

        # Archive current plan
        self.plan_manager.archive(suffix="before_refinement")

        # Build refinement prompt
        prompt = f"""The current execution plan needs refinement.

## Current Plan

{current_plan.to_markdown()}

## Feedback

{feedback}

Create an improved execution plan that addresses this feedback.

Output ONLY the revised steps in markdown format. Start directly with:
## Step 1: ...
"""

        # Run planner
        response = await self.agent.run(prompt)

        # Parse steps
        steps = self._parse_steps(response.text)

        # Create new plan
        plan = self.plan_manager.create(
            goals=current_plan.goals,
            steps=steps,
            created_by=self.provider.model,
        )

        logger.info(f"Plan refined with {len(steps)} steps")

        return plan

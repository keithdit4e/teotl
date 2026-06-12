"""Progress tracking via PROGRESS.md artifact.

Provides durable progress state that persists across agent executions.
Agent reads PROGRESS.md to understand current task, completed work, and
remaining work - not conversation history.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ProgressState:
    """Parsed progress state from PROGRESS.md."""

    current: str | None
    completed: list[str]
    remaining: list[str]
    updated_at: datetime
    is_complete: bool

    @property
    def age_minutes(self) -> float:
        """Minutes since last update."""
        delta = datetime.now() - self.updated_at
        return delta.total_seconds() / 60

    @property
    def total_tasks(self) -> int:
        """Total number of tasks (completed + remaining)."""
        return len(self.completed) + len(self.remaining)

    @property
    def completion_percentage(self) -> float:
        """Percentage of tasks completed."""
        if self.total_tasks == 0:
            return 100.0
        return (len(self.completed) / self.total_tasks) * 100


class ProgressTracker:
    """Manages PROGRESS.md artifact for durable progress tracking.

    Usage:
        tracker = ProgressTracker(agent_id="coding-assistant")

        # Update progress
        tracker.update(
            current="Add type hints to utils.py",
            completed=["Fix bug in parser.py", "Add tests for validator.py"],
            remaining=["Refactor database.py", "Update documentation"]
        )

        # Read progress
        state = tracker.read()
        print(f"Current: {state.current}")
        print(f"Progress: {state.completion_percentage}%")
    """

    def __init__(self, agent_id: str, workspace_dir: Path | None = None):
        """Initialize progress tracker.

        Args:
            agent_id: Agent identifier
            workspace_dir: Optional workspace directory (defaults to ~/.forge/agents/{agent_id})
        """
        self.agent_id = agent_id

        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path.home() / ".forge" / "agents" / agent_id

        self.path = self.workspace_dir / "PROGRESS.md"

        # Ensure workspace directory exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def update(
        self,
        current: str | None = None,
        completed: list[str] | None = None,
        remaining: list[str] | None = None,
    ) -> None:
        """Update PROGRESS.md with current state.

        Args:
            current: Current task being worked on (None if complete)
            completed: List of completed tasks
            remaining: List of remaining tasks
        """
        completed = completed or []
        remaining = remaining or []

        # Determine if work is complete
        is_complete = current is None and len(remaining) == 0

        # Build markdown content
        timestamp = datetime.now().isoformat()
        content = f"""# Progress

Last updated: {timestamp}

"""

        if is_complete:
            content += f"""## Status: ✅ COMPLETE

All tasks finished! {len(completed)} tasks completed.

"""
        else:
            content += f"""## Current Task

{current if current else "Starting..."}

"""

        if completed:
            content += f"""## Completed ({len(completed)})

"""
            for task in completed:
                content += f"- ✅ {task}\n"
            content += "\n"

        if remaining:
            content += f"""## Remaining ({len(remaining)})

"""
            for task in remaining:
                content += f"- ⏳ {task}\n"
            content += "\n"

        if not is_complete and (completed or remaining):
            total = len(completed) + len(remaining)
            percentage = (len(completed) / total * 100) if total > 0 else 0
            content += f"""## Progress Summary

- Total tasks: {total}
- Completed: {len(completed)}
- Remaining: {len(remaining)}
- Progress: {percentage:.1f}%

"""

        # Write to file
        self.path.write_text(content)

    def read(self) -> ProgressState:
        """Read and parse PROGRESS.md.

        Returns:
            ProgressState with parsed progress information

        Raises:
            FileNotFoundError: If PROGRESS.md doesn't exist
        """
        if not self.path.exists():
            raise FileNotFoundError(
                f"PROGRESS.md not found at {self.path}. Call update() first to initialize."
            )

        content = self.path.read_text()
        return self._parse_progress(content)

    def _parse_progress(self, content: str) -> ProgressState:
        """Parse PROGRESS.md markdown into structured state.

        Args:
            content: Raw markdown content

        Returns:
            Parsed ProgressState
        """
        lines = content.split("\n")

        current = None
        completed = []
        remaining = []
        updated_at = datetime.now()
        is_complete = False

        # Parse sections
        current_section = None

        for line in lines:
            line = line.strip()

            # Parse timestamp
            if line.startswith("Last updated:"):
                timestamp_str = line.replace("Last updated:", "").strip()
                try:
                    updated_at = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    pass  # Use default if parsing fails

            # Check for completion
            if "Status: ✅ COMPLETE" in line or "Status: COMPLETE" in line:
                is_complete = True

            # Track sections
            if line.startswith("## Current Task"):
                current_section = "current"
                continue
            elif line.startswith("## Completed"):
                current_section = "completed"
                continue
            elif line.startswith("## Remaining"):
                current_section = "remaining"
                continue
            elif line.startswith("##"):
                current_section = None
                continue

            # Parse task items
            if current_section == "current" and line and not line.startswith("#"):
                if current is None:  # Take first non-empty line
                    current = line
            elif current_section == "completed" and line.startswith("-"):
                task = line.lstrip("- ✅").strip()
                if task:
                    completed.append(task)
            elif current_section == "remaining" and line.startswith("-"):
                task = line.lstrip("- ⏳").strip()
                if task:
                    remaining.append(task)

        return ProgressState(
            current=current,
            completed=completed,
            remaining=remaining,
            updated_at=updated_at,
            is_complete=is_complete,
        )

    def exists(self) -> bool:
        """Check if PROGRESS.md exists."""
        return self.path.exists()

    def clear(self) -> None:
        """Clear progress by removing PROGRESS.md."""
        if self.path.exists():
            self.path.unlink()

    def mark_complete(self) -> None:
        """Mark all work as complete."""
        state = self.read() if self.exists() else None

        completed = state.completed if state else []
        if state and state.current:
            completed.append(state.current)
        if state and state.remaining:
            completed.extend(state.remaining)

        self.update(current=None, completed=completed, remaining=[])

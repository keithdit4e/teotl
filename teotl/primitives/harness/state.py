"""State management via STATE.json artifact.

Provides durable structured state that persists across agent executions.
Use for variables, flags, checkpoints, counters, and other state that needs
to survive context resets.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


class AgentState(BaseModel):
    """Pydantic model for agent state validation.

    Defines the schema for STATE.json to prevent corruption and
    ensure type safety.
    """

    model_config = ConfigDict(extra="allow")  # Allow additional fields not defined in schema

    # Metadata (required) - no leading underscores for Pydantic v2
    agent_id: str = Field(..., description="Agent identifier")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")
    version: str = Field(default="1.0", description="State schema version")

    # Execution tracking
    phase: str | None = Field(default=None, description="Current execution phase")
    current_turn: int | None = Field(default=0, description="Current turn number")
    current_cycle: int | None = Field(default=None, description="Current cycle number")
    current_step: int | None = Field(default=None, description="Current step number")

    # Health metrics
    consecutive_errors: int | None = Field(default=0, description="Consecutive error count")
    last_error: str | None = Field(default=None, description="Last error message")
    last_progress_turn: int | None = Field(default=0, description="Turn of last progress")

    # Execution state
    halted: bool | None = Field(default=False, description="Whether execution is halted")
    halt_reason: str | None = Field(default=None, description="Reason for halt")
    halt_turn: int | None = Field(default=None, description="Turn when halted")

    # Retry tracking
    retry_count: int | None = Field(default=0, description="Retry attempt count")
    retrying_step: int | None = Field(default=None, description="Step being retried")

    # Timing
    execution_start_time: str | None = Field(default=None, description="Execution start time")
    last_heartbeat_time: str | None = Field(default=None, description="Last heartbeat time")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentState":
        """Create AgentState from dictionary with validation.

        Args:
            data: State dictionary

        Returns:
            Validated AgentState instance

        Raises:
            ValidationError: If data doesn't match schema
        """
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            State as dictionary
        """
        return self.model_dump()


class StateManager:
    """Manages STATE.json artifact for durable state persistence.

    Usage:
        state = StateManager(agent_id="crm-sync")

        # Save state variables
        state.save(
            last_sync_cursor="2024-03-27T10:30:00Z",
            records_processed=147,
            api_credentials_valid=True,
            phase="syncing_contacts"
        )

        # Read state
        cursor = state.get("last_sync_cursor")
        phase = state.get("phase", default="initializing")

        # Update specific values
        state.update(records_processed=148)

        # Check if state exists
        if state.exists():
            print("Resuming from previous state")

    State is useful for:
    - Sync cursors (last processed record ID)
    - Phase tracking (initializing → executing → verifying)
    - Counters (consecutive_failures, records_processed)
    - Flags (credentials_valid, tests_passed)
    - Checkpoints (last_successful_commit, backup_created_at)
    """

    def __init__(
        self,
        agent_id: str,
        workspace_dir: Path | None = None,
        enable_validation: bool = True,
    ):
        """Initialize state manager.

        Args:
            agent_id: Agent identifier
            workspace_dir: Optional workspace directory (defaults to ~/.forge/agents/{agent_id})
            enable_validation: Enable Pydantic validation (default: True)
        """
        self.agent_id = agent_id
        self.enable_validation = enable_validation

        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path.home() / ".forge" / "agents" / agent_id

        self.path = self.workspace_dir / "STATE.json"

        # Ensure workspace directory exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def save(self, **kwargs: Any) -> None:
        """Save state variables (merges with existing state).

        Args:
            **kwargs: State variables to save

        Example:
            state.save(
                phase="testing",
                tests_passed=4,
                last_error=None
            )

        Raises:
            ValidationError: If state doesn't match schema (when validation enabled)
        """
        # Load existing state
        current_state = self.load()

        # Merge with new values
        current_state.update(kwargs)

        # Add metadata (no leading underscores for Pydantic v2)
        current_state["updated_at"] = datetime.now().isoformat()
        current_state["agent_id"] = self.agent_id

        # Validate if enabled
        if self.enable_validation:
            try:
                validated_state = AgentState.from_dict(current_state)
                current_state = validated_state.to_dict()
            except ValidationError as e:
                logger.error(f"State validation failed: {e}")
                # Log validation error but still save (for backward compatibility)
                # In strict mode, we could raise here
                logger.warning("Saving state despite validation errors")

        # Write to file
        self.path.write_text(json.dumps(current_state, indent=2, default=str))

    def load(self) -> dict[str, Any]:
        """Load current state with optional validation.

        Returns:
            Dictionary of state variables (empty dict if STATE.json doesn't exist)

        Note:
            Validation errors are logged but don't prevent loading (backward compatibility)
        """
        if not self.path.exists():
            return {}

        try:
            content = self.path.read_text()
            state_data = json.loads(content)

            # Validate if enabled
            if self.enable_validation:
                try:
                    validated_state = AgentState.from_dict(state_data)
                    # Return validated state as dict
                    return validated_state.to_dict()
                except ValidationError as e:
                    logger.warning(f"State validation failed on load: {e}")
                    # Return unvalidated state (backward compatibility)
                    logger.warning("Returning unvalidated state")
                    return state_data

            return state_data

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to load state: {e}")
            # Corrupted state file, return empty
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a specific state variable.

        Args:
            key: State variable name
            default: Default value if key doesn't exist

        Returns:
            State variable value or default
        """
        state = self.load()
        return state.get(key, default)

    def update(self, **kwargs: Any) -> None:
        """Alias for save() - updates state variables.

        Args:
            **kwargs: State variables to update
        """
        self.save(**kwargs)

    def increment(self, key: str, by: int = 1) -> int:
        """Increment a counter variable.

        Args:
            key: Counter variable name
            by: Amount to increment (default: 1)

        Returns:
            New counter value

        Example:
            state.increment("consecutive_failures")  # 0 → 1
            state.increment("records_processed", by=10)  # 147 → 157
        """
        current_value = self.get(key, 0)
        new_value = current_value + by
        self.save(**{key: new_value})
        return new_value

    def decrement(self, key: str, by: int = 1) -> int:
        """Decrement a counter variable.

        Args:
            key: Counter variable name
            by: Amount to decrement (default: 1)

        Returns:
            New counter value
        """
        return self.increment(key, by=-by)

    def reset_counter(self, key: str) -> None:
        """Reset a counter to 0.

        Args:
            key: Counter variable name
        """
        self.save(**{key: 0})

    def set_flag(self, key: str, value: bool) -> None:
        """Set a boolean flag.

        Args:
            key: Flag name
            value: Flag value

        Example:
            state.set_flag("credentials_valid", True)
            state.set_flag("tests_passed", False)
        """
        self.save(**{key: value})

    def get_flag(self, key: str, default: bool = False) -> bool:
        """Get a boolean flag.

        Args:
            key: Flag name
            default: Default value if flag doesn't exist

        Returns:
            Flag value or default
        """
        return self.get(key, default)

    def exists(self) -> bool:
        """Check if STATE.json exists."""
        return self.path.exists()

    def clear(self) -> None:
        """Clear all state by removing STATE.json."""
        if self.path.exists():
            self.path.unlink()

    def archive(self, suffix: str | None = None) -> Path:
        """Archive current state to a timestamped file.

        Args:
            suffix: Optional suffix for archive filename

        Returns:
            Path to archived state file

        Example:
            state.archive()  # STATE_2024-03-27T10-30-00.json
            state.archive("before_migration")  # STATE_before_migration.json
        """
        if not self.exists():
            raise FileNotFoundError("No state to archive")

        if suffix:
            archive_name = f"STATE_{suffix}.json"
        else:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            archive_name = f"STATE_{timestamp}.json"

        archive_path = self.workspace_dir / archive_name
        archive_path.write_text(self.path.read_text())

        return archive_path

    def restore(self, archive_path: Path) -> None:
        """Restore state from an archived file.

        Args:
            archive_path: Path to archived state file
        """
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        self.path.write_text(archive_path.read_text())

    @property
    def updated_at(self) -> datetime | None:
        """Get last update timestamp."""
        state = self.load()
        timestamp_str = state.get("updated_at")

        if timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str)
            except ValueError:
                pass

        return None

    @property
    def age_minutes(self) -> float | None:
        """Get minutes since last update."""
        updated = self.updated_at
        if updated:
            delta = datetime.now() - updated
            return delta.total_seconds() / 60
        return None

    def __repr__(self) -> str:
        """String representation."""
        state = self.load()
        num_vars = len([k for k in state if not k.startswith("_")])
        return f"StateManager(agent_id='{self.agent_id}', vars={num_vars})"

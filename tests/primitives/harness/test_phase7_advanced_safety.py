"""Integration tests for Phase 7 advanced safety features.

Tests the following Phase 7 capabilities:
1. Git-based checkpoint and rollback system
2. Comprehensive audit trail logging
3. Pydantic state validation
"""

import json

import pytest

from teotl.primitives.harness.audit import AuditLogger
from teotl.primitives.harness.checkpoint import CheckpointManager
from teotl.primitives.harness.state import AgentState, StateManager


class TestCheckpointManager:
    """Test git-based checkpoint and rollback system."""

    def test_checkpoint_initialization(self, tmp_path):
        """Test CheckpointManager initialization."""
        # Without git repo, auto_checkpoint should be disabled
        manager = CheckpointManager(
            workspace_dir=tmp_path,
            auto_checkpoint_enabled=True,
        )

        assert manager.workspace_dir == tmp_path
        # Auto-checkpoint gets disabled when no git repo exists (expected behavior)
        assert manager.auto_checkpoint_enabled is False
        assert manager.checkpoint_prefix == "teotl-checkpoint"

    def test_workspace_clean_check(self, tmp_path):
        """Test workspace clean status check."""
        # Create a git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

        manager = CheckpointManager(workspace_dir=tmp_path)

        # Initially clean (no files)
        assert manager.is_workspace_clean() is True

        # Add a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Should show uncommitted changes
        assert manager.is_workspace_clean() is False

    def test_get_changed_files(self, tmp_path):
        """Test getting list of changed files."""
        # Create git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

        manager = CheckpointManager(workspace_dir=tmp_path)

        # No changes initially
        assert len(manager.get_changed_files()) == 0

        # Add files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        # Should detect changes
        changed = manager.get_changed_files()
        assert len(changed) == 2
        assert "file1.txt" in changed or any("file1.txt" in f for f in changed)

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, tmp_path):
        """Test checkpoint creation."""
        # Setup git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

        manager = CheckpointManager(workspace_dir=tmp_path)

        # Create initial commit
        file1 = tmp_path / "file1.txt"
        file1.write_text("initial content")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True)

        # Make changes
        file2 = tmp_path / "file2.txt"
        file2.write_text("new content")

        # Create checkpoint
        checkpoint = await manager.create_checkpoint(
            description="Before risky operation",
            step_number=5,
            auto_stage=True,
        )

        assert checkpoint is not None
        assert checkpoint.step_number == 5
        assert checkpoint.description == "Before risky operation"
        assert len(checkpoint.id) == 40  # Git SHA
        assert checkpoint.is_clean is False  # Had uncommitted changes

    @pytest.mark.asyncio
    async def test_rollback_to_checkpoint(self, tmp_path):
        """Test rollback to previous checkpoint."""
        # Setup git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

        manager = CheckpointManager(workspace_dir=tmp_path)

        # Create checkpoint
        file1 = tmp_path / "file1.txt"
        file1.write_text("version 1")

        checkpoint = await manager.create_checkpoint(
            description="Checkpoint 1",
            step_number=1,
            auto_stage=True,
        )

        # Make more changes
        file1.write_text("version 2 - bad changes")

        # Rollback
        success = await manager.rollback_to_checkpoint(checkpoint.id, hard=True)
        assert success is True

        # Verify rollback
        content = file1.read_text()
        assert content == "version 1"


class TestAuditLogger:
    """Test comprehensive audit trail logging."""

    def test_audit_logger_initialization(self, tmp_path):
        """Test AuditLogger initialization."""
        audit = AuditLogger(
            workspace_dir=tmp_path,
            agent_id="test-agent",
            redact_pii=True,
        )

        assert audit.agent_id == "test-agent"
        assert audit.redact_pii is True
        assert audit.log_file.exists() is False  # Not created until first log

    def test_log_planning_event(self, tmp_path):
        """Test logging planning event."""
        audit = AuditLogger(workspace_dir=tmp_path, agent_id="test-agent")

        audit.log_planning(
            prompt="Create execution plan",
            response="Step 1: Do something",
            model="claude-sonnet-4",
            cost=0.15,
            cycle=1,
            success=True,
        )

        # Verify log file created
        assert audit.log_file.exists()

        # Verify log entry
        with open(audit.log_file) as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "planning"
        assert entry["agent_id"] == "test-agent"
        assert entry["cycle"] == 1
        assert entry["model"] == "claude-sonnet-4"
        assert entry["cost"] == 0.15
        assert entry["success"] is True

    def test_log_execution_event(self, tmp_path):
        """Test logging execution event."""
        audit = AuditLogger(workspace_dir=tmp_path, agent_id="test-agent")

        audit.log_execution(
            step=5,
            prompt="Execute step 5",
            response="Step complete",
            model="claude-3-haiku-20240307",
            cost=0.05,
            tool_calls=[
                {"tool": "write_file", "args": {"path": "test.py"}},
                {"tool": "read_file", "args": {"path": "config.json"}},
            ],
            success=True,
        )

        # Verify log entry
        with open(audit.log_file) as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "execution"
        assert entry["step"] == 5
        assert len(entry["tool_calls"]) == 2
        assert entry["tool_calls"][0]["tool"] == "write_file"

    def test_log_security_event(self, tmp_path):
        """Test logging security event."""
        audit = AuditLogger(workspace_dir=tmp_path, agent_id="test-agent")

        audit.log_security_event(
            event_type="policy_violation",
            description="Attempted access to blocked path",
            severity="critical",
            resource="/etc/passwd",
            action="read",
        )

        # Verify log entry
        with open(audit.log_file) as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "security"
        assert len(entry["security_events"]) == 1
        assert entry["security_events"][0]["severity"] == "critical"
        assert entry["security_events"][0]["resource"] == "/etc/passwd"

    def test_pii_redaction(self, tmp_path):
        """Test PII redaction in logs."""
        audit = AuditLogger(workspace_dir=tmp_path, agent_id="test-agent", redact_pii=True)

        audit.log_planning(
            prompt="Contact john.doe@example.com at 555-123-4567",
            response="Will contact",
            model="test",
            cost=0.0,
            cycle=1,
        )

        # Verify redaction
        with open(audit.log_file) as f:
            entry = json.loads(f.readline())

        assert "[EMAIL_REDACTED]" in entry["prompt"]
        assert "[PHONE_REDACTED]" in entry["prompt"]
        assert "john.doe@example.com" not in entry["prompt"]
        assert "555-123-4567" not in entry["prompt"]

    def test_get_log_summary(self, tmp_path):
        """Test getting log summary statistics."""
        audit = AuditLogger(workspace_dir=tmp_path, agent_id="test-agent")

        # Log multiple events
        audit.log_planning(prompt="p1", response="r1", model="m1", cost=0.15, cycle=1)
        audit.log_execution(
            step=1, prompt="e1", response="r1", model="m2", cost=0.05, tool_calls=[], success=True
        )
        audit.log_execution(
            step=2,
            prompt="e2",
            response="r2",
            model="m2",
            cost=0.05,
            tool_calls=[],
            success=False,
            error="Failed",
        )

        summary = audit.get_log_summary()

        assert summary["total_events"] == 3
        assert summary["by_type"]["planning"] == 1
        assert summary["by_type"]["execution"] == 2
        assert summary["total_cost"] == 0.25
        assert summary["errors"] == 1


class TestStateValidation:
    """Test Pydantic state validation."""

    def test_agent_state_validation_success(self):
        """Test successful state validation."""
        state_data = {
            "agent_id": "test-agent",
            "updated_at": "2024-01-01T00:00:00",
            "phase": "executing",
            "current_turn": 5,
            "consecutive_errors": 0,
        }

        state = AgentState.from_dict(state_data)

        assert state.agent_id == "test-agent"
        assert state.phase == "executing"
        assert state.current_turn == 5
        assert state.consecutive_errors == 0

    def test_agent_state_validation_with_defaults(self):
        """Test state validation with default values."""
        minimal_data = {
            "agent_id": "test-agent",
            "updated_at": "2024-01-01T00:00:00",
        }

        state = AgentState.from_dict(minimal_data)

        assert state.agent_id == "test-agent"
        assert state.current_turn == 0  # Default value
        assert state.consecutive_errors == 0  # Default value
        assert state.phase is None  # Optional field

    def test_agent_state_extra_fields_allowed(self):
        """Test that extra fields are allowed (backward compatibility)."""
        state_data = {
            "agent_id": "test-agent",
            "updated_at": "2024-01-01T00:00:00",
            "custom_field": "custom_value",
            "another_field": 123,
        }

        state = AgentState.from_dict(state_data)

        # Should not raise validation error
        assert state.agent_id == "test-agent"

        # Extra fields should be preserved
        state_dict = state.to_dict()
        assert "custom_field" in state_dict
        assert state_dict["custom_field"] == "custom_value"

    def test_state_manager_with_validation(self, tmp_path):
        """Test StateManager with validation enabled."""
        manager = StateManager(
            agent_id="test-agent",
            workspace_dir=tmp_path,
            enable_validation=True,
        )

        # Save valid state
        manager.save(
            phase="testing",
            current_turn=10,
            consecutive_errors=0,
        )

        # Load and verify
        state = manager.load()
        assert state["phase"] == "testing"
        assert state["current_turn"] == 10
        assert "agent_id" in state
        assert state["agent_id"] == "test-agent"

    def test_state_manager_validation_disabled(self, tmp_path):
        """Test StateManager with validation disabled."""
        manager = StateManager(
            agent_id="test-agent",
            workspace_dir=tmp_path,
            enable_validation=False,
        )

        # Save any data (no validation)
        manager.save(
            random_field="anything",
            number=999,
        )

        # Should load without errors
        state = manager.load()
        assert state["random_field"] == "anything"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

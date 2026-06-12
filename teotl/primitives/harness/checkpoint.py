"""Git-based checkpoint and rollback system for autonomous agents.

Provides:
1. Automatic checkpoints before risky operations
2. Rollback to previous state on failure
3. Checkpoint history and management
4. Integration with Worker execution flow
"""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """Represents a git-based checkpoint."""

    id: str  # Git commit SHA
    timestamp: datetime
    description: str
    step_number: int
    files_changed: list[str]
    is_clean: bool  # Whether workspace was clean at checkpoint

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "step_number": self.step_number,
            "files_changed": self.files_changed,
            "is_clean": self.is_clean,
        }


class CheckpointManager:
    """Manages git-based checkpoints for rollback capability.

    Creates automatic checkpoints before risky operations and provides
    rollback capabilities if execution fails.

    Usage:
        manager = CheckpointManager(workspace_dir=Path("~/workspace"))

        # Create checkpoint before risky operation
        checkpoint = await manager.create_checkpoint(
            description="Before step 5: Refactor database layer",
            step_number=5,
        )

        try:
            # Execute risky operation
            result = await execute_step()

            if not result.success:
                # Rollback on failure
                await manager.rollback_to_checkpoint(checkpoint.id)

        except Exception as e:
            # Rollback on exception
            await manager.rollback_to_checkpoint(checkpoint.id)
            raise
    """

    def __init__(
        self,
        workspace_dir: Path,
        auto_checkpoint_enabled: bool = True,
        checkpoint_prefix: str = "forge-checkpoint",
    ):
        """Initialize checkpoint manager.

        Args:
            workspace_dir: Workspace directory (must be git repo)
            auto_checkpoint_enabled: Enable automatic checkpoints
            checkpoint_prefix: Prefix for checkpoint commit messages
        """
        self.workspace_dir = Path(workspace_dir).resolve()
        self.auto_checkpoint_enabled = auto_checkpoint_enabled
        self.checkpoint_prefix = checkpoint_prefix

        # Validate git repo
        if not self._is_git_repo():
            logger.warning(
                f"Workspace {workspace_dir} is not a git repo. "
                "Checkpoint functionality will be limited."
            )
            self.auto_checkpoint_enabled = False

    def _is_git_repo(self) -> bool:
        """Check if workspace is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Git check failed: {e}")
            return False

    def _run_git_command(
        self,
        command: list[str],
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run git command in workspace.

        Args:
            command: Git command args (without 'git')
            check: Raise exception on non-zero exit

        Returns:
            CompletedProcess result
        """
        result = subprocess.run(
            ["git"] + command,
            cwd=self.workspace_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if check and result.returncode != 0:
            raise RuntimeError(
                f"Git command failed: {' '.join(command)}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        return result

    def is_workspace_clean(self) -> bool:
        """Check if workspace has uncommitted changes.

        Returns:
            True if workspace is clean (no uncommitted changes)
        """
        if not self.auto_checkpoint_enabled:
            return True

        try:
            result = self._run_git_command(["status", "--porcelain"], check=False)
            return len(result.stdout.strip()) == 0
        except Exception as e:
            logger.error(f"Failed to check workspace status: {e}")
            return False

    def get_changed_files(self) -> list[str]:
        """Get list of files with uncommitted changes.

        Returns:
            List of file paths relative to workspace
        """
        if not self.auto_checkpoint_enabled:
            return []

        try:
            result = self._run_git_command(["status", "--porcelain"], check=False)
            lines = result.stdout.strip().split("\n")

            files = []
            for line in lines:
                if line.strip():
                    # Format: "XY filename" where X/Y are status codes
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        files.append(parts[1])

            return files
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return []

    async def create_checkpoint(
        self,
        description: str,
        step_number: int,
        auto_stage: bool = True,
    ) -> Checkpoint | None:
        """Create git checkpoint before risky operation.

        Args:
            description: Description of what's about to happen
            step_number: Step number being executed
            auto_stage: Automatically stage all changes

        Returns:
            Checkpoint object or None if checkpoint creation failed
        """
        if not self.auto_checkpoint_enabled:
            logger.debug("Checkpoint disabled (not a git repo)")
            return None

        try:
            # Get current state
            was_clean = self.is_workspace_clean()
            files_changed = self.get_changed_files()

            # Auto-stage changes if requested
            if auto_stage and files_changed:
                logger.info(f"Staging {len(files_changed)} changed files for checkpoint")
                self._run_git_command(["add", "-A"])

            # Check if there's anything to commit
            result = self._run_git_command(["diff", "--cached", "--quiet"], check=False)
            has_staged_changes = result.returncode != 0

            if not has_staged_changes:
                logger.debug("No staged changes for checkpoint")
                # Still return a checkpoint referencing HEAD
                head_sha = self._get_head_sha()
                return Checkpoint(
                    id=head_sha,
                    timestamp=datetime.now(),
                    description=description,
                    step_number=step_number,
                    files_changed=[],
                    is_clean=True,
                )

            # Create checkpoint commit
            commit_message = f"{self.checkpoint_prefix}: {description}"
            self._run_git_command(["commit", "-m", commit_message])

            # Get commit SHA
            commit_sha = self._get_head_sha()

            checkpoint = Checkpoint(
                id=commit_sha,
                timestamp=datetime.now(),
                description=description,
                step_number=step_number,
                files_changed=files_changed,
                is_clean=was_clean,
            )

            logger.info(
                f"Created checkpoint {commit_sha[:8]} for step {step_number}: "
                f"{len(files_changed)} files"
            )

            return checkpoint

        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return None

    async def rollback_to_checkpoint(
        self,
        checkpoint_id: str,
        hard: bool = True,
    ) -> bool:
        """Rollback workspace to checkpoint.

        Args:
            checkpoint_id: Git commit SHA to rollback to
            hard: Use hard reset (discard uncommitted changes)

        Returns:
            True if rollback succeeded
        """
        if not self.auto_checkpoint_enabled:
            logger.warning("Cannot rollback: checkpoint disabled")
            return False

        try:
            logger.warning(f"Rolling back to checkpoint {checkpoint_id[:8]}...")

            # Verify checkpoint exists
            result = self._run_git_command(
                ["cat-file", "-e", checkpoint_id],
                check=False,
            )

            if result.returncode != 0:
                logger.error(f"Checkpoint {checkpoint_id} not found")
                return False

            # Perform rollback
            if hard:
                self._run_git_command(["reset", "--hard", checkpoint_id])
            else:
                self._run_git_command(["reset", "--soft", checkpoint_id])

            logger.info(f"✅ Rolled back to checkpoint {checkpoint_id[:8]}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def _get_head_sha(self) -> str:
        """Get current HEAD commit SHA.

        Returns:
            Commit SHA string
        """
        result = self._run_git_command(["rev-parse", "HEAD"])
        return result.stdout.strip()

    def get_checkpoint_history(
        self,
        limit: int = 10,
    ) -> list[Checkpoint]:
        """Get recent checkpoint history.

        Args:
            limit: Maximum number of checkpoints to return

        Returns:
            List of Checkpoint objects
        """
        if not self.auto_checkpoint_enabled:
            return []

        try:
            # Get commit history for checkpoint commits
            result = self._run_git_command(
                [
                    "log",
                    f"--grep=^{self.checkpoint_prefix}:",
                    f"-{limit}",
                    "--format=%H|%ct|%s",
                ]
            )

            checkpoints = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|", 2)
                if len(parts) != 3:
                    continue

                commit_sha, timestamp, message = parts

                # Extract description from message
                if message.startswith(f"{self.checkpoint_prefix}:"):
                    description = message[len(self.checkpoint_prefix) + 1 :].strip()
                else:
                    description = message

                # Parse step number from description if present
                step_number = 0
                if "step " in description.lower():
                    try:
                        # Extract number after "step"
                        parts = description.lower().split("step")[1].strip().split()
                        step_number = int(parts[0].rstrip(":"))
                    except (IndexError, ValueError):
                        pass

                checkpoint = Checkpoint(
                    id=commit_sha,
                    timestamp=datetime.fromtimestamp(int(timestamp)),
                    description=description,
                    step_number=step_number,
                    files_changed=[],  # Not preserved in commit
                    is_clean=True,  # Assume clean at checkpoint
                )

                checkpoints.append(checkpoint)

            return checkpoints

        except Exception as e:
            logger.error(f"Failed to get checkpoint history: {e}")
            return []

    def cleanup_old_checkpoints(
        self,
        keep_count: int = 20,
    ) -> int:
        """Remove old checkpoint commits to keep history manageable.

        Args:
            keep_count: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints removed
        """
        if not self.auto_checkpoint_enabled:
            return 0

        try:
            checkpoints = self.get_checkpoint_history(limit=keep_count + 100)

            if len(checkpoints) <= keep_count:
                logger.debug(f"Only {len(checkpoints)} checkpoints, no cleanup needed")
                return 0

            # Keep the most recent `keep_count` checkpoints
            # For older ones, we'd need to rewrite git history (complex)
            # For now, just log that cleanup is needed
            old_count = len(checkpoints) - keep_count
            logger.info(f"Found {old_count} old checkpoints (keeping {keep_count} most recent)")

            # TODO: Implement git history rewriting if needed
            # This is complex and risky, so we'll defer for now

            return 0

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0

    def __repr__(self) -> str:
        """String representation."""
        status = "enabled" if self.auto_checkpoint_enabled else "disabled"
        return f"CheckpointManager(workspace={self.workspace_dir}, status={status})"

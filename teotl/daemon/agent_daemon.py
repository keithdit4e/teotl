"""Agent daemon for autonomous agent execution.

The agent daemon manages scheduled missions and immediate tasks for a single agent.
Each agent instance gets its own daemon (decentralized architecture).

Key responsibilities:
- Execute missions on schedule (HOURLY, DAILY, WEEKLY)
- Process tasks by priority (CRITICAL → LOW)
- Interrupt missions for high-priority tasks
- Register with resolution service (optional)
- Handle graceful shutdown (SIGTERM for containers)
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from teotl.primitives.missions import Mission, MissionInterval, MissionStore
from teotl.primitives.tasks import Priority, Task, TaskState, TaskStore

if TYPE_CHECKING:
    from collections.abc import Callable

    from teotl.primitives.resolution import ResolutionService

logger = logging.getLogger(__name__)


class AgentDaemon:
    """Autonomous execution daemon for a single agent.

    Each agent instance runs its own daemon (decentralized model).
    The daemon handles:
    - Scheduled mission execution
    - Priority-based task processing
    - Mission interruption for urgent tasks
    - Optional resolution service registration
    - Graceful shutdown
    """

    def __init__(
        self,
        agent_id: str,
        agent_executor: Callable[[str, dict[str, Any]], Any],
        *,
        mission_store: MissionStore | None = None,
        task_store: TaskStore | None = None,
        resolution_service: ResolutionService | None = None,
        poll_interval: int = 10,  # seconds
        data_dir: Path | None = None,
    ):
        """Initialize heartbeat daemon.

        Args:
            agent_id: Unique agent identifier
            agent_executor: Async function to execute tasks/missions
                           Takes (description, context) -> result
            mission_store: Mission storage (default: creates new)
            task_store: Task storage (default: creates new)
            resolution_service: Optional resolution service
            poll_interval: Seconds between execution cycles
            data_dir: Data directory for stores (default: ~/.forge/{agent_id}/)
        """
        self.agent_id = agent_id
        self.agent_executor = agent_executor
        self.poll_interval = poll_interval
        self.resolution_service = resolution_service

        # Setup data directory
        if data_dir is None:
            data_dir = Path.home() / ".forge" / agent_id
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = data_dir

        # Initialize stores
        self.mission_store = mission_store or MissionStore(data_dir / "missions.db")
        self.task_store = task_store or TaskStore(data_dir / "tasks.db")

        # Daemon state
        self.running = False
        self.current_mission: Mission | None = None
        self.current_task: Task | None = None
        self._stop_event = asyncio.Event()
        self._loop_task: asyncio.Task | None = None

        # PID file for process management
        self.pid_file = data_dir / "daemon.pid"

    async def start(self) -> None:
        """Start the daemon (blocks until stopped).

        This is the main entry point. It will:
        1. Register with resolution service (if provided)
        2. Write PID file
        3. Start execution loop
        4. Block until stopped (SIGTERM or stop() called)
        """
        if self.running:
            logger.warning(f"Daemon already running for agent {self.agent_id}")
            return

        logger.info(f"Starting heartbeat daemon for agent {self.agent_id}")
        self.running = True

        # Write PID file
        self._write_pid_file()

        # Register with resolution service
        if self.resolution_service:
            await self._register_with_resolution_service()

        # Setup signal handlers
        self._setup_signal_handlers()

        # Start execution loop
        try:
            self._loop_task = asyncio.create_task(self._execution_loop())
            await self._stop_event.wait()  # Block until stopped
        finally:
            await self._cleanup()

    async def stop(self) -> None:
        """Stop the daemon gracefully."""
        if not self.running:
            return

        logger.info(f"Stopping daemon for agent {self.agent_id}")
        self.running = False
        self._stop_event.set()

        # Wait for loop to finish
        if self._loop_task:
            await self._loop_task

    async def _execution_loop(self) -> None:
        """Main execution loop - processes tasks and missions."""
        logger.info(f"Execution loop started for agent {self.agent_id}")

        while self.running:
            try:
                await self._execute_cycle()
            except Exception as e:
                logger.error(f"Error in execution cycle: {e}", exc_info=True)

            # Wait before next cycle
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
                break  # Stop event was set
            except TimeoutError:
                pass  # Normal timeout, continue loop

        logger.info(f"Execution loop stopped for agent {self.agent_id}")

    async def _execute_cycle(self) -> None:
        """Single execution cycle - priority-based scheduling.

        Priority order:
        1. Cleanup expired tasks first
        2. CRITICAL tasks (always interrupt)
        3. URGENT tasks (interrupt if mission allows)
        4. Due missions
        5. HIGH/NORMAL/LOW tasks (only if no active mission blocking them)
        """
        # 1. Cleanup expired tasks first (before checking what to execute)
        await self.task_store.cleanup_expired()

        # 2. Check for CRITICAL tasks (always interrupt)
        critical_tasks = await self.task_store.get_by_priority(
            Priority.CRITICAL, state=TaskState.PENDING, limit=1
        )
        if critical_tasks:
            await self._interrupt_and_execute_task(critical_tasks[0])
            return

        # 3. Check for URGENT tasks (interrupt if mission allows)
        urgent_tasks = await self.task_store.get_by_priority(
            Priority.URGENT, state=TaskState.PENDING, limit=1
        )
        if urgent_tasks:
            if not self.current_mission or self._should_interrupt(urgent_tasks[0]):
                await self._interrupt_and_execute_task(urgent_tasks[0])
                return
            # URGENT task exists but can't interrupt - skip other tasks for now
            return

        # 4. If no current mission, check for due missions
        if not self.current_mission:
            due_missions = await self.mission_store.list_due()
            if due_missions:
                await self._execute_mission(due_missions[0])
                return

        # 5. Process task queue (HIGH, NORMAL, LOW) - only if no active mission
        if not self.current_mission:
            pending_tasks = await self.task_store.get_pending(limit=1)
            if pending_tasks:
                await self._execute_task(pending_tasks[0])
                return

    def _should_interrupt(self, task: Task) -> bool:
        """Check if task should interrupt current mission.

        Args:
            task: Task wanting to execute

        Returns:
            True if should interrupt current mission
        """
        if not self.current_mission:
            return True

        # Mission cannot be interrupted
        if not self.current_mission.can_be_interrupted:
            return False

        # Check if task priority meets interrupt threshold
        return task.priority >= self.current_mission.interrupt_threshold

    async def _interrupt_and_execute_task(self, task: Task) -> None:
        """Interrupt current mission and execute task.

        Args:
            task: High-priority task to execute
        """
        if self.current_mission:
            logger.info(
                f"Interrupting mission {self.current_mission.id[:8]} for {task.priority.name} task"
            )
            # Mission will resume on next cycle

        await self._execute_task(task)

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task.

        Args:
            task: Task to execute
        """
        logger.info(
            f"Executing {task.priority.name} task {task.id[:8]}: {task.description[:50]}..."
        )

        self.current_task = task
        task.start()
        await self.task_store.update(task)

        try:
            # Execute via agent
            result = await self.agent_executor(task.description, task.context)

            # Mark complete
            task.complete(result={"output": result} if result else None)
            await self.task_store.update(task)

            logger.info(f"Task {task.id[:8]} completed successfully")

        except Exception as e:
            task.fail(str(e))
            await self.task_store.update(task)
            logger.error(f"Task {task.id[:8]} failed: {e}")

        finally:
            self.current_task = None

    async def _execute_mission(self, mission: Mission) -> None:
        """Execute a mission.

        Args:
            mission: Mission to execute
        """
        logger.info(
            f"Executing mission {mission.id[:8]} ({mission.interval.value}): {mission.description[:50]}..."
        )

        self.current_mission = mission
        mission.last_executed_at = datetime.now()
        mission.execution_count += 1

        # Calculate next execution time
        mission.next_execution_at = self._calculate_next_execution(mission)
        await self.mission_store.update(mission)

        try:
            # Execute via agent
            await self.agent_executor(mission.description, mission.context)

            # Mark success
            mission.success_count += 1
            await self.mission_store.update(mission)

            logger.info(f"Mission {mission.id[:8]} completed successfully")

            # If ONCE, mark as completed
            if mission.interval == MissionInterval.ONCE:
                mission.complete()
                await self.mission_store.update(mission)

        except Exception as e:
            mission.failure_count += 1
            await self.mission_store.update(mission)
            logger.error(f"Mission {mission.id[:8]} failed: {e}")

        finally:
            self.current_mission = None

    def _calculate_next_execution(self, mission: Mission) -> datetime | None:
        """Calculate next execution time based on interval.

        Args:
            mission: Mission to calculate for

        Returns:
            Next execution datetime, or None if MANUAL/ONCE
        """
        now = datetime.now()

        if mission.interval == MissionInterval.MINUTES_5:
            return now + timedelta(minutes=5)
        elif mission.interval == MissionInterval.MINUTES_10:
            return now + timedelta(minutes=10)
        elif mission.interval == MissionInterval.MINUTES_30:
            return now + timedelta(minutes=30)
        elif mission.interval == MissionInterval.HOURLY:
            return now + timedelta(hours=1)
        elif mission.interval == MissionInterval.DAILY:
            return now + timedelta(days=1)
        elif mission.interval == MissionInterval.WEEKLY:
            return now + timedelta(weeks=1)
        elif mission.interval == MissionInterval.ONCE:
            return None  # Don't reschedule
        elif mission.interval == MissionInterval.MANUAL:
            return None  # Wait for manual trigger

        return None

    async def _register_with_resolution_service(self) -> None:
        """Register this agent with resolution service."""
        if not self.resolution_service:
            return

        try:
            # TODO: Get capabilities and endpoint from agent config
            # For now, just register with agent_id
            await self.resolution_service.register_agent(
                agent_id=self.agent_id,
                capabilities=[],  # TODO: Get from agent
                endpoint="http://localhost:8000/a2a",  # TODO: Get from config
            )
            logger.info(f"Registered agent {self.agent_id} with resolution service")
        except Exception as e:
            logger.warning(f"Failed to register with resolution service: {e}")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def handle_signal(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.stop())

        # Handle SIGTERM (Docker/K8s sends this)
        signal.signal(signal.SIGTERM, handle_signal)

        # Handle SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, handle_signal)

    def _write_pid_file(self) -> None:
        """Write PID file for process management."""
        try:
            self.pid_file.write_text(str(os.getpid()))
            logger.debug(f"Wrote PID file: {self.pid_file}")
        except Exception as e:
            logger.warning(f"Failed to write PID file: {e}")

    def _remove_pid_file(self) -> None:
        """Remove PID file on shutdown."""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.debug(f"Removed PID file: {self.pid_file}")
        except Exception as e:
            logger.warning(f"Failed to remove PID file: {e}")

    async def _cleanup(self) -> None:
        """Cleanup on shutdown."""
        # Unregister from resolution service
        if self.resolution_service:
            try:
                await self.resolution_service.unregister_agent(self.agent_id)
                logger.info(f"Unregistered agent {self.agent_id} from resolution service")
            except Exception as e:
                logger.warning(f"Failed to unregister from resolution service: {e}")

        # Remove PID file
        self._remove_pid_file()

        # Close stores
        self.mission_store.close()
        self.task_store.close()

        logger.info(f"Daemon cleanup complete for agent {self.agent_id}")

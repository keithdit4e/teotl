"""
Autonomous Agent Example

This example demonstrates how to create and run an autonomous agent
that executes tasks and missions using the HeartbeatDaemon.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from teotl.daemon.heartbeat import HeartbeatDaemon

from teotl.daemon.executor import create_simple_executor
from teotl.primitives.missions import Mission, MissionInterval
from teotl.primitives.tasks import Priority, Task

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run autonomous agent example."""

    # NOTE: Replace with your actual provider
    # For this example, we'll use a mock provider
    from unittest.mock import AsyncMock, Mock

    mock_provider = Mock()
    mock_provider.complete = AsyncMock(
        return_value=Mock(message=Mock(content="Task completed successfully", tool_calls=[]))
    )

    # Create agent executor
    # This bridges the daemon to the agent loop
    executor = create_simple_executor(
        provider=mock_provider,
        instructions="""You are an email assistant that helps manage emails.

        You can:
        - Check for new emails
        - Send emails
        - Organize emails into folders
        - Flag important messages
        """,
        skills=["gmail"],  # Would load gmail skill if configured
        auto_approve=True,  # Auto-approve for autonomous execution
    )

    # Create data directory
    data_dir = Path.home() / ".forge" / "examples" / "email-agent"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create heartbeat daemon
    daemon = HeartbeatDaemon(
        agent_id="email-agent",
        agent_executor=executor,
        data_dir=data_dir,
        poll_interval=5,  # Check every 5 seconds
    )

    logger.info("🤖 Creating autonomous email agent")

    # Add some missions (scheduled work)
    missions = [
        Mission(
            description="Check for new emails and flag important ones",
            interval=MissionInterval.HOURLY,
            next_execution_at=datetime.now() + timedelta(seconds=10),
            can_be_interrupted=True,
            interrupt_threshold=Priority.URGENT,
        ),
        Mission(
            description="Clean up spam folder",
            interval=MissionInterval.DAILY,
            next_execution_at=datetime.now() + timedelta(seconds=30),
            can_be_interrupted=True,
            interrupt_threshold=Priority.URGENT,
        ),
    ]

    for mission in missions:
        await daemon.mission_store.create(mission)
        logger.info(f"📅 Added mission: {mission.description}")

    # Add some tasks (immediate work)
    tasks = [
        Task(
            description="Send welcome email to new user",
            priority=Priority.HIGH,
            context={"to": "newuser@example.com", "template": "welcome"},
            expires_at=datetime.now() + timedelta(hours=1),
        ),
        Task(
            description="Reply to customer support ticket #1234",
            priority=Priority.URGENT,
            context={"ticket_id": "1234", "category": "billing"},
            expires_at=datetime.now() + timedelta(hours=2),
        ),
        Task(
            description="Archive old emails from last year",
            priority=Priority.LOW,
            context={"before_date": "2024-01-01"},
            expires_at=datetime.now() + timedelta(days=7),
        ),
    ]

    for task in tasks:
        await daemon.task_store.create(task)
        logger.info(f"✅ Added {task.priority.name} priority task: {task.description[:50]}...")

    # Start daemon
    logger.info("\n🚀 Starting autonomous agent daemon...")
    logger.info("Press Ctrl+C to stop\n")

    # Start daemon in background
    daemon_task = asyncio.create_task(daemon.start())

    try:
        # Monitor for 60 seconds or until Ctrl+C
        for _i in range(12):  # 12 x 5 seconds = 60 seconds
            await asyncio.sleep(5)

            # Show status
            pending_tasks = await daemon.task_store.get_pending()
            logger.info(
                f"📊 Status: {len(pending_tasks)} pending tasks, "
                f"Current mission: {daemon.current_mission.description[:30] + '...' if daemon.current_mission else 'None'}"
            )

            # Check if all work is done
            if not pending_tasks and not daemon.current_mission:
                due_missions = await daemon.mission_store.list_due()
                if not due_missions:
                    logger.info("✨ All work completed!")
                    break

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupt received, shutting down gracefully...")

    finally:
        # Stop daemon
        await daemon.stop()
        await daemon_task

        logger.info("👋 Daemon stopped")

        # Show final stats
        all_tasks = await daemon.task_store.get_all()
        completed = sum(1 for t in all_tasks if t.state.value == "completed")
        failed = sum(1 for t in all_tasks if t.state.value == "failed")

        all_missions = await daemon.mission_store.list_all()
        total_executions = sum(m.execution_count for m in all_missions)

        logger.info("\n📈 Final Statistics:")
        logger.info(f"   Tasks completed: {completed}")
        logger.info(f"   Tasks failed: {failed}")
        logger.info(f"   Mission executions: {total_executions}")


if __name__ == "__main__":
    asyncio.run(main())

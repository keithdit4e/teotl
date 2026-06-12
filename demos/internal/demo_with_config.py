"""
Autonomous Agent Demo with Real Provider
Uses configuration file for easy setup.

Setup:
1. Edit config.yaml to set your provider
2. Set environment variable: export ANTHROPIC_API_KEY="your-key"
3. Run: python demo_with_config.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from teotl.daemon.heartbeat import HeartbeatDaemon

from teotl.daemon.executor import create_simple_executor
from teotl.primitives.missions import Mission, MissionInterval
from teotl.primitives.tasks import Priority, Task

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from YAML file."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        logger.error(f"❌ Configuration file not found: {config_path}")
        logger.error("   Please create config.yaml (see REAL_SETUP.md)")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def create_provider(config):
    """Create provider based on config."""
    provider_type = config["provider"]["type"]
    model = config["provider"]["model"]
    api_key_env = config["provider"].get("api_key_env")

    logger.info(f"🔌 Creating {provider_type} provider with model {model}")

    # Get API key from environment if needed
    api_key = None
    if api_key_env:
        api_key = os.getenv(api_key_env)
        if not api_key:
            logger.error(f"❌ Environment variable {api_key_env} not set")
            logger.error(f"   Run: export {api_key_env}='your-key-here'")
            sys.exit(1)
        logger.info(f"✅ API key found in ${api_key_env}")

    # Create provider based on type
    if provider_type == "anthropic":
        from teotl.core.provider import AnthropicProvider

        return AnthropicProvider(api_key=api_key, model=model)

    elif provider_type == "openai":
        from teotl.core.provider import OpenAIProvider

        return OpenAIProvider(api_key=api_key, model=model)

    elif provider_type == "ollama":
        from teotl.core.provider import OllamaProvider

        # Check if Ollama is running
        try:
            import ollama

            client = ollama.Client()
            models = client.list()
            logger.info(
                f"✅ Ollama connected. Available models: {[m['name'] for m in models['models']]}"
            )
        except Exception:
            logger.error("❌ Error: Ollama not running")
            logger.error("   Start it with: ollama serve")
            sys.exit(1)

        return OllamaProvider(model=model)

    else:
        logger.error(f"❌ Unknown provider type: {provider_type}")
        logger.error("   Supported: anthropic, openai, ollama")
        sys.exit(1)


async def main():
    """Run demo with real provider."""

    logger.info("=" * 60)
    logger.info("🤖 Forge Autonomous Agent Demo")
    logger.info("=" * 60)

    # Load configuration
    try:
        config = load_config()
        logger.info("📄 Configuration loaded from config.yaml")
    except Exception as e:
        logger.error(f"❌ Failed to load config: {e}")
        sys.exit(1)

    # Create provider
    try:
        provider = create_provider(config)
    except Exception as e:
        logger.error(f"❌ Failed to create provider: {e}")
        sys.exit(1)

    # Add rate limiting if configured
    if "rate_limits" in config:
        from teotl.core.rate_limited_provider import RateLimitedProvider

        provider = RateLimitedProvider(
            provider=provider,
            max_requests_per_minute=config["rate_limits"]["max_requests_per_minute"],
            max_cost_per_minute=config["rate_limits"]["max_cost_per_minute"],
        )
        logger.info(
            f"🛡️  Rate limiting: {config['rate_limits']['max_requests_per_minute']} req/min, "
            f"${config['rate_limits']['max_cost_per_minute']}/min"
        )

    # Create executor
    executor = create_simple_executor(
        provider=provider,
        instructions=config["agent"]["instructions"],
        auto_approve=config["agent"]["auto_approve"],
    )
    logger.info("✅ Agent executor created")

    # Create data directory
    data_dir = Path(config["daemon"]["data_dir"]).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Data directory: {data_dir}")

    # Create daemon
    daemon = HeartbeatDaemon(
        agent_id=config["agent"]["agent_id"],
        agent_executor=executor,
        data_dir=data_dir,
        poll_interval=config["daemon"]["poll_interval"],
    )
    logger.info(f"🤖 Daemon created: {config['agent']['agent_id']}")

    # Add missions from config
    logger.info("\n📅 Adding missions:")
    for mission_config in config["missions"]:
        mission = Mission(
            description=mission_config["description"],
            interval=MissionInterval[mission_config["interval"]],
            next_execution_at=datetime.now() + timedelta(seconds=15),
            can_be_interrupted=mission_config["can_be_interrupted"],
            interrupt_threshold=Priority[mission_config["interrupt_threshold"]],
        )
        await daemon.mission_store.create(mission)
        logger.info(
            f"   • {mission.description} ({mission.interval.value}, "
            f"interruptible by {mission.interrupt_threshold.name}+)"
        )

    # Add tasks from config
    logger.info("\n✅ Adding tasks:")
    for task_config in config["tasks"]:
        # Calculate expiration
        expires_at = datetime.now()
        if "expires_minutes" in task_config:
            expires_at += timedelta(minutes=task_config["expires_minutes"])
        elif "expires_days" in task_config:
            expires_at += timedelta(days=task_config["expires_days"])

        task = Task(
            description=task_config["description"],
            priority=Priority[task_config["priority"]],
            context=task_config.get("context", {}),
            expires_at=expires_at,
        )
        await daemon.task_store.create(task)
        logger.info(f"   • [{task.priority.name}] {task.description}")

    # Start daemon
    logger.info("\n" + "=" * 60)
    logger.info("🚀 Starting autonomous agent daemon...")
    logger.info(f"⏱️  Poll interval: {config['daemon']['poll_interval']}s")
    logger.info("⚠️  Press Ctrl+C to stop")
    logger.info("=" * 60 + "\n")

    daemon_task = asyncio.create_task(daemon.start())

    try:
        # Monitor until work is done or Ctrl+C
        check_count = 0
        max_checks = 40  # ~20 minutes with 30s interval

        while check_count < max_checks:
            await asyncio.sleep(5)
            check_count += 1

            # Get current status
            pending_tasks = await daemon.task_store.get_pending()
            current_work = None

            if daemon.current_task:
                current_work = f"Task: {daemon.current_task.description[:40]}..."
            elif daemon.current_mission:
                current_work = f"Mission: {daemon.current_mission.description[:40]}..."

            logger.info(
                f"📊 [{check_count}] Pending: {len(pending_tasks)} tasks | "
                f"Current: {current_work or 'Idle'}"
            )

            # Check if all work is done
            if not pending_tasks and not daemon.current_mission and not daemon.current_task:
                due_missions = await daemon.mission_store.list_due()
                if not due_missions:
                    logger.info("\n✨ All work completed!")
                    break

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupt received, shutting down gracefully...")

    finally:
        # Stop daemon
        logger.info("🛑 Stopping daemon...")
        await daemon.stop()
        await daemon_task

        # Show final stats
        logger.info("\n" + "=" * 60)
        logger.info("📈 Final Statistics")
        logger.info("=" * 60)

        all_tasks = await daemon.task_store.get_all()
        completed = sum(1 for t in all_tasks if t.state.value == "completed")
        failed = sum(1 for t in all_tasks if t.state.value == "failed")
        pending = sum(1 for t in all_tasks if t.state.value == "pending")

        all_missions = await daemon.mission_store.list_all()
        total_executions = sum(m.execution_count for m in all_missions)
        successful = sum(m.success_count for m in all_missions)
        failures = sum(m.failure_count for m in all_missions)

        logger.info("\nTasks:")
        logger.info(f"  ✅ Completed: {completed}")
        logger.info(f"  ❌ Failed: {failed}")
        logger.info(f"  ⏳ Pending: {pending}")

        logger.info("\nMissions:")
        logger.info(f"  🔄 Total executions: {total_executions}")
        logger.info(f"  ✅ Successful: {successful}")
        logger.info(f"  ❌ Failed: {failures}")

        logger.info("\n👋 Daemon stopped cleanly")
        logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)

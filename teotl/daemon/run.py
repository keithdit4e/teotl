"""
Command-line runner for Forge agent daemon.

This module provides a CLI entry point to start an agent daemon from a config file.
"""

import argparse
import asyncio
import contextlib
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any

import yaml

from teotl.daemon.executor import create_simple_executor
from teotl.daemon.heartbeat import HeartbeatDaemon
from teotl.primitives.discovery import LocalDiscovery
from teotl.primitives.missions import Mission, MissionInterval
from teotl.primitives.tasks import Priority, Task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from YAML file."""
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def get_provider(provider_config: dict[str, Any]):
    """Create provider instance from config."""
    provider_type = provider_config["type"]
    model = provider_config.get("model")
    api_key_env = provider_config.get("api_key_env")

    # Get API key from environment
    api_key = None
    if api_key_env:
        api_key = os.getenv(api_key_env)
        if not api_key:
            logger.error(f"API key not found in environment: {api_key_env}")
            sys.exit(1)

    if provider_type == "anthropic":
        from teotl.core.provider import AnthropicProvider

        return AnthropicProvider(model=model, api_key=api_key)
    elif provider_type == "openai":
        from teotl.core.provider import OpenAIProvider

        return OpenAIProvider(model=model, api_key=api_key)
    elif provider_type == "ollama":
        from teotl.core.provider import OllamaProvider

        return OllamaProvider(model=model or "llama3")
    else:
        logger.error(f"Unknown provider type: {provider_type}")
        sys.exit(1)


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize single-agent config to multi-agent format."""
    # If config has "agent" (singular), convert to "agents" (plural)
    if "agent" in config and "agents" not in config:
        agent_config = config["agent"]
        agent_id = agent_config.get("agent_id", "default")
        config["agents"] = {agent_id: agent_config}
        del config["agent"]

    return config


async def load_initial_tasks(daemon: HeartbeatDaemon, tasks_config: list[dict[str, Any]]):
    """Load initial tasks from config."""
    for task_config in tasks_config:
        task = Task(
            description=task_config["description"],
            priority=Priority[task_config.get("priority", "NORMAL")],
            context=task_config.get("context", {}),
        )

        # Set expiration if provided
        if "expires_minutes" in task_config:
            from datetime import datetime, timedelta

            task.expires_at = datetime.now() + timedelta(minutes=task_config["expires_minutes"])

        await daemon.task_store.create(task)
        logger.info(f"✅ Loaded task: {task.description}")


async def load_initial_missions(daemon: HeartbeatDaemon, missions_config: list[dict[str, Any]]):
    """Load initial missions from config."""
    for mission_config in missions_config:
        from datetime import datetime, timedelta

        interval = MissionInterval[mission_config.get("interval", "DAILY")]

        # Calculate next execution based on interval
        if interval == MissionInterval.HOURLY:
            next_exec = datetime.now() + timedelta(hours=1)
        elif interval == MissionInterval.DAILY:
            next_exec = datetime.now() + timedelta(days=1)
        elif interval == MissionInterval.WEEKLY:
            next_exec = datetime.now() + timedelta(weeks=1)
        else:
            next_exec = datetime.now() + timedelta(hours=1)

        mission = Mission(
            description=mission_config["description"],
            interval=interval,
            next_execution_at=next_exec,
            can_be_interrupted=mission_config.get("can_be_interrupted", True),
            interrupt_threshold=Priority[mission_config.get("interrupt_threshold", "URGENT")],
        )

        await daemon.mission_store.create(mission)
        logger.info(f"📅 Loaded mission: {mission.description}")


async def run_daemon(config_path: Path, agent_id: str | None = None):
    """Run the agent daemon."""
    # Load config
    config = load_config(config_path)
    config = normalize_config(config)

    # Determine which agent to run
    agents_config = config.get("agents", {})

    if not agents_config:
        logger.error("No agents defined in configuration")
        sys.exit(1)

    # If agent_id not specified and only one agent, use that
    if agent_id is None:
        if len(agents_config) == 1:
            agent_id = list(agents_config.keys())[0]
        else:
            logger.error(
                f"Multiple agents defined. Please specify --agent-id from: {', '.join(agents_config.keys())}"
            )
            sys.exit(1)

    # Get agent config
    if agent_id not in agents_config:
        logger.error(
            f"Agent '{agent_id}' not found in configuration. Available: {', '.join(agents_config.keys())}"
        )
        sys.exit(1)

    agent_config = agents_config[agent_id]

    logger.info("🤖 Forge Agent Daemon Starting...")
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  Agent ID: {agent_id}")
    logger.info(
        f"  Provider: {config['provider']['type']} ({config['provider'].get('model', 'default')})"
    )
    logger.info(f"  Poll Interval: {config.get('daemon', {}).get('poll_interval', 30)} seconds")

    # Get data directory
    workspace = agent_config.get("workspace") or config.get("daemon", {}).get(
        "data_dir", f"~/.forge/{agent_id}"
    )
    data_dir = Path(workspace).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"  Data Directory: {data_dir}")
    logger.info("")

    # Create provider
    provider = get_provider(config["provider"])

    # Initialize memory if enabled
    memory = None
    memory_config = agent_config.get("memory", {})
    if memory_config.get("enabled", False):
        try:
            from teotl.primitives.memory.local import LocalMemory

            memory_path = data_dir / "memory.db"
            memory = LocalMemory(path=memory_path)
            logger.info(f"✓ Memory initialized: {memory_path}")
        except Exception as e:
            logger.warning(f"Failed to initialize memory: {e}")
            logger.warning("Continuing without memory")

    # Get janitor configuration
    janitor_config = agent_config.get("janitor", {})
    enable_auto_compact = janitor_config.get("enabled")  # None = auto (enables with memory)
    compact_every = janitor_config.get("compact_every", 15)
    max_context_tokens = janitor_config.get("max_context_tokens")  # None = auto-detect

    # Get harness feature flags
    harness_config = agent_config.get("harness", {})
    enable_cost_tracking = harness_config.get("cost_tracking", False)
    enable_checkpoints = harness_config.get("checkpoints", False)
    enable_heartbeat = harness_config.get("heartbeat", False)
    enable_state = harness_config.get("state", False)

    # Log enabled features
    if memory:
        logger.info(f"✓ Memory enabled (compact every {compact_every} turns)")
    enabled_harness = [k for k, v in harness_config.items() if v]
    if enabled_harness:
        logger.info(f"✓ Harness features: {', '.join(enabled_harness)}")

    # Create executor
    executor = create_simple_executor(
        provider=provider,
        instructions=agent_config.get("instructions", "You are a helpful AI assistant."),
        skills=agent_config.get("skills", []),
        workspace_dir=data_dir,  # Load workspace files from agent's data directory
        auto_approve=agent_config.get("auto_approve", True),
        # Memory and janitor
        memory=memory,
        enable_auto_compact=enable_auto_compact,
        compact_every=compact_every,
        max_context_tokens=max_context_tokens,
        # Harness features
        enable_cost_tracking=enable_cost_tracking,
        enable_checkpoints=enable_checkpoints,
        enable_heartbeat=enable_heartbeat,
        enable_state=enable_state,
    )

    # Create daemon
    daemon = HeartbeatDaemon(
        agent_id=agent_id,
        agent_executor=executor,
        data_dir=data_dir,
        poll_interval=config.get("daemon", {}).get("poll_interval", 30),
    )

    # Load initial tasks and missions if this is first run
    initial_tasks = config.get("tasks", [])
    initial_missions = config.get("missions", [])

    if initial_tasks:
        await load_initial_tasks(daemon, initial_tasks)

    if initial_missions:
        await load_initial_missions(daemon, initial_missions)

    # Register with discovery service if multi-agent
    if len(agents_config) > 1:
        discovery = LocalDiscovery()
        port = agent_config.get("port", 8000)
        endpoint = f"http://localhost:{port}/a2a"

        await discovery.register(
            agent_id=agent_id,
            endpoint=endpoint,
            capabilities=agent_config.get("capabilities", []),
            workspace=str(data_dir),
        )
        logger.info(f"✓ Registered with discovery service: {endpoint}")
        logger.info("")

    # Start daemon
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ FORGE AGENT DAEMON STARTED SUCCESSFULLY")
    logger.info("=" * 70)
    logger.info(f"Agent ID:        {agent_id}")
    logger.info(f"Process ID:      {os.getpid()}")
    logger.info(f"Data Directory:  {data_dir}")
    logger.info(f"Poll Interval:   {config.get('daemon', {}).get('poll_interval', 30)}s")
    logger.info(
        f"Provider:        {config['provider']['type']} ({config['provider'].get('model', 'default')})"
    )
    logger.info("=" * 70)
    logger.info("")
    logger.info("✓ Task store initialized")
    logger.info("✓ Mission store initialized")
    if initial_tasks:
        logger.info(f"✓ Loaded {len(initial_tasks)} initial task(s)")
    if initial_missions:
        logger.info(f"✓ Loaded {len(initial_missions)} initial mission(s)")
    logger.info("")
    logger.info("Daemon is now running. Press Ctrl+C to stop gracefully.")
    logger.info("")

    # Handle shutdown signals
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("")
        logger.info("Received shutdown signal (SIGINT/SIGTERM)")
        shutdown_event.set()

    # Use asyncio's signal handling (works better with event loop)
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Start daemon in background
    daemon_task = asyncio.create_task(daemon.start())

    try:
        # Wait for shutdown signal
        await shutdown_event.wait()
    except Exception as e:
        logger.error(f"Error during daemon execution: {e}")
    finally:
        logger.info("Shutting down gracefully...")

        # Unregister from discovery
        if len(agents_config) > 1:
            discovery = LocalDiscovery()
            await discovery.unregister(agent_id)
            logger.info("✓ Unregistered from discovery service")

        # Stop daemon
        await daemon.stop()

        # Wait for daemon task to complete
        try:
            await asyncio.wait_for(daemon_task, timeout=5.0)
        except TimeoutError:
            logger.warning("Daemon shutdown timed out, cancelling task")
            daemon_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await daemon_task

        logger.info("✓ Stopped heartbeat daemon")
        logger.info("✓ Closed database connections")
        logger.info("✓ Daemon stopped cleanly")
        logger.info("")
        logger.info("Goodbye!")

        # Explicitly exit
        sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Forge agent daemon")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to configuration file (config.yaml)",
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        help="Agent ID to run (required for multi-agent configs)",
    )

    args = parser.parse_args()

    # Run daemon
    asyncio.run(run_daemon(args.config, args.agent_id))


if __name__ == "__main__":
    main()

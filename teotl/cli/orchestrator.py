"""Multi-agent orchestrator CLI command.

Usage:
    forge start                    # Start all agents from config.yaml
    forge start personal           # Start specific agent
    forge start personal work      # Start multiple specific agents
    forge status                   # Show status of all agents
    forge stop                     # Stop all running agents
"""

import asyncio
import sys

from teotl.config.multi_agent import load_multi_agent_config
from teotl.primitives.discovery import LocalDiscovery


class Color:
    """ANSI color codes."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Color.GREEN}✓{Color.END} {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Color.RED}✗{Color.END} {text}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Color.CYAN}ℹ{Color.END} {text}")


async def start_agents(config_path: str = "config.yaml", agent_ids: list[str] | None = None):
    """Start one or more agents from config.

    Args:
        config_path: Path to config file
        agent_ids: List of specific agent IDs to start (None = all)
    """
    try:
        config = load_multi_agent_config(config_path)
    except FileNotFoundError:
        print_error(f"Config file not found: {config_path}")
        print_info("Run 'forge onboard' to create a configuration")
        sys.exit(1)
    except ValueError as e:
        print_error(f"Invalid config: {e}")
        sys.exit(1)

    # Determine which agents to start
    if agent_ids:
        agents_to_start = {aid: config.get_agent(aid) for aid in agent_ids if config.get_agent(aid)}

        # Check for invalid agent IDs
        invalid_ids = set(agent_ids) - set(agents_to_start.keys())
        if invalid_ids:
            print_error(f"Unknown agent IDs: {', '.join(invalid_ids)}")
            print_info(f"Available agents: {', '.join(config.agent_ids)}")
            sys.exit(1)
    else:
        agents_to_start = config.agents

    if not agents_to_start:
        print_error("No agents to start")
        sys.exit(1)

    print(f"\n{Color.BOLD}Starting {len(agents_to_start)} agent(s)...{Color.END}\n")

    # TODO: Actually start the agents as daemons
    # For now, just print what would be started
    for agent_id, agent_config in agents_to_start.items():
        print_success(f"Would start: {agent_id}")
        print(f"  Instructions: {agent_config.instructions[:60]}...")
        print(f"  Workspace: {agent_config.workspace or f'~/.forge/{agent_id}'}")

        if agent_config.skills:
            print(f"  Skills: {', '.join(agent_config.skills)}")

        print()

    print_info(
        "Multi-agent orchestration is under development. "
        "Use 'python -m forge.daemon.run' to start a single agent for now."
    )


async def show_status():
    """Show status of all registered agents."""
    discovery = LocalDiscovery()

    try:
        agents = await discovery.list_all()

        if not agents:
            print_info("No agents currently registered")
            print_info("Start agents with: forge start")
            return

        print(f"\n{Color.BOLD}Registered Agents:{Color.END}\n")

        for agent in agents:
            # Check if agent is still running
            is_healthy = await discovery.health_check()

            status_symbol = (
                f"{Color.GREEN}●{Color.END}" if is_healthy else f"{Color.RED}●{Color.END}"
            )
            print(f"{status_symbol} {Color.BOLD}{agent.agent_id}{Color.END}")
            print(f"  Endpoint: {agent.endpoint}")

            if agent.capabilities:
                print(f"  Capabilities: {', '.join(agent.capabilities)}")

            if agent.pid:
                print(f"  PID: {agent.pid}")

            print(f"  Last heartbeat: {agent.last_heartbeat}")
            print()

    except Exception as e:
        print_error(f"Failed to get agent status: {e}")
        sys.exit(1)


async def stop_agents(agent_ids: list[str] | None = None):
    """Stop one or more running agents.

    Args:
        agent_ids: List of specific agent IDs to stop (None = all)
    """
    discovery = LocalDiscovery()

    try:
        if agent_ids:
            agents = [await discovery.find_by_id(aid) for aid in agent_ids]
            agents = [a for a in agents if a]  # Filter None

            if not agents:
                print_error("No matching agents found")
                sys.exit(1)
        else:
            agents = await discovery.list_all()

        if not agents:
            print_info("No agents to stop")
            return

        print(f"\n{Color.BOLD}Stopping {len(agents)} agent(s)...{Color.END}\n")

        for agent in agents:
            # TODO: Send stop signal to agent process
            # For now, just unregister
            await discovery.unregister(agent.agent_id)
            print_success(f"Unregistered: {agent.agent_id}")

    except Exception as e:
        print_error(f"Failed to stop agents: {e}")
        sys.exit(1)


def main_start(args: list[str]):
    """Handle 'forge start' command."""
    config_path = "config.yaml"
    agent_ids = args if args else None

    asyncio.run(start_agents(config_path, agent_ids))


def main_status(args: list[str]):
    """Handle 'forge status' command."""
    asyncio.run(show_status())


def main_stop(args: list[str]):
    """Handle 'forge stop' command."""
    agent_ids = args if args else None
    asyncio.run(stop_agents(agent_ids))


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) < 2:
        print("Usage: forge [start|status|stop] [agent_ids...]")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    if command == "start":
        main_start(args)
    elif command == "status":
        main_status(args)
    elif command == "stop":
        main_stop(args)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: start, status, stop")
        sys.exit(1)

"""Entry point for running the dashboard as a module."""

import argparse
import asyncio
import sys
from pathlib import Path

from teotl.web.server import DashboardServer


def discover_agents() -> dict[str, Path]:
    """Auto-discover agents in ~/.forge directory.

    Returns:
        Dict mapping agent_id -> data_dir path
    """
    forge_dir = Path.home() / ".forge"

    if not forge_dir.exists():
        return {}

    agents = {}

    # Check for single-agent setup (databases directly in ~/.forge/)
    if (forge_dir / "tasks.db").exists():
        agents["default"] = forge_dir

    # Check for multi-agent setup (databases in ~/.forge/agents/*)
    agents_dir = forge_dir / "agents"
    if agents_dir.exists() and agents_dir.is_dir():
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir() and (agent_dir / "tasks.db").exists():
                agents[agent_dir.name] = agent_dir

    return agents


def filter_agents(discovered: dict[str, Path], agent_filter: str | None) -> dict[str, Path]:
    """Filter discovered agents based on user input.

    Args:
        discovered: All discovered agents
        agent_filter: Comma-separated list of agent IDs to monitor

    Returns:
        Filtered dict of agents
    """
    if not agent_filter:
        return discovered

    # Parse filter
    requested = [a.strip() for a in agent_filter.split(",")]

    # Filter agents
    filtered = {}
    for agent_id in requested:
        if agent_id in discovered:
            filtered[agent_id] = discovered[agent_id]
        else:
            print(f"⚠️  Warning: Agent '{agent_id}' not found, skipping")

    return filtered


def main():
    """Run the dashboard server."""
    parser = argparse.ArgumentParser(
        description="Forge Agent Dashboard - Monitor multiple agents",
        epilog="""
Examples:
  # Auto-detect and monitor all agents
  python3 -m forge.web

  # Monitor specific agents
  python3 -m forge.web --agents personal,work

  # Monitor single agent
  python3 -m forge.web --agents personal

  # Custom port
  python3 -m forge.web --port 3000

  # Manual data directory (legacy single-agent mode)
  python3 -m forge.web --data-dir ~/.forge/my-agent
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="(Legacy) Path to single agent data directory",
    )
    parser.add_argument(
        "--agents",
        type=str,
        help="Comma-separated list of agent IDs to monitor (e.g., personal,work). If not specified, monitors all discovered agents.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to run dashboard on (default: 8080)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host to bind to (default: localhost)",
    )

    args = parser.parse_args()

    # Determine which agents to monitor
    if args.data_dir:
        # Legacy mode: single data directory
        data_dir = Path(args.data_dir).expanduser()

        if not data_dir.exists():
            print(f"❌ Error: Data directory not found: {data_dir}")
            sys.exit(1)

        if not (data_dir / "tasks.db").exists():
            print(f"❌ Error: No tasks.db found in {data_dir}")
            sys.exit(1)

        agents = {data_dir.name: data_dir}
        print(f"📁 Legacy mode: Monitoring single agent from {data_dir}")

    else:
        # Auto-discovery mode
        print("🔍 Auto-discovering agents...")
        discovered = discover_agents()

        if not discovered:
            print("❌ Error: No agents found!")
            print("")
            print("Please ensure:")
            print("  1. You have run an agent at least once")
            print("  2. Agent data exists in ~/.forge/ or ~/.forge/agents/")
            print("  3. Or specify --data-dir manually")
            sys.exit(1)

        print(f"✅ Found {len(discovered)} agent(s): {', '.join(discovered.keys())}")

        # Apply filter if specified
        agents = filter_agents(discovered, args.agents)

        if not agents:
            print("❌ Error: No agents match the filter!")
            print(f"Available agents: {', '.join(discovered.keys())}")
            sys.exit(1)

        if args.agents:
            print(f"🎯 Filtering to {len(agents)} agent(s): {', '.join(agents.keys())}")

    # Validate all agents
    for agent_id, data_dir in agents.items():
        if not (data_dir / "tasks.db").exists():
            print(f"❌ Error: Agent '{agent_id}' missing tasks.db in {data_dir}")
            sys.exit(1)

    # Create and run server
    print("")
    print("🚀 Starting Forge Dashboard")
    print(f"📊 Monitoring {len(agents)} agent(s): {', '.join(agents.keys())}")
    print(f"🌐 Dashboard: http://{args.host}:{args.port}")
    print("")
    print("Press Ctrl+C to stop")
    print("")

    server = DashboardServer(
        agents=agents,
        host=args.host,
        port=args.port,
    )

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n\n✋ Shutting down dashboard...")
        server.close()
        print("👋 Dashboard stopped")


if __name__ == "__main__":
    main()

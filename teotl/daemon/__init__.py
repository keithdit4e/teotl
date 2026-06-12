"""Autonomous agent daemon for scheduled mission execution."""

from teotl.daemon.agent_daemon import AgentDaemon
from teotl.daemon.executor import (
    AgentExecutor,
    AgentExecutorFactory,
    create_simple_executor,
)

# Backward compatibility alias
HeartbeatDaemon = AgentDaemon

__all__ = [
    "AgentDaemon",
    "HeartbeatDaemon",  # Deprecated, use AgentDaemon
    "AgentExecutor",
    "AgentExecutorFactory",
    "create_simple_executor",
]

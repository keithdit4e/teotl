"""Agent-to-Agent (A2A) communication protocol.

Simple HTTP-based protocol for agents to communicate and delegate tasks.
"""

from teotl.primitives.a2a.client import A2AClient
from teotl.primitives.a2a.protocol import (
    A2ARequest,
    A2AResponse,
    A2AStatus,
    TaskPriority,
)
from teotl.primitives.a2a.server import A2AServer

__all__ = [
    "A2AClient",
    "A2AServer",
    "A2ARequest",
    "A2AResponse",
    "A2AStatus",
    "TaskPriority",
]

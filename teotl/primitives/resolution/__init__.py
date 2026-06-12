"""Resolution service interface for agent discovery.

The resolution service is external to the agent framework and will be implemented
as a standalone project. This module defines the interface that agents use to
discover and communicate with each other.

Agents can work without a resolution service (hardcoded endpoints, direct config),
but it enables dynamic multi-agent architectures with auto-scaling.
"""

from teotl.primitives.resolution.interface import (
    AgentEndpoint,
    AgentNotFoundError,
    AgentRegistration,
    ResolutionService,
)
from teotl.primitives.resolution.mock import MockResolutionService

__all__ = [
    "AgentEndpoint",
    "AgentNotFoundError",
    "AgentRegistration",
    "ResolutionService",
    "MockResolutionService",
]

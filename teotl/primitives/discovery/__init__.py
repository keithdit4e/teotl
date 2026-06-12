"""Local agent discovery for multi-agent coordination.

Simple file-based agent registry for personal and small team deployments.
No orchestration service required.
"""

from teotl.primitives.discovery.local import LocalDiscovery

__all__ = ["LocalDiscovery"]

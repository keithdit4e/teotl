"""Extension loading and lifecycle management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from teotl.core.types import Extension

logger = logging.getLogger(__name__)


class ExtensionManager:
    """
    Manages extension lifecycle: loading, activation, deactivation.

    Extensions hook into the agent's event bus to modify behavior
    without changing core code.
    """

    def __init__(self, extensions: list[Extension] | None = None) -> None:
        self._extensions: dict[str, Extension] = {}
        for ext in extensions or []:
            self.register(ext)

    def register(self, extension: Extension) -> None:
        """Register an extension (does not activate it yet)."""
        self._extensions[extension.name] = extension
        logger.debug(f"Registered extension: {extension.name} v{extension.version}")

    def activate_all(self, agent: Any) -> None:
        """Activate all registered extensions on an agent."""
        for ext in self._extensions.values():
            try:
                ext.activate(agent)
                logger.info(f"Activated extension: {ext.name}")
            except Exception as e:
                logger.error(f"Failed to activate {ext.name}: {e}")

    def deactivate_all(self, agent: Any) -> None:
        """Deactivate all extensions."""
        for ext in self._extensions.values():
            try:
                ext.deactivate(agent)
            except Exception as e:
                logger.error(f"Failed to deactivate {ext.name}: {e}")

    def get(self, name: str) -> Extension | None:
        return self._extensions.get(name)

    @property
    def names(self) -> list[str]:
        return list(self._extensions.keys())

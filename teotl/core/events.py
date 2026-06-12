"""Event bus and hook system. The nervous system of Forge."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from teotl.core.types import EventResult

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[..., Awaitable[EventResult]]


# Available events and their descriptions
EVENTS = {
    "turn_start": "Before LLM call. Inject context here.",
    "turn_end": "After LLM responds. Extract memories here.",
    "tool_call": "Before tool execution. Guardrails hook here.",
    "tool_result": "After tool execution. Filter output here.",
    "session_start": "New session begins.",
    "session_end": "Session ends. Persist state here.",
    "compact": "Context window is getting full. Summarize.",
    "error": "Something went wrong.",
    "bash_spawn": "Before subprocess exec. Sandbox hook.",
}


class EventBus:
    """
    Typed async event bus. Extensions hook into this.

    Handlers are called in priority order (lower = first).
    Any handler can block execution by setting blocked=True on the result.

    Usage:
        bus = EventBus()
        bus.on("tool_call", my_handler, priority=0)
        result = await bus.emit("tool_call", tool_call_data, ui=ui)
        if result.blocked:
            # Handle blocked event
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[tuple[int, EventHandler]]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler, *, priority: int = 0) -> None:
        """
        Register a handler for an event.

        Args:
            event: Event name (see EVENTS dict for available events).
            handler: Async callable that receives an EventResult and returns one.
            priority: Lower priority = runs first. Default 0.
        """
        self._handlers[event].append((priority, handler))
        self._handlers[event].sort(key=lambda x: x[0])
        logger.debug(f"Registered handler for '{event}' at priority {priority}")

    def off(self, event: str, handler: EventHandler) -> None:
        """Remove a handler for an event."""
        self._handlers[event] = [(p, h) for p, h in self._handlers[event] if h is not handler]

    async def emit(self, event: str, data: Any = None, **kwargs: Any) -> EventResult:
        """
        Emit an event. Handlers are called in priority order.

        Any handler can:
        - Modify the data (set result.data)
        - Block execution (set result.blocked = True)
        - Add metadata (set result.modified = True)

        If a handler blocks, subsequent handlers are NOT called.

        Args:
            event: Event name.
            data: Event payload (tool call, message, etc.).
            **kwargs: Additional context (ui, session, etc.).

        Returns:
            EventResult with final state after all handlers.
        """
        result = EventResult(data=data)

        handlers = self._handlers.get(event, [])
        if not handlers:
            return result

        for _, handler in handlers:
            try:
                result = await handler(result, **kwargs)
            except Exception as e:
                logger.error(f"Error in handler for '{event}': {e}", exc_info=True)
                # Don't let a broken handler crash the agent
                continue

            if result.blocked:
                logger.info(f"Event '{event}' blocked: {result.reason}")
                break

        return result

    def has_handlers(self, event: str) -> bool:
        """Check if any handlers are registered for an event."""
        return bool(self._handlers.get(event))

    def clear(self, event: str | None = None) -> None:
        """Clear handlers. If event is None, clear all."""
        if event is None:
            self._handlers.clear()
        else:
            self._handlers.pop(event, None)

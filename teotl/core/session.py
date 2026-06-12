"""Append-only JSONL session management."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import ulid

from teotl.core.types import Message, Role

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


class Session:
    """
    Append-only session log. Never mutate, only append.

    Supports:
    - JSONL persistence (one message per line)
    - Branching via id/parent_id tree
    - Compaction (summarize old messages, preserve full log)
    - Token-budget-aware message retrieval
    """

    def __init__(self, path: Path | None = None) -> None:
        self.id: str = ulid.new().str
        self.path = path
        self.messages: list[Message] = []
        self.created: datetime = datetime.now()

        if path and path.exists():
            self._load()

    def append(self, message: Message) -> None:
        """Append a message to the session."""
        self.messages.append(message)
        if self.path:
            self._persist(message)

    def add_user(self, content: str) -> Message:
        """Add a user message."""
        msg = Message(
            id=ulid.new().str,
            role=Role.USER,
            content=content,
            parent_id=self.messages[-1].id if self.messages else None,
        )
        self.append(msg)
        return msg

    def add_assistant(self, content: str, **kwargs: Any) -> Message:
        """Add an assistant message."""
        msg = Message(
            id=ulid.new().str,
            role=Role.ASSISTANT,
            content=content,
            parent_id=self.messages[-1].id if self.messages else None,
            **kwargs,
        )
        self.append(msg)
        return msg

    def add_system(self, content: str) -> Message:
        """Add a system message."""
        msg = Message(
            id=ulid.new().str,
            role=Role.SYSTEM,
            content=content,
        )
        self.append(msg)
        return msg

    def get_messages(self, *, token_budget: int | None = None) -> list[Message]:
        """
        Get messages for context window, respecting optional token budget.

        If budget is set, walks backward from newest messages filling budget.
        Always includes system messages.
        """
        if token_budget is None:
            return list(self.messages)

        # Always include system messages
        system_msgs = [m for m in self.messages if m.role == Role.SYSTEM]
        non_system = [m for m in self.messages if m.role != Role.SYSTEM]

        system_tokens = sum(_estimate_tokens(m.content) for m in system_msgs)
        remaining_budget = token_budget - system_tokens

        # Walk backward from newest, filling budget
        selected: list[Message] = []
        tokens = 0
        for msg in reversed(non_system):
            msg_tokens = _estimate_tokens(msg.content)
            if tokens + msg_tokens > remaining_budget:
                break
            selected.insert(0, msg)
            tokens += msg_tokens

        return system_msgs + selected

    def get_context_messages(self) -> list[dict[str, str]]:
        """Get messages formatted for LLM API calls."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.messages
            if msg.role != Role.SYSTEM
        ]

    def get_system_prompt(self) -> str:
        """Combine all system messages into one prompt."""
        system_msgs = [m for m in self.messages if m.role == Role.SYSTEM]
        return "\n\n".join(m.content for m in system_msgs)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def estimated_tokens(self) -> int:
        return sum(_estimate_tokens(m.content) for m in self.messages)

    def _persist(self, message: Message) -> None:
        """Append a single message to the JSONL file."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file is new (need to set permissions)
            is_new_file = not self.path.exists()

            with open(self.path, "a") as f:
                data = {
                    "id": message.id,
                    "parent_id": message.parent_id,
                    "role": message.role.value,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "metadata": message.metadata,
                    "compact": message.compact,
                }
                f.write(json.dumps(data) + "\n")

            # Set restrictive permissions (owner read/write only)
            if is_new_file:
                self.path.chmod(0o600)
                logger.debug(f"Set session file permissions to 0600: {self.path}")
        except Exception as e:
            logger.error(f"Failed to persist message: {e}")

    def _load(self) -> None:
        """Load messages from JSONL file."""
        try:
            with open(self.path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    self.messages.append(
                        Message(
                            id=data["id"],
                            parent_id=data.get("parent_id"),
                            role=Role(data["role"]),
                            content=data["content"],
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            metadata=data.get("metadata", {}),
                            compact=data.get("compact", False),
                        )
                    )
        except Exception as e:
            logger.error(f"Failed to load session: {e}")

    def format_for_extraction(self) -> str:
        """Format session for memory extraction."""
        lines = []
        for msg in self.messages:
            if msg.role == Role.SYSTEM:
                continue
            prefix = "User" if msg.role == Role.USER else "Assistant"
            lines.append(f"{prefix}: {msg.content}")
        return "\n\n".join(lines)

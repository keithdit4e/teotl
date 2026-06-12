"""Core type definitions used throughout Forge."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ActionType(StrEnum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    DESTRUCTIVE = "destructive"


class Decision(StrEnum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    BLOCK = "block"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Tool types
# ---------------------------------------------------------------------------


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""

    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool call."""

    call_id: str
    output: str = ""
    error: str | None = None
    is_error: bool = False


@dataclass
class ToolDefinition:
    """Schema for a tool the LLM can call."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Action classification (for guardrails)
# ---------------------------------------------------------------------------


@dataclass
class Action:
    """Classified action from a tool call."""

    type: ActionType
    target: str = ""
    risk: RiskLevel = RiskLevel.LOW
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------


@dataclass
class Message:
    """A single message in a session."""

    id: str
    role: Role
    content: str
    parent_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    compact: bool = False  # True if this is a compaction summary


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


@dataclass
class Response:
    """Final response from the agent."""

    text: str
    messages: list[Message] = field(default_factory=list)
    tool_calls_made: list[ToolCall] = field(default_factory=list)
    tokens_used: int = 0
    cost: float = 0.0


# ---------------------------------------------------------------------------
# Completion result (from provider)
# ---------------------------------------------------------------------------


@dataclass
class CompletionResult:
    """Raw result from an LLM provider."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    done: bool = True  # False if tool calls need processing
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None  # Provider-specific raw response


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


@dataclass
class EventResult:
    """Result of emitting an event through the bus."""

    data: Any = None
    blocked: bool = False
    reason: str = ""
    modified: bool = False


# ---------------------------------------------------------------------------
# Protocols (interfaces)
# ---------------------------------------------------------------------------


@runtime_checkable
class Extension(Protocol):
    """All extensions implement this interface."""

    name: str
    version: str

    def activate(self, agent: Any) -> None:
        """Register hooks, modify agent behavior."""
        ...

    def deactivate(self, agent: Any) -> None:
        """Clean up."""
        ...


@runtime_checkable
class UI(Protocol):
    """Abstract UI interface for agent interactions."""

    async def confirm(self, message: str, *, title: str = "") -> bool:
        """Ask user for confirmation. Returns True if approved."""
        ...

    async def display(self, message: str) -> None:
        """Display a message to the user."""
        ...

    async def input(self, prompt: str = "") -> str:
        """Get text input from the user."""
        ...

    async def error(self, message: str) -> None:
        """Display an error message."""
        ...


# ---------------------------------------------------------------------------
# Memory types
# ---------------------------------------------------------------------------


class MemoryMeta(BaseModel):
    """Metadata for a stored memory."""

    source: str = "manual"  # "session", "manual", "import"
    tags: list[str] = field(default_factory=list)
    importance: int = 5  # 1-10
    session_id: str | None = None


class Memory(BaseModel):
    """A single memory entry."""

    id: str
    content: str
    metadata: MemoryMeta = MemoryMeta()
    created: datetime = field(default_factory=datetime.now)
    last_accessed: datetime | None = None
    access_count: int = 0
    expires_at: datetime | None = None  # When memory expires (None = never)


# ---------------------------------------------------------------------------
# Skill types
# ---------------------------------------------------------------------------


@dataclass
class SkillMeta:
    """Parsed frontmatter from a SKILL.md file."""

    name: str
    description: str
    path: Any  # Path, but avoiding import here
    version: str = "0.1.0"
    auth: str = "none"  # "none", "api_key", "oauth2"
    triggers: list[str] = field(default_factory=list)


@dataclass
class SkillFull:
    """Fully loaded skill with instructions."""

    meta: SkillMeta
    instructions: str  # Full SKILL.md body

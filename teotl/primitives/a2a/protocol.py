"""Agent-to-Agent (A2A) protocol definitions.

Simple protocol for agents to send tasks to each other via HTTP.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class TaskPriority(StrEnum):
    """Task priority levels for A2A requests."""

    CRITICAL = "CRITICAL"
    URGENT = "URGENT"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class A2AStatus(StrEnum):
    """Status of A2A request/response."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class A2ARequest(BaseModel):
    """Request from one agent to another.

    Example:
        request = A2ARequest(
            requester_agent_id="personal-agent",
            task_description="Send email to john@example.com with meeting notes",
            priority=TaskPriority.HIGH,
            context={"recipient": "john@example.com", "subject": "Meeting Notes"},
        )
    """

    requester_agent_id: str  # Who is requesting
    task_description: str  # What to do
    priority: TaskPriority = TaskPriority.NORMAL
    context: dict[str, Any] = {}  # Additional data
    timeout_seconds: int | None = None  # Max time to wait for response
    callback_url: str | None = None  # URL to send result to (async)


class A2AResponse(BaseModel):
    """Response from agent after processing A2A request.

    Example:
        response = A2AResponse(
            status=A2AStatus.COMPLETED,
            result={"message_id": "msg_123", "sent_at": "2026-03-25T10:00:00Z"},
            message="Email sent successfully",
        )
    """

    status: A2AStatus
    result: dict[str, Any] | None = None
    message: str | None = None
    error: str | None = None
    task_id: str | None = None  # ID for tracking async tasks

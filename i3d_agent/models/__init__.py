"""
Models package for i3d-agent-system.

This package contains all Pydantic models used throughout the system.
"""

from i3d_agent.models.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    SourceDocument,
    SUPPORTED_TENANTS,
)
from i3d_agent.models.task import (
    AgentTask,
    TaskCreate,
    TaskStatus,
    TaskType,
    TaskUpdate,
)

__all__ = [
    "Message",
    "ChatRequest",
    "SourceDocument",
    "ChatResponse",
    "SUPPORTED_TENANTS",
    "TaskType",
    "TaskStatus",
    "AgentTask",
    "TaskCreate",
    "TaskUpdate",
]

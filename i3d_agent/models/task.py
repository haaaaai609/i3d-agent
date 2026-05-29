"""
Task models for i3d-agent-system.

This module defines Pydantic models for task-related operations including
task types, statuses, and task management.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Task type enumeration."""

    SEARCH = "SEARCH"
    RAG = "RAG"
    PROCESS = "PROCESS"


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentTask(BaseModel):
    """Agent task model with all fields."""

    id: str = Field(..., description="Task ID")
    tenant_id: str = Field(..., description="Tenant ID")
    user_id: str = Field(..., description="User ID")
    task_type: TaskType = Field(..., description="Task type")
    task_data: Dict[str, Any] = Field(..., description="Task data")
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Task status"
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Task result"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if task failed"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Task creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Task update timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Task completion timestamp"
    )


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    task_type: TaskType = Field(..., description="Task type")
    task_data: Dict[str, Any] = Field(..., description="Task data")


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    status: Optional[TaskStatus] = Field(default=None, description="Task status")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result")
    error_message: Optional[str] = Field(
        default=None, description="Error message if task failed"
    )

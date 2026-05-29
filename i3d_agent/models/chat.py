"""
Chat models for i3d-agent-system.

This module defines Pydantic models for chat-related operations including
messages, requests, responses, and source documents.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# Supported tenants for the system
# Note: "huabei" is the default tenant as per requirements
SUPPORTED_TENANTS = ["huabei", "default", "tenant1", "tenant2"]


class Message(BaseModel):
    """A chat message with role and content."""

    role: str = Field(
        ...,
        pattern=r"^(user|assistant|system)$",
        description="Message role: user, assistant, or system"
    )
    content: str = Field(
        ...,
        description="Message content",
        min_length=0
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Message timestamp"
    )


class SourceDocument(BaseModel):
    """A source document from RAG retrieval."""

    title: str = Field(..., description="Document title")
    source: str = Field(..., description="Document source/file path")
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score (0-1)"
    )
    chunk_index: Optional[int] = Field(
        default=None,
        description="Chunk index in the document"
    )


class ChatRequest(BaseModel):
    """Request model for chat API."""

    message: str = Field(
        ...,
        description="User message",
        min_length=1
    )
    user_id: str = Field(..., description="User ID")
    tenant_id: str = Field(
        default="huabei",
        description="Tenant ID"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for conversation continuity"
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response"
    )

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Validate tenant_id against SUPPORTED_TENANTS."""
        if v not in SUPPORTED_TENANTS:
            raise ValueError(
                f"tenant_id must be one of {SUPPORTED_TENANTS}, got '{v}'"
            )
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "What is the weather today?",
                    "user_id": "user123",
                    "tenant_id": "huabei",
                    "session_id": "session456",
                    "stream": True
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Response model for chat API."""

    response: str = Field(..., description="AI assistant response")
    sources: Optional[List[SourceDocument]] = Field(
        default=None,
        description="Source documents used for the response"
    )
    thought_process: Optional[str] = Field(
        default=None,
        description="Optional thought process/reasoning"
    )
    session_id: str = Field(..., description="Session ID for the conversation")
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional metadata (model, tokens, etc.)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "The weather is sunny with a high of 75°F.",
                    "sources": [
                        {
                            "title": "Weather Report",
                            "source": "weather.pdf",
                            "score": 0.95,
                            "chunk_index": 0
                        }
                    ],
                    "thought_process": "I searched the weather database and found the current conditions.",
                    "session_id": "session456",
                    "metadata": {
                        "model": "claude-3-5-sonnet-20241022",
                        "tokens": 150
                    }
                }
            ]
        }
    }

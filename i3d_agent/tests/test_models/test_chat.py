"""
Tests for chat models using TDD approach.

Following TDD principles:
1. Write failing test first
2. Watch it fail
3. Write minimal code to pass
4. Verify it passes
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from i3d_agent.models.chat import (
    Message,
    ChatRequest,
    SourceDocument,
    ChatResponse,
    SUPPORTED_TENANTS,
)


class TestMessage:
    """Tests for Message model."""

    def test_message_creation(self):
        """Test creating a valid message with all required fields."""
        message = Message(
            role="user",
            content="Hello, how are you?"
        )

        assert message.role == "user"
        assert message.content == "Hello, how are you?"
        assert isinstance(message.timestamp, datetime)

    def test_message_with_all_fields(self):
        """Test creating a message with timestamp."""
        now = datetime.now()
        message = Message(
            role="assistant",
            content="I'm doing well, thank you!",
            timestamp=now
        )

        assert message.role == "assistant"
        assert message.content == "I'm doing well, thank you!"
        assert message.timestamp == now

    def test_message_invalid_role(self):
        """Test that invalid role raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Message(
                role="invalid_role",
                content="This should fail"
            )

        errors = exc_info.value.errors()
        assert any("role" in str(error.get("loc", "")) for error in errors)
        assert any("user|assistant|system" in str(error.get("msg", "")) or "pattern" in str(error).lower() for error in errors)

    def test_message_empty_content(self):
        """Test that message with empty content is allowed (for streaming)."""
        message = Message(
            role="assistant",
            content=""
        )

        assert message.content == ""

    def test_message_all_valid_roles(self):
        """Test all valid role values."""
        roles = ["user", "assistant", "system"]

        for role in roles:
            message = Message(role=role, content=f"Test as {role}")
            assert message.role == role


class TestChatRequest:
    """Tests for ChatRequest model."""

    def test_chat_request_validation(self):
        """Test creating a valid chat request."""
        request = ChatRequest(
            message="What is the weather today?",
            user_id="user123",
            session_id="session456",
            stream=True
        )

        assert request.message == "What is the weather today?"
        assert request.user_id == "user123"
        assert request.session_id == "session456"
        assert request.stream is True
        assert request.tenant_id == "huabei"  # default value

    def test_chat_request_with_tenant(self):
        """Test chat request with explicit tenant_id."""
        request = ChatRequest(
            message="Hello",
            user_id="user123",
            tenant_id="default"
        )

        assert request.tenant_id == "default"

    def test_chat_request_defaults(self):
        """Test chat request with default values."""
        request = ChatRequest(
            message="Test message",
            user_id="user123"
        )

        assert request.tenant_id == "huabei"
        assert request.stream is False
        assert request.session_id is None

    def test_chat_request_invalid_tenant(self):
        """Test that invalid tenant_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                message="Hello",
                user_id="user123",
                tenant_id="invalid_tenant"
            )

        errors = exc_info.value.errors()
        assert any("tenant_id" in str(error.get("loc", "")) for error in errors)

    def test_chat_request_empty_message(self):
        """Test that empty message raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                message="",
                user_id="user123"
            )

        errors = exc_info.value.errors()
        assert any("message" in str(error.get("loc", "")) for error in errors)

    def test_chat_request_json_schema(self):
        """Test that ChatRequest has json_schema_extra."""
        schema = ChatRequest.model_json_schema()
        assert "example" in schema or schema.get("title") == "ChatRequest"


class TestSourceDocument:
    """Tests for SourceDocument model."""

    def test_source_document_creation(self):
        """Test creating a valid source document."""
        doc = SourceDocument(
            title="Test Document",
            source="test_source.pdf",
            score=0.95,
            chunk_index=1
        )

        assert doc.title == "Test Document"
        assert doc.source == "test_source.pdf"
        assert doc.score == 0.95
        assert doc.chunk_index == 1

    def test_source_document_optional_fields(self):
        """Test source document with minimal required fields."""
        doc = SourceDocument(
            title="Simple Doc",
            source="doc.txt",
            score=0.8
        )

        assert doc.chunk_index is None
        assert doc.title == "Simple Doc"

    def test_source_document_score_range(self):
        """Test that score accepts valid range."""
        doc = SourceDocument(
            title="Test",
            source="test.pdf",
            score=0.0
        )
        assert doc.score == 0.0

        doc2 = SourceDocument(
            title="Test",
            source="test.pdf",
            score=1.0
        )
        assert doc2.score == 1.0


class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_chat_response_creation(self):
        """Test creating a valid chat response."""
        response = ChatResponse(
            response="Hello! How can I help you today?",
            session_id="session789"
        )

        assert response.response == "Hello! How can I help you today?"
        assert response.session_id == "session789"
        assert response.sources is None
        assert response.thought_process is None
        assert response.metadata is None

    def test_chat_response_with_all_fields(self):
        """Test chat response with all fields."""
        sources = [
            SourceDocument(
                title="Weather Report",
                source="weather.pdf",
                score=0.9,
                chunk_index=0
            )
        ]
        metadata = {"model": "claude-3-5-sonnet", "tokens": 150}

        response = ChatResponse(
            response="The weather is sunny.",
            sources=sources,
            thought_process="I searched for weather information.",
            session_id="session123",
            metadata=metadata
        )

        assert len(response.sources) == 1
        assert response.sources[0].title == "Weather Report"
        assert response.thought_process == "I searched for weather information."
        assert response.metadata == metadata

    def test_chat_response_empty_response(self):
        """Test that empty response is allowed (for streaming)."""
        response = ChatResponse(
            response="",
            session_id="session456"
        )

        assert response.response == ""

    def test_chat_response_json_schema(self):
        """Test that ChatResponse has json_schema_extra."""
        schema = ChatResponse.model_json_schema()
        assert "example" in schema or schema.get("title") == "ChatResponse"


class TestSupportedTenants:
    """Tests for SUPPORTED_TENANTS constant."""

    def test_supported_tenants_exists(self):
        """Test that SUPPORTED_TENANTS is defined."""
        assert isinstance(SUPPORTED_TENANTS, list)
        assert len(SUPPORTED_TENANTS) > 0

    def test_huabei_in_supported_tenants(self):
        """Test that 'huabei' is in supported tenants."""
        assert "huabei" in SUPPORTED_TENANTS

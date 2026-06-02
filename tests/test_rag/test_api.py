"""Tests for RAG API routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock, Mock
from httpx import AsyncClient, ASGITransport
from i3d_agent.rag.models import DocumentResponse
from datetime import datetime


@pytest.fixture
def mock_document_manager():
    """Mock DocumentManager."""
    manager = AsyncMock()
    manager.create_document = AsyncMock()
    manager.get_document = AsyncMock()
    manager.update_document = AsyncMock()
    manager.delete_document = AsyncMock()
    manager.restore_document = AsyncMock()
    manager.get_document_history = AsyncMock()
    manager.list_documents = AsyncMock()
    return manager


@pytest.fixture
def mock_rag_controller():
    """Mock AgenticRAGController."""
    controller = AsyncMock()
    controller.retrieve = AsyncMock()
    return controller


@pytest.fixture
def mock_monitor_service():
    """Mock MonitorService."""
    monitor = AsyncMock()
    monitor.get_index_stats = AsyncMock()
    monitor.get_metrics = AsyncMock()
    monitor.get_quality_metrics = AsyncMock()
    monitor.save_feedback = AsyncMock()
    return monitor


@pytest.fixture
def mock_app(mock_document_manager, mock_rag_controller, mock_monitor_service):
    """Create app with mocked dependencies."""
    # Use FastAPI's dependency override
    from i3d_agent.api.main import create_app
    from i3d_agent.rag import document_manager, controller, monitor

    app = create_app()

    # Override the dependencies at the app level
    app.dependency_overrides[i3d_agent.rag.api.get_document_manager] = lambda: mock_document_manager
    app.dependency_overrides[i3d_agent.rag.api.get_rag_controller] = lambda: mock_rag_controller
    app.dependency_overrides[i3d_agent.rag.api.get_monitor_service] = lambda: mock_monitor_service

    yield app

    # Clean up
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_create_document(mock_app):
    """测试创建文档 API"""
    # Mock DocumentManager
    mock_doc = DocumentResponse(
        id="test-doc-id",
        tenant_id="default",
        title="Test Document",
        description=None,
        doc_type="technical",
        source_type=None,
        version=1,
        is_latest=True,
        status="active",
        metadata={},
        tags=[],
        language="zh",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    mock_doc_manager.create_document = AsyncMock(return_value=mock_doc)

    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/rag/documents",
            json={
                "tenant_id": "default",
                "title": "Test Document",
                "content": "Test content",
                "doc_type": "technical"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Document"
        assert data["tenant_id"] == "default"


@pytest.mark.asyncio
async def test_search(mock_app):
    """测试检索 API"""
    # Mock the RAG controller
    mock_result = MagicMock()
    mock_result.query = "test query"
    mock_result.results = []
    mock_result.iterations = 1
    mock_result.query_expansions = []

    mock_rag_controller.retrieve = AsyncMock(return_value=mock_result)

    # Mock embedding service
    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 768)

    with patch('i3d_agent.rag.api.EmbeddingService', return_value=mock_embedding):
        async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/rag/search",
                json={
                    "query": "test query",
                    "tenant_id": "default",
                    "top_k": 10
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert data["query"] == "test query"
            assert data["total"] == 0


@pytest.mark.asyncio
async def test_ask(mock_app):
    """测试问答 API"""
    # Mock the RAG controller with no results (no documents found)
    mock_result = MagicMock()
    mock_result.results = []  # No results found

    mock_rag_controller.retrieve = AsyncMock(return_value=mock_result)

    # Mock embedding service
    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 768)

    with patch('i3d_agent.rag.api.EmbeddingService', return_value=mock_embedding):
        async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/rag/ask",
                json={
                    "question": "How to configure API?",
                    "tenant_id": "default"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert data["status"] == "no_results"


@pytest.mark.asyncio
async def test_ask_with_results(mock_app):
    """测试问答 API - 有结果的情况"""
    # Mock chunk result
    mock_chunk = MagicMock()
    mock_chunk.id = "chunk-1"
    mock_chunk.doc_id = "doc-1"
    mock_chunk.content = "API configuration involves setting environment variables."
    mock_chunk.final_score = 0.95
    mock_chunk.metadata = {"title": "API Configuration Guide"}

    # Mock the RAG controller
    mock_result = MagicMock()
    mock_result.results = [mock_chunk]
    mock_result.iterations = 1
    mock_result.query_expansions = []

    mock_rag_controller.retrieve = AsyncMock(return_value=mock_result)

    # Mock embedding service
    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 768)

    # Mock LLM client
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="To configure the API, you need to set environment variables.")

    with patch('i3d_agent.rag.api.EmbeddingService', return_value=mock_embedding), \
         patch('i3d_agent.rag.api.get_llm_client', return_value=mock_llm):
        async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/rag/ask",
                json={
                    "question": "How to configure API?",
                    "tenant_id": "default"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert data["status"] == "success"
            assert len(data["sources"]) > 0


@pytest.mark.asyncio
async def test_get_document_not_found(mock_app):
    """测试获取不存在的文档"""
    mock_doc_manager.get_document = AsyncMock(return_value=None)

    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
        response = await client.get("/api/v1/rag/documents/nonexistent-id")

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(mock_app):
    """测试删除文档"""
    mock_doc_manager.delete_document = AsyncMock(return_value=None)

    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
        response = await client.delete("/api/v1/rag/documents/test-doc-id")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document deleted successfully"

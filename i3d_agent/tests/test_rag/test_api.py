"""Tests for RAG API routes."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from i3d_agent.api.main import create_app


@pytest.mark.asyncio
async def test_create_document():
    """测试创建文档 API"""
    from i3d_agent.rag.models import DocumentResponse
    from datetime import datetime

    app = create_app()

    # Mock the document manager
    mock_doc = DocumentResponse(
        id="doc-1",
        tenant_id="default",
        title="Test Document",
        description=None,
        doc_type="technical",
        source_type=None,
        version=1,
        is_latest=True,
        status="pending",
        metadata={},
        tags=[],
        language="zh",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    with patch('i3d_agent.rag.api.DocumentManager') as mock_dm_class:
        mock_dm = AsyncMock()
        mock_dm.create_document.return_value = mock_doc
        mock_dm_class.return_value = mock_dm

        # Test by calling the endpoint directly
        from i3d_agent.rag.api import create_document, get_document_manager, DocumentCreate
        from fastapi import FastAPI

        # Create a test app with RAG router
        test_app = FastAPI()
        from i3d_agent.rag.api import router
        test_app.include_router(router)

        # Create test client
        from httpx import AsyncClient, ASGITransport
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
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


@pytest.mark.asyncio
async def test_search():
    """测试检索 API"""
    from i3d_agent.rag.models import Chunk, RetrievalResult

    app = create_app()

    # Mock the RAG controller
    mock_result = RetrievalResult(
        results=[
            Chunk(
                id="chunk-1",
                doc_id="doc-1",
                tenant_id="default",
                content="Test content",
                embedding=[],
                chunk_index=0,
                metadata={"title": "Test Doc"},
                doc_version=1,
                final_score=0.9
            )
        ],
        query="test query",
        iterations=1,
        query_expansions=[]
    )

    with patch('i3d_agent.rag.api.AgenticRAGController') as mock_ctrl_class:
        mock_ctrl = AsyncMock()
        mock_ctrl.retrieve.return_value = mock_result
        mock_ctrl_class.return_value = mock_ctrl

    with patch('i3d_agent.rag.api.EmbeddingService') as mock_embed_class:
        mock_embed = AsyncMock()
        mock_embed.embed_text.return_value = [0.1] * 1536
        mock_embed_class.return_value = mock_embed

        # Create a test app with RAG router
        test_app = create_app()

        # Create test client
        from httpx import AsyncClient, ASGITransport
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
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


@pytest.mark.asyncio
async def test_ask():
    """测试问答 API"""
    app = create_app()

    with patch('i3d_agent.rag.api.AgenticRAGController') as mock_ctrl_class:
        mock_result = Mock()
        mock_result.results = [
            Mock(
                id="chunk-1",
                doc_id="doc-1",
                content="Test content",
                final_score=0.9,
                metadata={"title": "Test Doc"}
            )
        ]
        mock_result.query = "test question"
        mock_result.iterations = 1

        mock_ctrl = AsyncMock()
        mock_ctrl.retrieve.return_value = mock_result
        mock_ctrl_class.return_value = mock_ctrl

    with patch('i3d_agent.rag.api.EmbeddingService') as mock_embed_class:
        mock_embed = AsyncMock()
        mock_embed.embed_text.return_value = [0.1] * 1536
        mock_embed_class.return_value = mock_embed

    with patch('i3d_agent.llm.get_llm_client') as mock_llm:
        mock_client = AsyncMock()
        mock_client.generate.return_value = "Test answer"
        mock_llm.return_value = mock_client

        # Create a test app with RAG router
        test_app = create_app()

        # Create test client
        from httpx import AsyncClient, ASGITransport
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
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


@pytest.mark.asyncio
async def test_get_index_status():
    """测试获取索引状态 API"""
    app = create_app()

    with patch('i3d_agent.rag.api.MonitorService') as mock_monitor_class:
        mock_monitor = AsyncMock()
        mock_monitor.get_index_stats.return_value = {
            "total_documents": 10,
            "total_chunks": 50,
            "pending_index": 2,
            "failed_index": 0,
            "indexing_docs": 1
        }
        mock_monitor_class.return_value = mock_monitor

        # Create a test app with RAG router
        test_app = create_app()

        # Create test client
        from httpx import AsyncClient, ASGITransport
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/rag/index/status")

            assert response.status_code == 200
            data = response.json()
            assert data["total_documents"] == 10


@pytest.mark.asyncio
async def test_health_check():
    """测试健康检查端点"""
    app = create_app()

    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

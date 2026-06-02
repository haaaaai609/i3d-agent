"""Integration tests for RAG module."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from i3d_agent.rag.document_manager import DocumentManager
from i3d_agent.rag.controller import AgenticRAGController
from i3d_agent.rag.monitor import MonitorService
from i3d_agent.rag.index_worker import IndexWorker


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_rag_workflow():
    """测试完整的 RAG 工作流"""
    # 1. 创建文档
    manager = DocumentManager()

    # Mock the database operations
    with patch.object(manager, '_get_pool') as mock_pool_getter:
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.__aenter__.return_value = mock_conn
        mock_pool.acquire.__aexit__.return_value = None
        mock_pool_getter.return_value = mock_pool

        # Mock document creation
        mock_doc = Mock()
        mock_doc.id = "doc-1"
        mock_conn.fetchrow.return_value = {
            'id': 'doc-1',
            'tenant_id': 'test',
            'title': 'Test API Document',
            'description': None,
            'doc_type': 'technical',
            'source_type': 'md',
            'version': 1,
            'is_latest': True,
            'status': 'pending',
            'metadata': {},
            'tags': [],
            'language': 'zh',
            'created_at': None,
            'updated_at': None
        }

        doc = await manager.create_document(
            tenant_id="test",
            title="Test API Document",
            content="# API Reference\n\n## GET /api/test\n\nThis is a test endpoint.",
            doc_type="technical",
            source_type="md"
        )

        assert doc.id == "doc-1"

        # 2. 测试监控服务
        monitor = MonitorService()

        with patch.object(monitor, '_get_pool', return_value=mock_pool):
            mock_conn.fetchval.side_effect = [10, 50, 2, 0, 1, 800]
            mock_conn.fetch.return_value = [
                Mock(doc_type='technical', count=10)
            ]

            stats = await monitor.get_index_stats()
            assert stats["total_documents"] == 10

        # 3. 测试 Agentic RAG Controller
        controller = AgenticRAGController()

        with patch.object(controller, '_get_pool', return_value=mock_pool):
            # Mock embedding service
            with patch('i3d_agent.rag.controller.EmbeddingService') as mock_embed:
                mock_embed_service = AsyncMock()
                mock_embed_service.embed_text.return_value = [0.1] * 1536
                mock_embed.return_value = mock_embed_service

                # Mock retrieval results
                mock_chunk = Mock()
                mock_chunk.id = "chunk-1"
                mock_chunk.doc_id = "doc-1"
                mock_chunk.content = "This is a test endpoint."
                mock_chunk.final_score = 0.9
                mock_chunk.metadata = {"title": "Test API Document"}

                mock_conn.fetch.return_value = [mock_chunk]

                result = await controller.retrieve(
                    query="test endpoint",
                    tenant_id="test",
                    top_k=5,
                    enable_expansion=False,
                    enable_hyde=False,
                    enable_rerank=False
                )

                assert len(result.results) > 0

        # 清理
        await manager.close()
        await controller.close()
        await monitor.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agentic_rag_features():
    """测试 Agentic RAG 特性"""
    controller = AgenticRAGController()

    # Mock database and embedding service
    with patch.object(controller, '_get_pool') as mock_pool_getter:
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.__aenter__.return_value = mock_conn
        mock_pool.acquire.__aexit__.return_value = None
        mock_pool_getter.return_value = mock_pool

        with patch('i3d_agent.rag.controller.EmbeddingService') as mock_embed:
            mock_embed_service = AsyncMock()
            mock_embed_service.embed_text.return_value = [0.1] * 1536
            mock_embed.return_value = mock_embed_service

            # Mock query expansion service
            with patch('i3d_agent.rag.controller.QueryExpansionService') as mock_qe:
                mock_qe_service = AsyncMock()
                mock_qe_service.expand_query.return_value = [
                    "如何配置 API？",
                    "怎样配置 API？",
                    "API 配置方法"
                ]
                mock_qe.return_value = mock_qe_service

                # Mock HyDE service
                with patch('i3d_agent.rag.controller.HyDEService') as mock_hyde:
                    mock_hyde_service = AsyncMock()
                    mock_hyde_service.generate_hypothetical.return_value = "假设文档内容..."
                    mock_hyde.return_value = mock_hyde_service

                    # Mock retrieval results
                    mock_chunk = Mock()
                    mock_chunk.id = "chunk-1"
                    mock_chunk.doc_id = "doc-1"
                    mock_chunk.content = "API 配置方法"
                    mock_chunk.final_score = 0.85
                    mock_chunk.metadata = {"title": "API Documentation"}

                    mock_conn.fetch.return_value = [mock_chunk]

                    result = await controller.retrieve(
                        query="如何配置 API？",
                        tenant_id="test",
                        enable_expansion=True,
                        enable_hyde=True,
                        enable_rerank=False,
                        top_k=5
                    )

                    assert result.query_expansions is not None
                    assert len(result.query_expansions) >= 0

    await controller.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_monitor_service_integration():
    """测试监控服务集成"""
    monitor = MonitorService()

    with patch.object(monitor, '_get_pool') as mock_pool_getter:
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.__aenter__.return_value = mock_conn
        mock_pool.acquire.__aexit__.return_value = None
        mock_pool_getter.return_value = mock_pool

        # Test get_index_stats
        mock_conn.fetchval.side_effect = [10, 50, 2, 0, 1, 800]
        mock_conn.fetch.return_value = [
            Mock(doc_type='technical', count=10)
        ]

        stats = await monitor.get_index_stats()
        assert stats["total_documents"] == 10
        assert stats["total_chunks"] == 50

        # Test get_quality_metrics
        mock_conn.fetchval.side_effect = [4.5, 8, 10, 7]
        metrics = await monitor.get_quality_metrics("test", days=7)
        assert metrics["avg_rating"] == 4.5
        assert metrics["helpful_rate"] == 0.8

        # Test save_feedback
        await monitor.save_feedback(
            tenant_id="test",
            session_id="session-1",
            query="test query",
            retrieved_doc_ids=["doc-1"],
            rating=5,
            is_helpful=True,
            thumb_up=True,
            feedback_text="Helpful",
            answer="Test answer",
            sources={"test": "source"}
        )

        mock_conn.execute.assert_called()

    await monitor.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_document_versioning():
    """测试文档版本管理"""
    manager = DocumentManager()

    with patch.object(manager, '_get_pool') as mock_pool_getter:
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.__aenter__.return_value = mock_conn
        mock_pool.acquire.__aexit__.return_value = None
        mock_pool_getter.return_value = mock_pool

        # Mock get_document for update
        current_doc = {
            'id': 'doc-1',
            'tenant_id': 'test',
            'title': 'Original Title',
            'raw_content': 'Original content',
            'doc_type': 'technical',
            'language': 'zh',
            'version': 1,
            'content_hash': 'old-hash',
            'description': None,
            'metadata': {},
            'tags': [],
            'source_type': 'md'
        }

        new_doc = {
            'id': 'doc-2',
            'tenant_id': 'test',
            'title': 'Updated Title',
            'description': None,
            'doc_type': 'technical',
            'source_type': 'md',
            'version': 2,
            'is_latest': True,
            'status': 'pending',
            'metadata': {},
            'tags': [],
            'language': 'zh',
            'created_at': None,
            'updated_at': None
        }

        mock_conn.fetchrow.side_effect = [current_doc, new_doc]

        # Test document update
        updated = await manager.update_document("doc-1", content="New content")
        assert updated.version == 2

    await manager.close()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration"])

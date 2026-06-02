"""Tests for RAG monitoring service."""

import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from i3d_agent.rag.monitor import MonitorService


@pytest.mark.asyncio
async def test_get_index_stats():
    """测试获取索引状态统计"""
    service = MonitorService()

    # Mock the connection pool and connection
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock()

    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock()

    # Mock fetchval to return different values for each query
    mock_conn.fetchval = AsyncMock(side_effect=[100, 500, 5, 2, 3, 150])
    # Mock fetch to return type distribution
    mock_conn.fetch = AsyncMock(return_value=[
        {'doc_type': 'technical', 'count': 80},
        {'doc_type': 'business', 'count': 20}
    ])

    with patch.object(service, '_get_pool', return_value=mock_pool):
        stats = await service.get_index_stats()

        assert stats["total_documents"] == 100
        assert stats["total_chunks"] == 500
        assert stats["pending_index"] == 5
        assert stats["failed_index"] == 2
        assert stats["indexing_docs"] == 3
        assert stats["avg_chunk_size"] == 150
        assert stats["doc_type_distribution"]["technical"] == 80
        assert stats["doc_type_distribution"]["business"] == 20


@pytest.mark.asyncio
async def test_record_metric():
    """测试记录指标"""
    service = MonitorService()

    # Mock the connection pool and connection
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock()

    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock()
    mock_conn.execute = AsyncMock()

    with patch.object(service, '_get_pool', return_value=mock_pool):
        await service.record_metric(
            tenant_id="default",
            metric_name="rag检索延迟",
            value={"p50": 100, "p95": 200, "p99": 500}
        )

        mock_conn.execute.assert_called_once()
        # Verify the call arguments
        call_args = mock_conn.execute.call_args
        assert call_args[0][1] == "default"
        assert call_args[0][2] == "rag检索延迟"
        assert call_args[0][3] == {"p50": 100, "p95": 200, "p99": 500}


@pytest.mark.asyncio
async def test_get_metrics():
    """测试获取监控指标"""
    service = MonitorService()

    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock()

    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock()

    mock_conn.fetch = AsyncMock(return_value=[
        {'id': 1, 'tenant_id': 'default', 'metric_name': 'rag检索延迟', 'metric_value': {'p50': 100}}
    ])

    with patch.object(service, '_get_pool', return_value=mock_pool):
        metrics = await service.get_metrics(tenant_id="default", time_range="24h")

        assert len(metrics) == 1
        assert metrics[0]['tenant_id'] == 'default'
        assert metrics[0]['metric_name'] == 'rag检索延迟'


@pytest.mark.asyncio
async def test_get_quality_metrics():
    """测试获取质量指标"""
    service = MonitorService()

    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock()

    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock()

    # Mock fetchval to return values for avg_rating, helpful_count, total_count, thumb_up_count
    mock_conn.fetchval = AsyncMock(side_effect=[4.5, 8, 10, 7])

    with patch.object(service, '_get_pool', return_value=mock_pool):
        quality = await service.get_quality_metrics(tenant_id="default", days=7)

        assert quality["avg_rating"] == 4.5
        assert quality["helpful_rate"] == 0.8  # 8/10
        assert quality["thumb_up_rate"] == 0.7  # 7/10
        assert quality["total_feedbacks"] == 10


@pytest.mark.asyncio
async def test_save_feedback():
    """测试保存质量反馈"""
    service = MonitorService()

    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock()

    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock()
    mock_conn.execute = AsyncMock()

    with patch.object(service, '_get_pool', return_value=mock_pool):
        await service.save_feedback(
            tenant_id="default",
            session_id="session-1",
            query="如何配置 API",
            retrieved_doc_ids=["doc1", "doc2"],
            rating=5,
            is_helpful=True,
            thumb_up=True,
            feedback_text="非常有帮助",
            answer="配置步骤如下...",
            sources={"doc1": "content1"}
        )

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert call_args[0][1] == "default"
        assert call_args[0][2] == "session-1"
        assert call_args[0][3] == "如何配置 API"


def test_parse_time_range():
    """测试解析时间范围"""
    service = MonitorService()

    assert service._parse_time_range("24h").total_seconds() == 24 * 3600
    assert service._parse_time_range("7d").total_seconds() == 7 * 24 * 3600
    assert service._parse_time_range("2w").total_seconds() == 2 * 7 * 24 * 3600
    # Default to 24h for invalid format
    assert service._parse_time_range("invalid").total_seconds() == 24 * 3600

"""Tests for RAG monitoring service."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch, AsyncMock as async_mock
from i3d_agent.rag.monitor import MonitorService


class AsyncContextManager:
    """Helper to create async context manager mocks."""
    def __init__(self, mock_obj):
        self.mock_obj = mock_obj

    async def __aenter__(self):
        return self.mock_obj

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_get_index_stats():
    """测试获取索引状态统计"""
    service = MonitorService()

    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(side_effect=[100, 500, 5, 2, 3, 800])
    mock_conn.fetch = AsyncMock(return_value=[
        Mock(doc_type='technical', count=60),
        Mock(doc_type='business', count=40)
    ])

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = AsyncContextManager(mock_conn)

    with patch.object(service, '_get_pool', return_value=mock_pool):
        stats = await service.get_index_stats()

        assert stats["total_documents"] == 100
        assert stats["total_chunks"] == 500
        assert stats["pending_index"] == 5
        assert stats["failed_index"] == 2
        assert stats["indexing_docs"] == 3
        assert stats["avg_chunk_size"] == 800
        assert stats["doc_type_distribution"]["technical"] == 60
        assert stats["doc_type_distribution"]["business"] == 40


@pytest.mark.asyncio
async def test_record_metric():
    """测试记录指标"""
    service = MonitorService()

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = AsyncContextManager(mock_conn)

    with patch.object(service, '_get_pool', return_value=mock_pool):
        await service.record_metric(
            tenant_id="default",
            metric_name="rag检索延迟",
            value={"p50": 100, "p95": 200, "p99": 500}
        )

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "rag_metrics" in call_args[0][0]


@pytest.mark.asyncio
async def test_get_quality_metrics():
    """测试获取质量指标"""
    service = MonitorService()

    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(side_effect=[4.5, 8, 10, 7])

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = AsyncContextManager(mock_conn)

    with patch.object(service, '_get_pool', return_value=mock_pool):
        metrics = await service.get_quality_metrics("default", days=7)

        assert metrics["avg_rating"] == 4.5
        assert metrics["helpful_rate"] == 0.8  # 8/10
        assert metrics["thumb_up_rate"] == 0.7  # 7/10
        assert metrics["total_feedbacks"] == 10


@pytest.mark.asyncio
async def test_save_feedback():
    """测试保存质量反馈"""
    service = MonitorService()

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = AsyncContextManager(mock_conn)

    with patch.object(service, '_get_pool', return_value=mock_pool):
        await service.save_feedback(
            tenant_id="default",
            session_id="session-1",
            query="测试查询",
            retrieved_doc_ids=["doc-1", "doc-2"],
            rating=5,
            is_helpful=True,
            thumb_up=True,
            feedback_text="很有帮助",
            answer="测试答案",
            sources={"source": "test"}
        )

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "rag_feedback" in call_args[0][0]


@pytest.mark.asyncio
async def test_get_metrics():
    """测试获取监控指标"""
    service = MonitorService()

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[
        {
            'id': 1,
            'tenant_id': 'default',
            'metric_name': 'rag检索延迟',
            'metric_value': {'p50': 100},
            'timestamp': '2024-01-01'
        }
    ])

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = AsyncContextManager(mock_conn)

    with patch.object(service, '_get_pool', return_value=mock_pool):
        metrics = await service.get_metrics("default", metric_name="rag检索延迟")

        assert len(metrics) == 1
        assert metrics[0]["metric_name"] == "rag检索延迟"


def test_parse_time_range():
    """测试时间范围解析"""
    service = MonitorService()

    from datetime import timedelta

    # Test hours
    assert service._parse_time_range("24h") == timedelta(hours=24)
    assert service._parse_time_range("1h") == timedelta(hours=1)

    # Test days
    assert service._parse_time_range("7d") == timedelta(days=7)

    # Test weeks
    assert service._parse_time_range("1w") == timedelta(weeks=1)

    # Test invalid format (should default to 24 hours)
    assert service._parse_time_range("invalid") == timedelta(hours=24)


@pytest.mark.asyncio
async def test_record_latency():
    """测试记录检索延迟"""
    service = MonitorService()

    # Mock the histogram if it exists
    with patch.object(service, 'rag_latency', create=True) as mock_histogram:
        await service.record_latency("default", 150.5)

        if hasattr(service, 'rag_latency'):
            mock_histogram.record.assert_called_once_with(150.5, {"tenant_id": "default"})


@pytest.mark.asyncio
async def test_record_request():
    """测试记录检索请求"""
    service = MonitorService()

    with patch.object(service, 'rag_requests', create=True) as mock_counter, \
         patch.object(service, 'rag_empty_results', create=True) as mock_empty:

        await service.record_request("default", has_results=True)

        if hasattr(service, 'rag_requests'):
            mock_counter.add.assert_called_once_with(1, {"tenant_id": "default"})
            # empty_results should not be called when has_results is True
            mock_empty.add.assert_not_called()

    # Test with no results
    with patch.object(service, 'rag_requests', create=True) as mock_counter, \
         patch.object(service, 'rag_empty_results', create=True) as mock_empty:

        await service.record_request("default", has_results=False)

        if hasattr(service, 'rag_requests'):
            mock_counter.add.assert_called_once_with(1, {"tenant_id": "default"})
            mock_empty.add.assert_called_once_with(1, {"tenant_id": "default"})


@pytest.mark.asyncio
async def test_close():
    """测试关闭连接"""
    service = MonitorService()

    mock_pool = AsyncMock()
    service._pool = mock_pool

    await service.close()

    mock_pool.close.assert_called_once()
    assert service._pool is None

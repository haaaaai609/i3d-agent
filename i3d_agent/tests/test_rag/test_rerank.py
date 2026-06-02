"""Tests for RerankService."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from i3d_agent.rag.rerank import RerankService


@pytest.mark.asyncio
async def test_rerank_with_cohere():
    """测试使用 Cohere 重排序"""
    service = RerankService()
    service.settings.COHERE_API_KEY = "test-key"

    with patch.object(service, '_call_cohere_rerank') as mock_cohere:
        mock_cohere.return_value = [
            {"index": 2, "relevance_score": 0.95},
            {"index": 0, "relevance_score": 0.85},
            {"index": 1, "relevance_score": 0.75}
        ]

        chunks = [
            Mock(id="c1", content="Content 1"),
            Mock(id="c2", content="Content 2"),
            Mock(id="c3", content="Content 3")
        ]

        results = await service.rerank(
            query="test query",
            chunks=chunks,
            top_k=3
        )

        assert len(results) == 3
        assert results[0].id == "c3"  # index 2
        assert results[1].id == "c1"  # index 0
        assert results[2].id == "c2"  # index 1


@pytest.mark.asyncio
async def test_rerank_fallback_to_original():
    """测试重排序失败时回退到原始顺序"""
    service = RerankService()

    with patch.object(service, '_call_cohere_rerank') as mock_cohere:
        mock_cohere.side_effect = Exception("API error")

        chunks = [
            Mock(id="c1", content="Content 1"),
            Mock(id="c2", content="Content 2")
        ]

        results = await service.rerank(
            query="test query",
            chunks=chunks,
            top_k=2
        )

        # 应该返回原始顺序
        assert len(results) == 2
        assert results[0].id == "c1"
        assert results[1].id == "c2"


@pytest.mark.asyncio
async def test_rerank_with_top_k():
    """测试 top_k 参数截断"""
    service = RerankService()
    service.settings.COHERE_API_KEY = "test-key"

    with patch.object(service, '_call_cohere_rerank') as mock_cohere:
        mock_cohere.return_value = [
            {"index": 2, "relevance_score": 0.95},
            {"index": 0, "relevance_score": 0.85},
            {"index": 1, "relevance_score": 0.75}
        ]

        chunks = [
            Mock(id="c1", content="Content 1"),
            Mock(id="c2", content="Content 2"),
            Mock(id="c3", content="Content 3")
        ]

        results = await service.rerank(
            query="test query",
            chunks=chunks,
            top_k=2
        )

        # 应该只返回前2个
        assert len(results) == 2
        assert results[0].id == "c3"
        assert results[1].id == "c1"


@pytest.mark.asyncio
async def test_rerank_empty_chunks():
    """测试空 chunks 列表"""
    service = RerankService()

    results = await service.rerank(
        query="test query",
        chunks=[],
        top_k=5
    )

    assert results == []


@pytest.mark.asyncio
async def test_rerack_no_api_key():
    """测试没有 API key 时回退"""
    service = RerankService()
    service.settings.COHERE_API_KEY = ""

    chunks = [
        Mock(id="c1", content="Content 1"),
        Mock(id="c2", content="Content 2")
    ]

    results = await service.rerank(
        query="test query",
        chunks=chunks,
        top_k=2
    )

    # 应该返回原始顺序
    assert len(results) == 2
    assert results[0].id == "c1"
    assert results[1].id == "c2"


@pytest.mark.asyncio
async def test_call_cohere_rerank():
    """测试 Cohere Rerank API 调用"""
    service = RerankService()
    service.settings.COHERE_API_KEY = "test-key"
    service.settings.COHERE_RERANK_MODEL = "rerank-english-v2.0"

    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [
            {"index": 1, "relevance_score": 0.95},
            {"index": 0, "relevance_score": 0.85}
        ]
    }
    mock_client.post.return_value = mock_response

    result = await service._call_cohere_rerank(mock_client, "test query", ["doc1", "doc2"])

    assert len(result) == 2
    assert result[0]["index"] == 1
    assert result[0]["relevance_score"] == 0.95
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_rerank_client_reuse():
    """测试 HTTP 客户端复用"""
    service = RerankService()

    client1 = await service._get_client()
    client2 = await service._get_client()

    assert client1 is client2


@pytest.mark.asyncio
async def test_rerank_close():
    """测试关闭客户端连接"""
    service = RerankService()

    # Initialize client
    await service._get_client()
    assert service.client is not None

    # Get reference to client before close
    client = service.client

    # Mock the aclose method
    client.aclose = AsyncMock()

    # Close
    await service.close()

    # Verify aclose was called
    client.aclose.assert_called_once()

    # Verify client is set to None
    assert service.client is None

"""Tests for EmbeddingService."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from i3d_agent.rag.embedding import EmbeddingService


@pytest.mark.asyncio
async def test_embedding_single_text():
    """测试单个文本 embedding"""
    service = EmbeddingService()

    with patch.object(service, '_call_embedding_api') as mock_api:
        mock_api.return_value = [[0.1] * 1536]

        result = await service.embed_text("测试文本")

        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
        mock_api.assert_called_once_with(["测试文本"])


@pytest.mark.asyncio
async def test_embedding_batch():
    """测试批量 embedding"""
    service = EmbeddingService()

    texts = ["文本1", "文本2", "文本3"]

    with patch.object(service, '_call_embedding_api') as mock_api:
        mock_api.return_value = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]

        results = await service.embed_batch(texts)

        assert len(results) == 3
        assert all(len(r) == 1536 for r in results)
        mock_api.assert_called_once_with(texts)


@pytest.mark.asyncio
async def test_embedding_chunks():
    """测试 chunk 列表 embedding"""
    service = EmbeddingService()

    chunks = [
        {"content": "内容1", "metadata": {"chunk_index": 0}},
        {"content": "内容2", "metadata": {"chunk_index": 1}}
    ]

    with patch.object(service, '_call_embedding_api') as mock_api:
        mock_api.return_value = [[0.1] * 1536, [0.2] * 1536]

        results = await service.embed_chunks(chunks)

        assert len(results) == 2
        assert results[0]["embedding"] == [0.1] * 1536
        assert results[1]["embedding"] == [0.2] * 1536
        assert "content" in results[0]
        assert "metadata" in results[0]


@pytest.mark.asyncio
async def test_embedding_empty_text():
    """测试空文本 embedding"""
    service = EmbeddingService()

    with patch.object(service, '_call_embedding_api') as mock_api:
        mock_api.return_value = [[0.1] * 1536]

        result = await service.embed_text("")

        assert len(result) == 1536
        mock_api.assert_called_once_with([""])


@pytest.mark.asyncio
async def test_embedding_empty_batch():
    """测试空批量 embedding"""
    service = EmbeddingService()

    results = await service.embed_batch([])

    assert results == []


@pytest.mark.asyncio
async def test_embedding_empty_chunks():
    """测试空 chunk 列表 embedding"""
    service = EmbeddingService()

    results = await service.embed_chunks([])

    assert results == []


@pytest.mark.asyncio
async def test_call_dashscope_api():
    """测试 DashScope API 调用"""
    service = EmbeddingService()
    service.settings.EMBEDDING_MODEL = "text-embedding-v3"
    service.settings.DASHSCOPE_API_KEY = "test-key"

    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.json.return_value = {
        "outputs": {
            "embeddings": [
                {"embedding": [0.1] * 1536},
                {"embedding": [0.2] * 1536}
            ]
        }
    }
    mock_client.post.return_value = mock_response

    result = await service._call_dashscope(mock_client, ["text1", "text2"])

    assert len(result) == 2
    assert result[0] == [0.1] * 1536
    assert result[1] == [0.2] * 1536
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_call_openai_api():
    """测试 OpenAI API 调用"""
    service = EmbeddingService()
    service.settings.EMBEDDING_MODEL = "text-embedding-3-small"
    service.settings.OPENAI_API_KEY = "test-key"

    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": [
            {"embedding": [0.1] * 1536},
            {"embedding": [0.2] * 1536}
        ]
    }
    mock_client.post.return_value = mock_response

    result = await service._call_openai(mock_client, ["text1", "text2"])

    assert len(result) == 2
    assert result[0] == [0.1] * 1536
    assert result[1] == [0.2] * 1536
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_embedding_client_reuse():
    """测试 HTTP 客户端复用"""
    service = EmbeddingService()

    client1 = await service._get_client()
    client2 = await service._get_client()

    assert client1 is client2


@pytest.mark.asyncio
async def test_embedding_close():
    """测试关闭客户端连接"""
    service = EmbeddingService()

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

"""Tests for AgenticRAGController."""

import pytest
from unittest.mock import Mock, AsyncMock
from i3d_agent.rag.controller import AgenticRAGController
from i3d_agent.rag.models import Chunk


@pytest.mark.asyncio
async def test_retrieve_with_all_features():
    """测试使用所有特性的检索"""
    controller = AgenticRAGController()

    # 设置 mock 对象
    mock_expansion = AsyncMock()
    mock_expansion.expand_query = AsyncMock(return_value=["query", "variation 1", "variation 2"])

    mock_hyde = AsyncMock()
    mock_hyde.generate_hypothetical = AsyncMock(return_value="hypothetical document")

    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)

    # 模拟检索结果
    mock_chunks = [
        Chunk(
            id="c1",
            doc_id="d1",
            tenant_id="default",
            content="Content 1",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.9
        ),
        Chunk(
            id="c2",
            doc_id="d2",
            tenant_id="default",
            content="Content 2",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.8
        )
    ]

    mock_retrieval = AsyncMock()
    mock_retrieval.hybrid_retrieval = AsyncMock(return_value=mock_chunks)

    mock_rerank = AsyncMock()
    mock_rerank.rerank = AsyncMock(return_value=mock_chunks)

    # Assign mocks to controller
    controller.query_expansion = mock_expansion
    controller.hyde_service = mock_hyde
    controller.retrieval_engine = mock_retrieval
    controller.rerank_service = mock_rerank
    controller.embedding_service = mock_embedding

    result = await controller.retrieve(
        query="test query",
        tenant_id="default",
        enable_expansion=True,
        enable_hyde=True,
        enable_rerank=True,
        top_k=5
    )

    assert len(result.results) > 0
    assert result.query == "test query"
    assert result.iterations == 1
    assert len(result.query_expansions) > 0


@pytest.mark.asyncio
async def test_retrieve_without_optional_features():
    """测试不启用可选特性的检索"""
    controller = AgenticRAGController()

    mock_chunks = [
        Chunk(
            id="c1",
            doc_id="d1",
            tenant_id="default",
            content="Content 1",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.9
        )
    ]

    mock_retrieval = AsyncMock()
    mock_retrieval.hybrid_retrieval = AsyncMock(return_value=mock_chunks)

    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)

    controller.retrieval_engine = mock_retrieval
    controller.embedding_service = mock_embedding

    result = await controller.retrieve(
        query="test query",
        tenant_id="default",
        enable_expansion=False,
        enable_hyde=False,
        enable_rerank=False,
        top_k=5
    )

    assert len(result.results) == 1
    assert result.query == "test query"
    assert len(result.query_expansions) == 0
    assert result.hypothetical_doc is None


@pytest.mark.asyncio
async def test_multi_step_reasoning():
    """测试多步推理"""
    controller = AgenticRAGController()

    # 第一次迭代质量低，第二次高
    mock_assess_results = [
        Mock(is_satisfactory=False, issue="low_relevance", feedback="需要更精确的关键词"),
        Mock(is_satisfactory=True)
    ]

    async def mock_assess(*args, **kwargs):
        return mock_assess_results.pop(0) if mock_assess_results else Mock(is_satisfactory=True)

    mock_chunks = [
        Chunk(
            id="c1",
            doc_id="d1",
            tenant_id="default",
            content="Content",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.5
        )
    ]

    mock_retrieval = AsyncMock()
    mock_retrieval.hybrid_retrieval = AsyncMock(return_value=mock_chunks)

    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)

    controller.retrieval_engine = mock_retrieval
    controller.embedding_service = mock_embedding
    controller._assess_quality = mock_assess
    controller._rewrite_query = AsyncMock(return_value="rewritten query")

    result = await controller.retrieve_with_multi_step(
        query="test",
        query_vector=[0.1] * 1536,
        tenant_id="default",
        max_iterations=3
    )

    assert result.iterations >= 2
    assert len(result.results) > 0


@pytest.mark.asyncio
async def test_multi_step_max_iterations_reached():
    """测试达到最大迭代次数"""
    controller = AgenticRAGController()

    # 始终返回低质量
    mock_assess_result = Mock(
        is_satisfactory=False,
        issue="low_relevance",
        feedback="需要更好的结果"
    )

    mock_chunks = [
        Chunk(
            id="c1",
            doc_id="d1",
            tenant_id="default",
            content="Content",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.3
        )
    ]

    mock_retrieval = AsyncMock()
    mock_retrieval.hybrid_retrieval = AsyncMock(return_value=mock_chunks)

    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)

    controller.retrieval_engine = mock_retrieval
    controller.embedding_service = mock_embedding
    controller._assess_quality = AsyncMock(return_value=mock_assess_result)

    result = await controller.retrieve_with_multi_step(
        query="test",
        query_vector=[0.1] * 1536,
        tenant_id="default",
        max_iterations=3
    )

    # 应该在 max_iterations 次后停止
    assert result.iterations == 3


@pytest.mark.asyncio
async def test_assess_quality_satisfactory():
    """测试质量评估 - 满意的情况"""
    controller = AgenticRAGController()

    chunks = [
        Chunk(
            id=f"c{i}",
            doc_id=f"d{i}",
            tenant_id="default",
            content=f"Content {i}",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.9 - i * 0.05
        ) for i in range(5)
    ]

    result = await controller._assess_quality(chunks, query="test")

    assert result.is_satisfactory is True


@pytest.mark.asyncio
async def test_assess_quality_low_count():
    """测试质量评估 - 结果数量不足"""
    controller = AgenticRAGController()

    chunks = [
        Chunk(
            id="c1",
            doc_id="d1",
            tenant_id="default",
            content="Content",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.9
        )
    ]

    result = await controller._assess_quality(chunks, query="test")

    assert result.is_satisfactory is False
    assert "insufficient" in result.issue


@pytest.mark.asyncio
async def test_assess_quality_low_scores():
    """测试质量评估 - 分数过低"""
    controller = AgenticRAGController()

    chunks = [
        Chunk(
            id=f"c{i}",
            doc_id=f"d{i}",
            tenant_id="default",
            content=f"Content {i}",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.3
        ) for i in range(5)
    ]

    result = await controller._assess_quality(chunks, query="test")

    assert result.is_satisfactory is False
    assert "low_score" in result.issue


@pytest.mark.asyncio
async def test_deduplicate_and_merge():
    """测试去重和合并"""
    controller = AgenticRAGController()

    chunks = [
        Chunk(
            id="c1",
            doc_id="d1",
            tenant_id="default",
            content="Content 1",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.8
        ),
        Chunk(
            id="c1",  # 重复 ID
            doc_id="d1",
            tenant_id="default",
            content="Content 1",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.9  # 更高的分数
        ),
        Chunk(
            id="c2",
            doc_id="d2",
            tenant_id="default",
            content="Content 2",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.7
        )
    ]

    result = controller._deduplicate_and_merge(chunks)

    # 应该只保留每个 ID 的最高分版本
    assert len(result) == 2
    assert any(c.id == "c1" and c.final_score == 0.9 for c in result)
    assert any(c.id == "c2" for c in result)


@pytest.mark.asyncio
async def test_query_expansion_integration():
    """测试查询扩展集成"""
    controller = AgenticRAGController()

    mock_expansion = AsyncMock()
    mock_expansion.expand_query = AsyncMock(
        return_value=["query", "expanded 1", "expanded 2"]
    )

    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)

    all_results = []
    for i in range(3):
        all_results.append([
            Chunk(
                id=f"c{i}_{j}",
                doc_id=f"d{i}",
                tenant_id="default",
                content=f"Content {i}_{j}",
                embedding=[0.1] * 1536,
                chunk_index=0,
                token_count=100,
                metadata={},
                doc_version=1,
                final_score=0.8 - j * 0.1
            ) for j in range(2)
        ])

    call_count = [0]

    async def mock_hybrid(*args, **kwargs):
        result = all_results[call_count[0]] if call_count[0] < len(all_results) else all_results[-1]
        call_count[0] += 1
        return result

    mock_retrieval = AsyncMock()
    mock_retrieval.hybrid_retrieval = mock_hybrid

    controller.query_expansion = mock_expansion
    controller.retrieval_engine = mock_retrieval
    controller.embedding_service = mock_embedding

    result = await controller.retrieve(
        query="test",
        tenant_id="default",
        enable_expansion=True,
        top_k=3
    )

    # 应该调用了多次检索（原始 + 扩展查询）
    assert len(result.results) > 0
    assert len(result.query_expansions) == 3


@pytest.mark.asyncio
async def test_hyde_integration():
    """测试 HyDE 集成"""
    controller = AgenticRAGController()

    mock_hyde = AsyncMock()
    mock_hyde.generate_hypothetical = AsyncMock(
        return_value="hypothetical answer document"
    )

    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)

    mock_chunks = [
        Chunk(
            id="c1",
            doc_id="d1",
            tenant_id="default",
            content="Content",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.9
        )
    ]

    mock_retrieval = AsyncMock()
    mock_retrieval.hybrid_retrieval = AsyncMock(return_value=mock_chunks)

    controller.hyde_service = mock_hyde
    controller.retrieval_engine = mock_retrieval
    controller.embedding_service = mock_embedding

    result = await controller.retrieve(
        query="How to configure API?",
        tenant_id="default",
        enable_hyde=True,
        enable_expansion=False,
        enable_rerank=False,
        top_k=5
    )

    # HyDE 应该生成了假设文档
    assert result.hypothetical_doc is not None
    assert len(result.results) > 0


@pytest.mark.asyncio
async def test_rerank_integration():
    """测试重排序集成"""
    controller = AgenticRAGController()

    # 创建重排序后的结果（顺序改变）
    original_chunks = [
        Chunk(
            id=f"c{i}",
            doc_id=f"d{i}",
            tenant_id="default",
            content=f"Content {i}",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={},
            doc_version=1,
            final_score=0.9 - i * 0.1
        ) for i in range(5)
    ]

    reranked_chunks = [
        original_chunks[2],  # c2
        original_chunks[0],  # c0
        original_chunks[1],  # c1
    ]

    mock_rerank = AsyncMock()
    mock_rerank.rerank = AsyncMock(return_value=reranked_chunks)

    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)

    mock_retrieval = AsyncMock()
    mock_retrieval.hybrid_retrieval = AsyncMock(return_value=original_chunks)

    controller.rerank_service = mock_rerank
    controller.retrieval_engine = mock_retrieval
    controller.embedding_service = mock_embedding

    result = await controller.retrieve(
        query="test",
        tenant_id="default",
        enable_expansion=False,
        enable_hyde=False,
        enable_rerank=True,
        top_k=3
    )

    # 结果应该是重排序后的
    assert len(result.results) == 3
    # 验证 rerank 被调用
    mock_rerank.rerank.assert_called_once()


@pytest.mark.asyncio
async def test_empty_results_handling():
    """测试空结果处理"""
    controller = AgenticRAGController()

    mock_retrieval = AsyncMock()
    mock_retrieval.hybrid_retrieval = AsyncMock(return_value=[])

    mock_embedding = AsyncMock()
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)

    controller.retrieval_engine = mock_retrieval
    controller.embedding_service = mock_embedding

    result = await controller.retrieve(
        query="test",
        tenant_id="default",
        top_k=5
    )

    assert len(result.results) == 0
    assert result.query == "test"

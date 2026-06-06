"""Tests for RetrievalEngine"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from i3d_agent.rag.retrieval import RetrievalEngine


@pytest.mark.asyncio
async def test_vector_search():
    """测试向量检索"""
    engine = RetrievalEngine()

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            'id': 'c1',
            'doc_id': 'd1',
            'tenant_id': 'default',
            'content': 'Content 1',
            'embedding': [0.1] * 1536,
            'chunk_index': 0,
            'metadata': {},
            'doc_version': 1,
            'score': 0.9
        },
        {
            'id': 'c2',
            'doc_id': 'd2',
            'tenant_id': 'default',
            'content': 'Content 2',
            'embedding': [0.1] * 1536,
            'chunk_index': 1,
            'metadata': {},
            'doc_version': 1,
            'score': 0.8
        }
    ]

    with patch.object(engine, '_get_connection', return_value=mock_conn):
        results = await engine.vector_search(
            query_vector=[0.1] * 1536,
            tenant_id="default",
            top_k=10
        )

        assert len(results) == 2
        assert results[0].id == "c1"
        assert results[0].vector_score == 0.9


@pytest.mark.asyncio
async def test_bm25_search():
    """测试 BM25 检索"""
    engine = RetrievalEngine()

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            'id': 'c1',
            'doc_id': 'd1',
            'tenant_id': 'default',
            'content': 'Content 1',
            'embedding': [0.1] * 1536,
            'chunk_index': 0,
            'metadata': {},
            'doc_version': 1,
            'score': 0.9
        }
    ]

    with patch.object(engine, '_get_connection', return_value=mock_conn):
        results = await engine.bm25_search(
            query="test query",
            tenant_id="default",
            top_k=10
        )

        assert len(results) == 1
        assert results[0].id == "c1"
        assert results[0].bm25_score == 0.9


@pytest.mark.asyncio
async def test_hybrid_retrieval():
    """测试混合检索"""
    from i3d_agent.rag.models import Chunk

    engine = RetrievalEngine()

    chunk_c1_vector = Chunk(
        id="c1", doc_id="d1", tenant_id="default", content="Content 1",
        embedding=[0.1] * 1536, chunk_index=0, token_count=None, metadata={}, doc_version=1,
        vector_score=0.9, bm25_score=0.0, final_score=0.9
    )
    chunk_c2_vector = Chunk(
        id="c2", doc_id="d2", tenant_id="default", content="Content 2",
        embedding=[0.1] * 1536, chunk_index=1, token_count=None, metadata={}, doc_version=1,
        vector_score=0.8, bm25_score=0.0, final_score=0.8
    )
    chunk_c1_bm25 = Chunk(
        id="c1", doc_id="d1", tenant_id="default", content="Content 1",
        embedding=[0.1] * 1536, chunk_index=0, token_count=None, metadata={}, doc_version=1,
        vector_score=0.0, bm25_score=0.7, final_score=0.7
    )
    chunk_c3_bm25 = Chunk(
        id="c3", doc_id="d3", tenant_id="default", content="Content 3",
        embedding=[0.1] * 1536, chunk_index=2, token_count=None, metadata={}, doc_version=1,
        vector_score=0.0, bm25_score=0.6, final_score=0.6
    )

    with patch.object(engine, 'vector_search') as mock_vector, \
         patch.object(engine, 'bm25_search') as mock_bm25:

        mock_vector.return_value = [chunk_c1_vector, chunk_c2_vector]
        mock_bm25.return_value = [chunk_c1_bm25, chunk_c3_bm25]

        results = await engine.hybrid_retrieval(
            query="test query",
            query_vector=[0.1] * 1536,
            tenant_id="default",
            top_k=10
        )

        # Should deduplicate and fuse scores
        assert len(results) >= 2


@pytest.mark.asyncio
async def test_hybrid_retrieval_semantic_weights():
    """测试混合检索语义权重"""
    from i3d_agent.rag.models import Chunk

    engine = RetrievalEngine()

    chunk_c1_vector = Chunk(
        id="c1", doc_id="d1", tenant_id="default", content="Content 1",
        embedding=[0.1] * 1536, chunk_index=0, token_count=None, metadata={}, doc_version=1,
        vector_score=0.9, bm25_score=0.0, final_score=0.9
    )
    chunk_c2_vector = Chunk(
        id="c2", doc_id="d2", tenant_id="default", content="Content 2",
        embedding=[0.1] * 1536, chunk_index=1, token_count=None, metadata={}, doc_version=1,
        vector_score=0.8, bm25_score=0.0, final_score=0.8
    )
    chunk_c1_bm25 = Chunk(
        id="c1", doc_id="d1", tenant_id="default", content="Content 1",
        embedding=[0.1] * 1536, chunk_index=0, token_count=None, metadata={}, doc_version=1,
        vector_score=0.0, bm25_score=0.7, final_score=0.7
    )

    with patch.object(engine, 'vector_search') as mock_vector, \
         patch.object(engine, 'bm25_search') as mock_bm25:

        mock_vector.return_value = [chunk_c1_vector, chunk_c2_vector]
        mock_bm25.return_value = [chunk_c1_bm25]

        results = await engine.hybrid_retrieval(
            query="test query",
            query_vector=[0.1] * 1536,
            tenant_id="default",
            top_k=10,
            search_type="semantic"
        )

        # Semantic search should weight vector higher (0.8)
        assert len(results) >= 1


@pytest.mark.asyncio
async def test_hybrid_retrieval_keyword_weights():
    """测试混合检索关键词权重"""
    from i3d_agent.rag.models import Chunk

    engine = RetrievalEngine()

    chunk_c1_vector = Chunk(
        id="c1", doc_id="d1", tenant_id="default", content="Content 1",
        embedding=[0.1] * 1536, chunk_index=0, token_count=None, metadata={}, doc_version=1,
        vector_score=0.9, bm25_score=0.0, final_score=0.9
    )
    chunk_c1_bm25 = Chunk(
        id="c1", doc_id="d1", tenant_id="default", content="Content 1",
        embedding=[0.1] * 1536, chunk_index=0, token_count=None, metadata={}, doc_version=1,
        vector_score=0.0, bm25_score=0.7, final_score=0.7
    )
    chunk_c2_bm25 = Chunk(
        id="c2", doc_id="d2", tenant_id="default", content="Content 2",
        embedding=[0.1] * 1536, chunk_index=1, token_count=None, metadata={}, doc_version=1,
        vector_score=0.0, bm25_score=0.6, final_score=0.6
    )

    with patch.object(engine, 'vector_search') as mock_vector, \
         patch.object(engine, 'bm25_search') as mock_bm25:

        mock_vector.return_value = [chunk_c1_vector]
        mock_bm25.return_value = [chunk_c1_bm25, chunk_c2_bm25]

        results = await engine.hybrid_retrieval(
            query="test query",
            query_vector=[0.1] * 1536,
            tenant_id="default",
            top_k=10,
            search_type="keyword"
        )

        # Keyword search should weight BM25 higher (0.7)
        assert len(results) >= 1


@pytest.mark.asyncio
async def test_hybrid_retrieval_exact_match_weights():
    """测试混合检索精确匹配权重"""
    from i3d_agent.rag.models import Chunk

    engine = RetrievalEngine()

    chunk_c1_vector = Chunk(
        id="c1", doc_id="d1", tenant_id="default", content="Content 1",
        embedding=[0.1] * 1536, chunk_index=0, token_count=None, metadata={}, doc_version=1,
        vector_score=0.9, bm25_score=0.0, final_score=0.9
    )
    chunk_c1_bm25 = Chunk(
        id="c1", doc_id="d1", tenant_id="default", content="Content 1",
        embedding=[0.1] * 1536, chunk_index=0, token_count=None, metadata={}, doc_version=1,
        vector_score=0.0, bm25_score=0.7, final_score=0.7
    )
    chunk_c2_bm25 = Chunk(
        id="c2", doc_id="d2", tenant_id="default", content="Content 2",
        embedding=[0.1] * 1536, chunk_index=1, token_count=None, metadata={}, doc_version=1,
        vector_score=0.0, bm25_score=0.6, final_score=0.6
    )

    with patch.object(engine, 'vector_search') as mock_vector, \
         patch.object(engine, 'bm25_search') as mock_bm25:

        mock_vector.return_value = [chunk_c1_vector]
        mock_bm25.return_value = [chunk_c1_bm25, chunk_c2_bm25]

        results = await engine.hybrid_retrieval(
            query="test query",
            query_vector=[0.1] * 1536,
            tenant_id="default",
            top_k=10,
            search_type="exact_match"
        )

        # Exact match should heavily weight BM25 (0.9)
        assert len(results) >= 1


def test_classify_query_error_code():
    """测试错误码查询分类"""
    engine = RetrievalEngine()

    query_type = engine.classify_query("Error 500: Internal Server Error")
    assert query_type == "keyword"

    query_type = engine.classify_query("ERR_CONNECTION_REFUSED")
    assert query_type == "keyword"

    query_type = engine.classify_query("Exception occurred")
    assert query_type == "keyword"


def test_classify_query_api_path():
    """测试 API 路径查询分类"""
    engine = RetrievalEngine()

    query_type = engine.classify_query("GET /api/v1/users")
    assert query_type == "exact_match"

    query_type = engine.classify_query("/api/v1/health")
    assert query_type == "exact_match"


def test_classify_query_question():
    """测试问题查询分类"""
    engine = RetrievalEngine()

    query_type = engine.classify_query("如何使用系统?")
    assert query_type == "semantic"

    query_type = engine.classify_query("What is the meaning of life?")
    assert query_type == "semantic"


def test_classify_query_default():
    """测试默认查询分类"""
    engine = RetrievalEngine()

    query_type = engine.classify_query("some random text")
    assert query_type == "balanced"


@pytest.mark.asyncio
async def test_vector_search_merges_document_metadata():
    """Retrieved chunks should expose document title and file metadata."""
    engine = RetrievalEngine()

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            'id': 'c1',
            'doc_id': 'd1',
            'tenant_id': 'default',
            'content': 'Content 1',
            'embedding': [0.1] * 1536,
            'chunk_index': 0,
            'token_count': 2,
            'metadata': {},
            'doc_version': 1,
            'doc_title': 'Design Proposal',
            'doc_file_name': 'design.md',
            'doc_file_md5': 'abc',
            'doc_storage_path': '/app/data/rag/design.md',
            'doc_source_path': '/mnt/rag-import/design.md',
            'score': 0.95
        }
    ]

    with patch.object(engine, '_get_connection', return_value=mock_conn):
        results = await engine.vector_search(
            query_vector=[0.1] * 1536,
            tenant_id="default",
            top_k=10
        )

    assert results[0].metadata["title"] == "Design Proposal"
    assert results[0].metadata["source"] == "design.md"
    assert results[0].metadata["file_md5"] == "abc"


@pytest.mark.asyncio
async def test_vector_search_with_connection():
    """测试向量检索使用数据库连接"""
    engine = RetrievalEngine(pool=AsyncMock())

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            'id': 'c1',
            'doc_id': 'd1',
            'tenant_id': 'default',
            'content': 'Content 1',
            'embedding': [0.1] * 1536,
            'chunk_index': 0,
            'metadata': {},
            'doc_version': 1,
            'score': 0.95
        }
    ]

    with patch.object(engine, '_get_connection', return_value=mock_conn):
        results = await engine.vector_search(
            query_vector=[0.1] * 1536,
            tenant_id="default",
            top_k=10
        )

        assert len(results) == 1
        assert results[0].content == "Content 1"


@pytest.mark.asyncio
async def test_bm25_search_with_connection():
    """测试 BM25 检索使用数据库连接"""
    engine = RetrievalEngine(pool=AsyncMock())

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            'id': 'c1',
            'doc_id': 'd1',
            'tenant_id': 'default',
            'content': 'Content 1',
            'embedding': [0.1] * 1536,
            'chunk_index': 0,
            'metadata': {},
            'doc_version': 1,
            'score': 0.85
        }
    ]

    with patch.object(engine, '_get_connection', return_value=mock_conn):
        results = await engine.bm25_search(
            query="test query",
            tenant_id="default",
            top_k=10
        )

        assert len(results) == 1
        assert results[0].content == "Content 1"


@pytest.mark.asyncio
async def test_score_normalization():
    """测试分数归一化"""
    engine = RetrievalEngine()

    # Test max-min normalization
    scores = [0.1, 0.5, 0.9, 1.0]
    normalized = engine._normalize_scores(scores)

    # Should be normalized to [0, 1]
    assert all(0 <= s <= 1 for s in normalized)
    assert max(normalized) == 1.0
    assert min(normalized) == 0.0


@pytest.mark.asyncio
async def test_deduplication():
    """测试结果去重"""
    engine = RetrievalEngine()

    results = [
        Mock(id="c1", final_score=0.9),
        Mock(id="c2", final_score=0.8),
        Mock(id="c1", final_score=0.7),  # Duplicate
        Mock(id="c3", final_score=0.6),
    ]

    deduplicated = engine._deduplicate_results(results)

    assert len(deduplicated) == 3
    assert all(r.id in ["c1", "c2", "c3"] for r in deduplicated)
    # Should keep the highest score for duplicates
    c1_result = [r for r in deduplicated if r.id == "c1"][0]
    assert c1_result.final_score == 0.9

"""Tests for RAG Agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from i3d_agent.agents.rag import RAGAgent
from i3d_agent.rag.models import Chunk


@pytest.fixture
def rag_agent():
    """Create RAG agent fixture."""
    return RAGAgent()


@pytest.fixture
def mock_chunks():
    """Create mock chunks for testing."""
    return [
        Chunk(
            id="chunk-1",
            doc_id="doc-1",
            tenant_id="default",
            content="API endpoint for 3D search: POST /api/v1/search/3d",
            embedding=[0.1] * 1536,
            chunk_index=0,
            token_count=100,
            metadata={"title": "3D Search API", "section": "API Reference"},
            doc_version=1,
            final_score=0.95
        ),
        Chunk(
            id="chunk-2",
            doc_id="doc-2",
            tenant_id="default",
            content="Deployment requires Docker and PostgreSQL with pgvector",
            embedding=[0.2] * 1536,
            chunk_index=0,
            token_count=80,
            metadata={"title": "Deployment Guide", "section": "Installation"},
            doc_version=1,
            final_score=0.85
        ),
        Chunk(
            id="chunk-3",
            doc_id="doc-1",
            tenant_id="default",
            content="Response format includes results array with metadata",
            embedding=[0.15] * 1536,
            chunk_index=1,
            token_count=90,
            metadata={"title": "3D Search API", "section": "Response Format"},
            doc_version=1,
            final_score=0.75
        )
    ]


class TestRAGAgent:
    """Test RAG Agent functionality."""

    def test_initialization(self, rag_agent):
        """Test agent initialization."""
        assert rag_agent.config.name == "rag"
        assert rag_agent.config.role == "technical_assistant"
        assert len(rag_agent.tools) == 4
        assert rag_agent.retrieval_engine is not None
        assert rag_agent.rerank_service is not None

    @pytest.mark.asyncio
    async def test_answer_empty_question(self, rag_agent):
        """Test answer with empty question."""
        result = await rag_agent.answer("")
        assert result["status"] == "error"
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_answer_whitespace_question(self, rag_agent):
        """Test answer with whitespace-only question."""
        result = await rag_agent.answer("   ")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_answer_success(self, rag_agent, mock_chunks):
        """Test successful answer generation."""
        # Mock the dependencies
        with patch('i3d_agent.rag.embedding.EmbeddingService') as MockEmbeddingService, \
             patch.object(rag_agent.retrieval_engine, 'hybrid_retrieval', new_callable=AsyncMock) as mock_retrieval, \
             patch.object(rag_agent.rerank_service, 'rerank', new_callable=AsyncMock) as mock_rerank, \
             patch('i3d_agent.agents.rag.get_llm_client') as mock_llm:

            # Setup mocks
            mock_embedding_instance = AsyncMock()
            mock_embedding_instance.embed_text.return_value = [0.1] * 1536
            MockEmbeddingService.return_value = mock_embedding_instance

            mock_retrieval.return_value = mock_chunks
            mock_rerank.return_value = mock_chunks[:2]

            mock_llm_client = AsyncMock()
            mock_llm_client.generate.return_value = "根据文档，3D搜索API支持POST请求。"
            mock_llm.return_value = mock_llm_client

            # Execute
            result = await rag_agent.answer(
                question="如何使用3D搜索API？",
                tenant_id="default",
                top_k=5,
                enable_rerank=True
            )

            # Verify
            assert result["status"] == "success"
            assert result["question"] == "如何使用3D搜索API？"
            assert "answer" in result
            assert len(result["sources"]) == 2  # After reranking, we get 2 chunks
            assert result["metadata"]["num_retrieved"] == 2
            assert result["metadata"]["search_type"] == "semantic"  # Chinese question

    @pytest.mark.asyncio
    async def test_answer_no_results(self, rag_agent):
        """Test answer when no documents found."""
        with patch('i3d_agent.rag.embedding.EmbeddingService') as MockEmbeddingService, \
             patch.object(rag_agent.retrieval_engine, 'hybrid_retrieval', new_callable=AsyncMock) as mock_retrieval:

            mock_embedding_instance = AsyncMock()
            mock_embedding_instance.embed_text.return_value = [0.1] * 1536
            MockEmbeddingService.return_value = mock_embedding_instance

            mock_retrieval.return_value = []

            result = await rag_agent.answer("unknown question")

            assert result["status"] == "no_results"
            assert "没有找到" in result["answer"]
            assert len(result["sources"]) == 0

    @pytest.mark.asyncio
    async def test_answer_with_error(self, rag_agent):
        """Test answer when retrieval fails."""
        with patch('i3d_agent.rag.embedding.EmbeddingService') as MockEmbeddingService, \
             patch.object(rag_agent.retrieval_engine, 'hybrid_retrieval', new_callable=AsyncMock) as mock_retrieval:

            mock_embedding_instance = AsyncMock()
            mock_embedding_instance.embed_text.side_effect = Exception("API error")
            MockEmbeddingService.return_value = mock_embedding_instance

            result = await rag_agent.answer("test question")

            assert result["status"] == "error"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_answer_without_rerank(self, rag_agent, mock_chunks):
        """Test answer without reranking enabled."""
        with patch('i3d_agent.rag.embedding.EmbeddingService') as MockEmbeddingService, \
             patch.object(rag_agent.retrieval_engine, 'hybrid_retrieval', new_callable=AsyncMock) as mock_retrieval, \
             patch('i3d_agent.agents.rag.get_llm_client') as mock_llm:

            mock_embedding_instance = AsyncMock()
            mock_embedding_instance.embed_text.return_value = [0.1] * 1536
            MockEmbeddingService.return_value = mock_embedding_instance

            mock_retrieval.return_value = mock_chunks

            mock_llm_client = AsyncMock()
            mock_llm_client.generate.return_value = "Test answer"
            mock_llm.return_value = mock_llm_client

            result = await rag_agent.answer(
                question="test",
                enable_rerank=False
            )

            assert result["status"] == "success"
            # Should use all chunks from retrieval when rerank is disabled
            assert len(result["sources"]) == 3

    @pytest.mark.asyncio
    async def test_build_context(self, rag_agent, mock_chunks):
        """Test context building from chunks."""
        context = rag_agent._build_context(mock_chunks)

        assert "3D Search API" in context
        assert "Deployment Guide" in context
        assert "相关度:" in context
        assert "[文档 1]" in context
        assert "[文档 2]" in context

    @pytest.mark.asyncio
    async def test_generate_answer(self, rag_agent):
        """Test LLM-based answer generation."""
        with patch('i3d_agent.agents.rag.get_llm_client') as mock_llm:
            mock_llm_client = AsyncMock()
            mock_llm_client.generate.return_value = "Generated answer based on context."
            mock_llm.return_value = mock_llm_client

            context = "[文档 1] Test Document\nTest content"
            answer = await rag_agent._generate_answer("Test question", context)

            assert answer == "Generated answer based on context."
            mock_llm_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, rag_agent):
        """Test closing agent connections."""
        with patch.object(rag_agent.rerank_service, 'close', new_callable=AsyncMock) as mock_close:
            await rag_agent.close()
            mock_close.assert_called_once()

    def test_query_classification_semantic(self, rag_agent):
        """Test query classification for semantic questions."""
        search_type = rag_agent.retrieval_engine.classify_query("如何部署系统？")
        assert search_type == "semantic"

    def test_query_classification_keyword(self, rag_agent):
        """Test query classification for keyword queries."""
        search_type = rag_agent.retrieval_engine.classify_query("Error 5001")
        assert search_type == "keyword"

    def test_query_classification_exact_match(self, rag_agent):
        """Test query classification for exact match."""
        search_type = rag_agent.retrieval_engine.classify_query("GET /api/v1/search")
        assert search_type == "exact_match"

    def test_query_classification_balanced(self, rag_agent):
        """Test query classification defaults to balanced."""
        search_type = rag_agent.retrieval_engine.classify_query("search deployment")
        assert search_type == "balanced"

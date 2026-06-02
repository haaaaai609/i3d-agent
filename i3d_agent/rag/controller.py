"""Agentic RAG Controller - orchestrates all RAG capabilities.

The AgenticRAGController coordinates:
- Query expansion via QueryExpansionService
- HyDE via HyDEService
- Hybrid retrieval via RetrievalEngine
- Reranking via RerankService
- Multi-step reasoning with quality assessment
- Query rewriting if quality is insufficient
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from i3d_agent.rag.models import Chunk, RetrievalResult
from i3d_agent.rag.query_expansion import QueryExpansionService
from i3d_agent.rag.hyde import HyDEService
from i3d_agent.rag.retrieval import RetrievalEngine
from i3d_agent.rag.rerank import RerankService
from i3d_agent.rag.embedding import EmbeddingService
from i3d_agent.llm.client import simple_generate
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QualityAssessment:
    """Quality assessment result."""
    is_satisfactory: bool
    issue: Optional[str] = None
    feedback: Optional[str] = None


class AgenticRAGController:
    """
    Agentic RAG Controller - orchestrates all RAG capabilities.

    This controller coordinates:
    - Query expansion for improved recall
    - HyDE (Hypothetical Document Embeddings) for better semantic matching
    - Hybrid retrieval (vector + BM25) for comprehensive results
    - Reranking for improved precision
    - Multi-step reasoning with quality assessment
    - Query rewriting when quality is insufficient

    Usage:
        controller = AgenticRAGController()
        result = await controller.retrieve(
            query="How to configure API?",
            tenant_id="default",
            enable_expansion=True,
            enable_hyde=True,
            enable_rerank=True,
            top_k=5
        )
    """

    # Quality assessment thresholds
    MIN_RESULTS_COUNT = 3
    MIN_AVG_SCORE = 0.5
    MIN_TOP_SCORE = 0.7

    def __init__(
        self,
        query_expansion: Optional[QueryExpansionService] = None,
        hyde_service: Optional[HyDEService] = None,
        retrieval_engine: Optional[RetrievalEngine] = None,
        rerank_service: Optional[RerankService] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Initialize AgenticRAGController.

        Args:
            query_expansion: Optional query expansion service
            hyde_service: Optional HyDE service
            retrieval_engine: Optional retrieval engine
            rerank_service: Optional rerank service
            embedding_service: Optional embedding service
        """
        self.query_expansion = query_expansion or QueryExpansionService()
        self.hyde_service = hyde_service or HyDEService()
        self.retrieval_engine = retrieval_engine or RetrievalEngine()
        self.rerank_service = rerank_service or RerankService()
        self.embedding_service = embedding_service or EmbeddingService()

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        query_vector: Optional[List[float]] = None,
        enable_expansion: bool = True,
        enable_hyde: bool = True,
        enable_rerank: bool = True,
        top_k: int = 10,
        search_type: Optional[str] = None,
        alpha: Optional[float] = None,
        beta: Optional[float] = None
    ) -> RetrievalResult:
        """
        Perform retrieval with all optional features.

        Coordinates: query expansion → HyDE → parallel retrieval →
        deduplication → reranking

        Args:
            query: Search query
            tenant_id: Tenant identifier
            query_vector: Optional pre-computed query embedding
            enable_expansion: Enable query expansion
            enable_hyde: Enable HyDE
            enable_rerank: Enable reranking
            top_k: Number of results to return
            search_type: Optional search type for hybrid retrieval
            alpha: Optional vector weight
            beta: Optional BM25 weight

        Returns:
            RetrievalResult with results and metadata
        """
        all_chunks = []
        query_expansions = []
        hypothetical_doc = None

        # Step 1: Query expansion
        if enable_expansion:
            query_expansions = await self.query_expansion.expand_query(query)
            logger.info(f"Expanded query into {len(query_expansions)} variations")
        else:
            query_expansions = [query]

        # Step 2: HyDE - generate hypothetical document
        if enable_hyde:
            hypothetical_doc = await self.hyde_service.generate_hypothetical(query)
            if hypothetical_doc:
                logger.info(f"Generated hypothetical document for query")

        # Step 3: Parallel retrieval for all query variations
        retrieval_queries = query_expansions.copy()

        # Add hypothetical doc as a query if generated
        if hypothetical_doc:
            retrieval_queries.append(hypothetical_doc)

        # Get embedding for each query variant
        for query_text in retrieval_queries:
            if query_vector is None or query_text != query:
                # Need to get embedding for this query
                try:
                    query_emb = await self.embedding_service.embed_text(query_text)
                except Exception as e:
                    logger.warning(f"Failed to embed query '{query_text[:50]}...': {e}")
                    query_emb = []
            else:
                query_emb = query_vector

            if not query_emb:
                logger.warning(f"Empty embedding for query '{query_text[:50]}...', skipping")
                continue

            # Perform hybrid retrieval
            try:
                chunks = await self.retrieval_engine.hybrid_retrieval(
                    query=query_text,
                    query_vector=query_emb,
                    tenant_id=tenant_id,
                    top_k=top_k * 2,  # Get more for deduplication
                    search_type=search_type,
                    alpha=alpha,
                    beta=beta
                )
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Retrieval failed for query '{query_text[:50]}...': {e}")

        # Step 4: Deduplicate and merge results
        merged_chunks = self._deduplicate_and_merge(all_chunks)

        # Step 5: Reranking
        if enable_rerank and merged_chunks:
            try:
                merged_chunks = await self.rerank_service.rerank(
                    query=query,
                    chunks=merged_chunks,
                    top_k=top_k
                )
            except Exception as e:
                logger.error(f"Reranking failed: {e}")

        # Keep only top_k results
        final_results = merged_chunks[:top_k]

        return RetrievalResult(
            results=final_results,
            query=query,
            iterations=1,
            query_expansions=query_expansions if enable_expansion else [],
            hypothetical_doc=hypothetical_doc
        )

    async def retrieve_with_multi_step(
        self,
        query: str,
        tenant_id: str,
        query_vector: Optional[List[float]] = None,
        max_iterations: int = 3,
        enable_expansion: bool = True,
        enable_hyde: bool = True,
        enable_rerank: bool = True,
        top_k: int = 10,
        search_type: Optional[str] = None
    ) -> RetrievalResult:
        """
        Perform retrieval with multi-step reasoning.

        Iteratively retrieves and assesses quality, rewriting query if needed.

        Args:
            query: Search query
            tenant_id: Tenant identifier
            query_vector: Optional pre-computed query embedding
            max_iterations: Maximum number of iterations
            enable_expansion: Enable query expansion
            enable_hyde: Enable HyDE
            enable_rerank: Enable reranking
            top_k: Number of results to return
            search_type: Optional search type

        Returns:
            RetrievalResult with multi-step metadata
        """
        current_query = query
        current_vector = query_vector
        all_chunks = []
        all_expansions = []
        hypothetical_doc = None

        for iteration in range(1, max_iterations + 1):
            logger.info(f"Multi-step iteration {iteration}/{max_iterations}")

            # Get embedding for current query if needed
            if current_vector is None:
                try:
                    current_vector = await self.embedding_service.embed_text(current_query)
                except Exception as e:
                    logger.warning(f"Failed to embed query: {e}")
                    current_vector = []

            # Perform retrieval
            result = await self.retrieve(
                query=current_query,
                query_vector=current_vector,
                tenant_id=tenant_id,
                enable_expansion=enable_expansion and iteration == 1,
                enable_hyde=enable_hyde and iteration == 1,
                enable_rerank=enable_rerank,
                top_k=top_k,
                search_type=search_type
            )

            all_chunks = result.results
            all_expansions.extend(result.query_expansions)
            hypothetical_doc = result.hypothetical_doc

            # Assess quality
            assessment = await self._assess_quality(all_chunks, current_query)

            if assessment.is_satisfactory:
                logger.info(f"Quality satisfactory after {iteration} iteration(s)")
                return RetrievalResult(
                    results=all_chunks,
                    query=query,
                    iterations=iteration,
                    query_expansions=all_expansions,
                    hypothetical_doc=hypothetical_doc
                )

            # Need to rewrite query
            logger.info(f"Quality not satisfactory: {assessment.issue}")
            if iteration < max_iterations:
                current_query = await self._rewrite_query(
                    current_query,
                    assessment.feedback or ""
                )
                current_vector = None  # Will be re-embedded
                logger.info(f"Rewritten query: {current_query[:50]}...")

        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached")
        return RetrievalResult(
            results=all_chunks,
            query=query,
            iterations=max_iterations,
            query_expansions=all_expansions,
            hypothetical_doc=hypothetical_doc
        )

    async def _assess_quality(
        self,
        chunks: List[Chunk],
        query: str
    ) -> QualityAssessment:
        """
        Assess the quality of retrieval results.

        Evaluates:
        - Result count (need minimum number of results)
        - Average score (need decent overall quality)
        - Top score (need at least one high-quality result)

        Args:
            chunks: Retrieved chunks
            query: Original query (for potential LLM assessment)

        Returns:
            QualityAssessment with satisfaction status
        """
        # Check result count
        if len(chunks) < self.MIN_RESULTS_COUNT:
            return QualityAssessment(
                is_satisfactory=False,
                issue="insufficient_results",
                feedback=f"Only {len(chunks)} results found, need at least {self.MIN_RESULTS_COUNT}. Try using broader terms or different keywords."
            )

        # Check scores
        scores = [c.final_score or 0.0 for c in chunks]
        avg_score = sum(scores) / len(scores)
        top_score = max(scores)

        if top_score < self.MIN_TOP_SCORE:
            return QualityAssessment(
                is_satisfactory=False,
                issue="low_score",
                feedback=f"Top score is {top_score:.2f}, below threshold {self.MIN_TOP_SCORE}. Results may not be relevant. Try rephrasing with more specific terms."
            )

        if avg_score < self.MIN_AVG_SCORE:
            return QualityAssessment(
                is_satisfactory=False,
                issue="low_avg_score",
                feedback=f"Average score is {avg_score:.2f}, below threshold {self.MIN_AVG_SCORE}. Overall result quality is low. Consider using different search terms."
            )

        # Quality is satisfactory
        return QualityAssessment(
            is_satisfactory=True,
            issue=None,
            feedback=None
        )

    async def _rewrite_query(
        self,
        query: str,
        feedback: str
    ) -> str:
        """
        Rewrite query based on quality assessment feedback.

        Args:
            query: Original query
            feedback: Quality assessment feedback

        Returns:
            Rewritten query string
        """
        if not feedback:
            return query

        try:
            system_prompt = """你是一个查询优化专家。根据给定的反馈，改写用户的搜索查询以提高检索质量。

规则：
1. 保持原始意图，但使用更精确的词汇
2. 添加相关的技术术语或同义词
3. 移除模糊或不重要的词
4. 使用清晰、具体的表达
5. 只输出改写后的查询，不要有其他内容"""

            user_prompt = f"""原始查询：{query}

反馈：{feedback}

请改写查询以提高检索质量："""

            rewritten = await simple_generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )

            # Clean the response
            rewritten = rewritten.strip()
            if rewritten and rewritten != query:
                logger.info(f"Query rewritten: '{query[:50]}...' -> '{rewritten[:50]}...'")
                return rewritten

        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")

        # Fallback to original query
        return query

    def _deduplicate_and_merge(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Deduplicate chunks by ID, keeping highest score version.

        Args:
            chunks: List of chunks to deduplicate

        Returns:
            Deduplicated list sorted by final_score
        """
        seen = {}
        for chunk in chunks:
            if chunk.id not in seen:
                seen[chunk.id] = chunk
            else:
                # Keep the one with higher final_score
                existing = seen[chunk.id]
                if (chunk.final_score or 0.0) > (existing.final_score or 0.0):
                    seen[chunk.id] = chunk

        # Sort by final_score descending
        deduplicated = list(seen.values())
        deduplicated.sort(key=lambda x: x.final_score or 0.0, reverse=True)

        return deduplicated

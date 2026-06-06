"""RetrievalEngine for hybrid vector and BM25 search."""

from typing import Optional, List, Dict, Any, Tuple
import re
import asyncpg
import numpy as np
import json

from i3d_agent.rag.models import Chunk
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_vector(vec: Any) -> List[float]:
    """
    Safely parse a vector from database response.

    Handles both string format "[0.1,0.2,...]" and list format.
    """
    if vec is None:
        return []
    if isinstance(vec, list):
        return [float(x) for x in vec]
    if isinstance(vec, str):
        # Remove brackets and split by comma
        vec = vec.strip()
        if vec.startswith('[') and vec.endswith(']'):
            vec = vec[1:-1]
        if not vec:
            return []
        return [float(x.strip()) for x in vec.split(',') if x.strip()]
    # Fallback: try to convert to list
    return list(vec)


def _preview_query(query: str, limit: int = 80) -> str:
    """Return a single-line preview for logging."""
    preview = " ".join((query or "").split())
    if len(preview) > limit:
        return f"{preview[:limit]}..."
    return preview


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    """Read a key from asyncpg records, dicts, or test doubles."""
    try:
        value = row.get(key, default)
    except AttributeError:
        try:
            value = row[key]
        except (KeyError, IndexError, TypeError):
            value = default
    except KeyError:
        value = default
    return value


def _metadata_from_row(row: Any) -> Dict[str, Any]:
    """Merge chunk metadata with document-level fields selected by retrieval."""
    metadata = _row_get(row, 'metadata') or {}
    if not isinstance(metadata, dict):
        metadata = {}
    else:
        metadata = dict(metadata)

    document_fields = {
        "title": _row_get(row, "doc_title"),
        "file_name": _row_get(row, "doc_file_name"),
        "file_md5": _row_get(row, "doc_file_md5"),
        "storage_path": _row_get(row, "doc_storage_path"),
        "source_path": _row_get(row, "doc_source_path"),
    }
    for key, value in document_fields.items():
        if value is not None and (key not in metadata or not metadata.get(key)):
            metadata[key] = value

    if not metadata.get("source"):
        metadata["source"] = (
            metadata.get("file_name")
            or metadata.get("source_path")
            or metadata.get("storage_path")
            or metadata.get("title")
        )

    return metadata


class RetrievalEngine:
    """
    Hybrid retrieval engine combining vector and BM25 search.

    Features:
    - HNSW vector similarity search using pgvector
    - Full-text search using PostgreSQL tsvector
    - Hybrid retrieval with score fusion
    - Dynamic weight adjustment based on search type
    - Automatic query classification
    - Result deduplication and normalization
    """

    # Search type weight configurations (alpha for vector, beta for BM25)
    WEIGHT_CONFIGS = {
        "semantic": (0.8, 0.2),      # Focus on vector similarity
        "keyword": (0.3, 0.7),        # Focus on BM25 matching
        "balanced": (0.5, 0.5),       # Equal weighting
        "exact_match": (0.1, 0.9)     # Heavy BM25 for precise matches
    }

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        """
        Initialize RetrievalEngine.

        Args:
            pool: Optional asyncpg connection pool
        """
        self.pool = pool
        self._conn: Optional[asyncpg.Connection] = None

    async def _get_connection(self) -> asyncpg.Connection:
        """Get database connection."""
        if self._conn:
            return self._conn
        if self.pool:
            return await self.pool.acquire()
        raise RuntimeError("No database connection available")

    async def _release_connection(self, conn: asyncpg.Connection):
        """Release connection back to pool."""
        if self.pool and conn != self._conn:
            await self.pool.release(conn)

    def classify_query(self, query: str) -> str:
        """
        Classify query type based on patterns.

        Args:
            query: Search query string

        Returns:
            Search type: semantic, keyword, balanced, or exact_match
        """
        query_lower = query.lower().strip()

        # Error codes and technical identifiers -> keyword
        error_pattern = r'(err_|error|exception|fail|fatal|critical)'
        if re.search(error_pattern, query_lower, re.IGNORECASE):
            return "keyword"

        # API paths and URLs -> exact_match
        url_pattern = r'^(get|post|put|delete|patch)?\s*/(api|v1|v2)[/\w]*'
        if re.search(url_pattern, query_lower, re.IGNORECASE):
            return "exact_match"

        # Questions and how-to -> semantic
        question_pattern = r'^(how|what|why|when|where|who|which|can|could|would|should|is|are|do|does|à|ù|é|è)'
        if re.search(question_pattern, query_lower, re.IGNORECASE):
            return "semantic"

        # Chinese questions -> semantic
        chinese_pattern = r'^(如何|怎么|什么是|为什么|哪个|哪些|能否|可以)'
        if re.search(chinese_pattern, query_lower):
            return "semantic"

        # Default to balanced
        return "balanced"

    async def vector_search(
        self,
        query_vector: List[float],
        tenant_id: str,
        top_k: int = 10,
        threshold: Optional[float] = None
    ) -> List[Chunk]:
        """
        Perform HNSW vector similarity search.

        Args:
            query_vector: Query embedding vector
            tenant_id: Tenant identifier
            top_k: Number of results to return
            threshold: Optional similarity threshold

        Returns:
            List of Chunk objects with vector_score set
        """
        conn = await self._get_connection()
        try:
            # Convert vector list to pgvector format string: [0.1,0.2,0.3,...]
            vector_str = f"[{','.join(str(x) for x in query_vector)}]"

            query = """
                SELECT
                    c.id, c.doc_id, c.tenant_id, c.content, c.embedding,
                    c.chunk_index, c.token_count, c.metadata, c.doc_version,
                    d.title AS doc_title, d.file_name AS doc_file_name,
                    d.file_md5 AS doc_file_md5, d.storage_path AS doc_storage_path,
                    d.source_path AS doc_source_path,
                    1 - (c.embedding <=> $1::vector) as score
                FROM rag_chunks c
                JOIN rag_documents d ON d.id = c.doc_id
                WHERE c.tenant_id = $2
                    AND d.tenant_id = $2
                    AND c.deleted_at IS NULL
                    AND d.deleted_at IS NULL
                    AND d.is_latest = true
                    AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> $1::vector
                LIMIT $3
            """

            params = [vector_str, tenant_id, top_k]

            if threshold is not None:
                query = """
                    SELECT
                        c.id, c.doc_id, c.tenant_id, c.content, c.embedding,
                        c.chunk_index, c.token_count, c.metadata, c.doc_version,
                        d.title AS doc_title, d.file_name AS doc_file_name,
                        d.file_md5 AS doc_file_md5, d.storage_path AS doc_storage_path,
                        d.source_path AS doc_source_path,
                        1 - (c.embedding <=> $1::vector) as score
                    FROM rag_chunks c
                    JOIN rag_documents d ON d.id = c.doc_id
                    WHERE c.tenant_id = $2
                        AND d.tenant_id = $2
                        AND c.deleted_at IS NULL
                        AND d.deleted_at IS NULL
                        AND d.is_latest = true
                        AND c.embedding IS NOT NULL
                        AND (1 - (c.embedding <=> $1::vector)) >= $4
                    ORDER BY c.embedding <=> $1::vector
                    LIMIT $3
                """
                params.append(threshold)

            rows = await conn.fetch(query, *params)

            logger.debug(f"Vector search returned {len(rows)} chunks (tenant: {tenant_id}, top_k: {top_k})")

            results = []
            for row in rows:
                # Safely parse embedding from pgvector
                embedding = _parse_vector(_row_get(row, 'embedding'))
                metadata = _metadata_from_row(row)

                chunk = Chunk(
                    id=str(row['id']),
                    doc_id=str(row['doc_id']),
                    tenant_id=row['tenant_id'],
                    content=row['content'],
                    embedding=embedding,
                    chunk_index=row['chunk_index'],
                    token_count=_row_get(row, 'token_count'),
                    metadata=metadata,
                    doc_version=row['doc_version'],
                    vector_score=float(row['score']),
                    bm25_score=None,
                    final_score=None
                )
                results.append(chunk)

            return results

        finally:
            await self._release_connection(conn)

    async def bm25_search(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 10,
        threshold: Optional[float] = None
    ) -> List[Chunk]:
        """
        Perform BM25 full-text search using PostgreSQL tsvector.

        Args:
            query: Search query string
            tenant_id: Tenant identifier
            top_k: Number of results to return
            threshold: Optional score threshold

        Returns:
            List of Chunk objects with bm25_score set
        """
        conn = await self._get_connection()
        try:
            search_query = query
            # Use ts_rank for BM25-like scoring
            sql = """
                SELECT
                    c.id, c.doc_id, c.tenant_id, c.content, c.embedding,
                    c.chunk_index, c.token_count, c.metadata, c.doc_version,
                    d.title AS doc_title, d.file_name AS doc_file_name,
                    d.file_md5 AS doc_file_md5, d.storage_path AS doc_storage_path,
                    d.source_path AS doc_source_path,
                    ts_rank(c.content_tsv, plainto_tsquery('simple', $1)) as score
                FROM rag_chunks c
                JOIN rag_documents d ON d.id = c.doc_id
                WHERE c.tenant_id = $2
                    AND d.tenant_id = $2
                    AND c.deleted_at IS NULL
                    AND d.deleted_at IS NULL
                    AND d.is_latest = true
                    AND c.content_tsv @@ plainto_tsquery('simple', $1)
                ORDER BY score DESC
                LIMIT $3
            """

            params = [search_query, tenant_id, top_k]

            if threshold is not None:
                sql = """
                    SELECT
                        c.id, c.doc_id, c.tenant_id, c.content, c.embedding,
                        c.chunk_index, c.token_count, c.metadata, c.doc_version,
                        d.title AS doc_title, d.file_name AS doc_file_name,
                        d.file_md5 AS doc_file_md5, d.storage_path AS doc_storage_path,
                        d.source_path AS doc_source_path,
                        ts_rank(c.content_tsv, plainto_tsquery('simple', $1)) as score
                    FROM rag_chunks c
                    JOIN rag_documents d ON d.id = c.doc_id
                    WHERE c.tenant_id = $2
                        AND d.tenant_id = $2
                        AND c.deleted_at IS NULL
                        AND d.deleted_at IS NULL
                        AND d.is_latest = true
                        AND c.content_tsv @@ plainto_tsquery('simple', $1)
                        AND ts_rank(c.content_tsv, plainto_tsquery('simple', $1)) >= $4
                    ORDER BY score DESC
                    LIMIT $3
                """
                params.append(threshold)

            rows = await conn.fetch(sql, *params)

            logger.debug(
                f"BM25 search returned {len(rows)} chunks for query "
                f"'{_preview_query(search_query)}' (tenant: {tenant_id}, top_k: {top_k})"
            )

            results = []
            for row in rows:
                # Safely parse embedding from pgvector
                embedding = _parse_vector(_row_get(row, 'embedding'))
                metadata = _metadata_from_row(row)

                chunk = Chunk(
                    id=str(row['id']),
                    doc_id=str(row['doc_id']),
                    tenant_id=row['tenant_id'],
                    content=row['content'],
                    embedding=embedding,
                    chunk_index=row['chunk_index'],
                    token_count=_row_get(row, 'token_count'),
                    metadata=metadata,
                    doc_version=row['doc_version'],
                    vector_score=None,
                    bm25_score=float(row['score']),
                    final_score=None
                )
                results.append(chunk)

            return results

        finally:
            await self._release_connection(conn)

    async def hybrid_retrieval(
        self,
        query: str,
        query_vector: List[float],
        tenant_id: str,
        top_k: int = 10,
        search_type: Optional[str] = None,
        alpha: Optional[float] = None,
        beta: Optional[float] = None
    ) -> List[Chunk]:
        """
        Perform hybrid retrieval combining vector and BM25 search.

        Args:
            query: Search query string
            query_vector: Query embedding vector
            tenant_id: Tenant identifier
            top_k: Number of results to return
            search_type: Type of search (semantic, keyword, balanced, exact_match)
            alpha: Optional custom vector weight
            beta: Optional custom BM25 weight

        Returns:
            List of Chunk objects with fused final_score
        """
        # Determine search type if not provided
        if search_type is None:
            search_type = self.classify_query(query)

        # Get weights
        if alpha is not None and beta is not None:
            weights = (alpha, beta)
        else:
            weights = self.WEIGHT_CONFIGS.get(search_type, self.WEIGHT_CONFIGS["balanced"])

        alpha, beta = weights

        # Perform both searches in parallel
        import asyncio
        vector_results, bm25_results = await asyncio.gather(
            self.vector_search(query_vector, tenant_id, top_k * 2),
            self.bm25_search(query, tenant_id, top_k * 2)
        )

        logger.debug(
            f"Hybrid retrieval: vector={len(vector_results)}, bm25={len(bm25_results)} "
            f"results (search_type: {search_type}, alpha: {alpha}, beta: {beta})"
        )

        # Create lookup for BM25 results
        bm25_lookup = {result.id: result for result in bm25_results}

        # Merge results
        merged_results = []
        seen_ids = set()

        for v_result in vector_results:
            if v_result.id in seen_ids:
                continue
            seen_ids.add(v_result.id)

            # Get corresponding BM25 result if exists
            b_result = bm25_lookup.get(v_result.id)

            # Normalize scores
            vector_norm = v_result.vector_score if v_result.vector_score else 0.0
            bm25_norm = b_result.bm25_score if b_result and b_result.bm25_score else 0.0

            # Calculate final score
            final_score = alpha * vector_norm + beta * bm25_norm

            metadata = dict(v_result.metadata or {})
            metadata["score_detail"] = {
                "vector_weight": alpha,
                "bm25_weight": beta,
                "search_type": search_type,
                "formula": "final_score = vector_weight * vector_score + bm25_weight * bm25_score",
            }

            # Create merged chunk
            merged_chunk = Chunk(
                id=v_result.id,
                doc_id=v_result.doc_id,
                tenant_id=v_result.tenant_id,
                content=v_result.content,
                embedding=v_result.embedding,
                chunk_index=v_result.chunk_index,
                token_count=v_result.token_count,
                metadata=metadata,
                doc_version=v_result.doc_version,
                vector_score=v_result.vector_score,
                bm25_score=b_result.bm25_score if b_result else 0.0,
                final_score=final_score
            )
            merged_results.append(merged_chunk)

        # Add BM25-only results
        for b_result in bm25_results:
            if b_result.id not in seen_ids:
                seen_ids.add(b_result.id)

                vector_norm = 0.0
                bm25_norm = b_result.bm25_score if b_result.bm25_score else 0.0
                final_score = alpha * vector_norm + beta * bm25_norm

                metadata = dict(b_result.metadata or {})
                metadata["score_detail"] = {
                    "vector_weight": alpha,
                    "bm25_weight": beta,
                    "search_type": search_type,
                    "formula": "final_score = vector_weight * vector_score + bm25_weight * bm25_score",
                }

                merged_chunk = Chunk(
                    id=b_result.id,
                    doc_id=b_result.doc_id,
                    tenant_id=b_result.tenant_id,
                    content=b_result.content,
                    embedding=b_result.embedding,
                    chunk_index=b_result.chunk_index,
                    token_count=b_result.token_count,
                    metadata=metadata,
                    doc_version=b_result.doc_version,
                    vector_score=0.0,
                    bm25_score=b_result.bm25_score,
                    final_score=final_score
                )
                merged_results.append(merged_chunk)

        # Sort by final score and return top_k
        merged_results.sort(key=lambda x: x.final_score or 0.0, reverse=True)
        final_results = merged_results[:top_k]
        logger.debug(f"Hybrid retrieval merged and deduplicated to {len(final_results)} chunks (returned top_k: {top_k})")
        return final_results

    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """
        Normalize scores using min-max normalization.

        Args:
            scores: List of raw scores

        Returns:
            List of normalized scores in [0, 1]
        """
        if not scores:
            return []

        scores_array = np.array(scores)
        min_score = np.min(scores_array)
        max_score = np.max(scores_array)

        if max_score == min_score:
            # All scores are the same, return normalized to 0.5
            return [0.5] * len(scores)

        normalized = (scores_array - min_score) / (max_score - min_score)
        return normalized.tolist()

    def _deduplicate_results(self, results: List[Chunk]) -> List[Chunk]:
        """
        Deduplicate results keeping highest score for each ID.

        Args:
            results: List of Chunk results

        Returns:
            Deduplicated list of Chunks
        """
        seen = {}
        for result in results:
            if result.id not in seen:
                seen[result.id] = result
            else:
                # Keep the one with higher final_score
                existing = seen[result.id]
                if (result.final_score or 0) > (existing.final_score or 0):
                    seen[result.id] = result

        return list(seen.values())

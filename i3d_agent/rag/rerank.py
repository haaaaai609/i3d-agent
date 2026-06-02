"""Rerank service for improving retrieval quality using Cohere Rerank API."""

from typing import List, Dict, Any, Optional
import httpx
from i3d_agent.config.settings import get_settings
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class RerankService:
    """Rerank 服务 - 使用 Cohere API 对检索结果重排序"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client

    async def rerank(
        self,
        query: str,
        chunks: List[Any],
        top_k: int = 5
    ) -> List[Any]:
        """对 chunks 进行重排序

        Args:
            query: 查询文本
            chunks: chunk 列表（可以是任何包含 id/content 的对象）
            top_k: 返回的前 k 个结果

        Returns:
            重排序后的 chunk 列表
        """
        if not chunks:
            logger.warning("Empty chunks provided for reranking")
            return []

        # 如果没有 API key，直接返回原始顺序
        if not self.settings.COHERE_API_KEY:
            logger.debug("No Cohere API key configured, returning original order")
            return list(chunks[:top_k])

        # 提取 chunk 内容
        documents = [self._extract_content(chunk) for chunk in chunks]

        try:
            # 调用 Cohere Rerank API
            rerank_results = await self._call_cohere_rerank(
                await self._get_client(),
                query,
                documents
            )

            # 根据返回的索引重新排序 chunks
            reranked_chunks = []
            for result in rerank_results[:top_k]:
                index = result.get("index")
                if 0 <= index < len(chunks):
                    reranked_chunks.append(chunks[index])

            # 如果 API 返回的结果少于 top_k，补充原始顺序的结果
            if len(reranked_chunks) < top_k:
                remaining_indices = set(range(len(chunks))) - {
                    r.get("index") for r in rerank_results if "index" in r
                }
                for idx in sorted(remaining_indices):
                    if len(reranked_chunks) >= top_k:
                        break
                    reranked_chunks.append(chunks[idx])

            logger.info(f"Reranked {len(reranked_chunks)} chunks for query: {query[:50]}...")
            return reranked_chunks

        except Exception as e:
            logger.error(f"Rerank API call failed: {e}, falling back to original order")
            # 失败时返回原始顺序
            return list(chunks[:top_k])

    def _extract_content(self, chunk: Any) -> str:
        """从 chunk 中提取文本内容

        Args:
            chunk: chunk 对象（可以是字典或对象）

        Returns:
            文本内容
        """
        if isinstance(chunk, dict):
            return chunk.get("content", "")
        else:
            # 假设是对象，尝试获取 content 属性
            return getattr(chunk, "content", "")

    async def _call_cohere_rerank(
        self,
        client: httpx.AsyncClient,
        query: str,
        documents: List[str]
    ) -> List[Dict[str, Any]]:
        """调用 Cohere Rerank API

        Args:
            client: HTTP 客户端
            query: 查询文本
            documents: 文档列表

        Returns:
            重排序结果列表，每个结果包含 index 和 relevance_score

        Raises:
            Exception: API 调用失败时抛出异常
        """
        url = "https://api.cohere.ai/v1/rerank"

        headers = {
            "Authorization": f"Bearer {self.settings.COHERE_API_KEY}",
            "Content-Type": "application/json",
            "X-Client-Name": "i3d-agent-system"
        }

        data = {
            "model": self.settings.COHERE_RERANK_MODEL,
            "query": query,
            "documents": documents,
            "top_n": len(documents),
            "return_documents": False
        }

        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()

            # Cohere 响应格式: {"results": [{"index": 0, "relevance_score": 0.95}, ...]}
            return result.get("results", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Cohere API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to call Cohere Rerank API: {e}")
            raise

    async def close(self):
        """关闭客户端连接"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.debug("RerankService client closed")

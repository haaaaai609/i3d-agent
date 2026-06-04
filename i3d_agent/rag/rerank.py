"""Rerank service for improving retrieval quality using DashScope Qwen3-VL-Rerank API."""

from typing import List, Dict, Any, Optional
import httpx
from i3d_agent.config.settings import get_settings
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class RerankService:
    """Rerank 服务 - 使用 DashScope Qwen3-VL-Rerank API 对检索结果重排序"""

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
        if not self.settings.DASHSCOPE_API_KEY:
            logger.debug("No DashScope API key configured, returning original order")
            return list(chunks[:top_k])

        # 如果 chunks 数量小于等于 top_k，直接返回
        if len(chunks) <= top_k:
            return list(chunks)

        # 提取 chunk 内容
        documents = [self._extract_content(chunk) for chunk in chunks]

        try:
            # 调用 DashScope Rerank API
            rerank_results = await self._call_dashscope_rerank(
                await self._get_client(),
                query,
                documents,
                top_n=top_k
            )

            # 根据返回的索引重新排序 chunks
            reranked_chunks = []
            for result in rerank_results:
                index = result.get("index")
                if 0 <= index < len(chunks):
                    chunk = chunks[index]
                    # 更新 relevance score
                    score = result.get("relevance_score")
                    if score is not None:
                        if hasattr(chunk, "final_score"):
                            chunk.final_score = score
                        elif isinstance(chunk, dict):
                            chunk["final_score"] = score
                    reranked_chunks.append(chunk)

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

    async def _call_dashscope_rerank(
        self,
        client: httpx.AsyncClient,
        query: str,
        documents: List[str],
        top_n: int
    ) -> List[Dict[str, Any]]:
        """调用 DashScope Qwen3-VL-Rerank API

        Args:
            client: HTTP 客户端
            query: 查询文本
            documents: 文档列表
            top_n: 返回的前 N 个结果

        Returns:
            重排序结果列表，每个结果包含 index 和 relevance_score

        Raises:
            Exception: API 调用失败时抛出异常
        """
        url = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

        headers = {
            "Authorization": f"Bearer {self.settings.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "qwen3-vl-rerank",
            "input": {
                "query": query,
                "documents": documents
            },
            "parameters": {
                "return_documents": False,
                "top_n": top_n
            }
        }

        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()

            # DashScope 响应格式: {"output": {"results": [{"index": 0, "relevance_score": 0.95}, ...]}}
            if "output" in result and "results" in result["output"]:
                return result["output"]["results"]
            else:
                logger.warning(f"Unexpected DashScope API response format: {result}")
                return []

        except httpx.HTTPStatusError as e:
            logger.error(f"DashScope API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to call DashScope Rerank API: {e}")
            raise

    async def close(self):
        """关闭客户端连接"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.debug("RerankService client closed")

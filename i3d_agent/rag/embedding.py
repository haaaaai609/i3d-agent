"""Embedding service for generating vector representations."""

from typing import List, Dict, Any, Optional
import httpx
from i3d_agent.config.settings import get_settings
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Embedding 服务 - 生成文本向量表示"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=60.0)
        return self.client

    async def embed_text(self, text: str) -> List[float]:
        """为单个文本生成 embedding

        Args:
            text: 输入文本

        Returns:
            embedding 向量
        """
        if not text:
            logger.warning("Empty text provided for embedding")

        embeddings = await self._call_embedding_api([text])
        return embeddings[0] if embeddings else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        if not texts:
            logger.warning("Empty text list provided for embedding")
            return []

        return await self._call_embedding_api(texts)

    async def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为 chunk 列表生成 embedding

        Args:
            chunks: chunk 字典列表，每个 chunk 必须包含 'content' 字段

        Returns:
            添加了 'embedding' 字段的 chunk 列表
        """
        if not chunks:
            logger.warning("Empty chunk list provided for embedding")
            return []

        # DashScope API 限制：
        # - 输入文本总长度不能超过 8192 字符
        # - 每批最多 10 个 chunks
        MAX_BATCH_CHARS = 7000  # 留一些余量
        MAX_BATCH_SIZE = 10  # DashScope API 限制
        results = []

        current_batch = []
        current_batch_chars = 0

        for chunk in chunks:
            content = chunk.get("content", "")
            content_chars = len(content)

            # 如果单个 chunk 就超过限制，截断它
            if content_chars > MAX_BATCH_CHARS:
                logger.warning(f"Chunk too long ({content_chars} chars), truncating to {MAX_BATCH_CHARS}")
                # 创建修改后的 chunk 副本
                chunk = {**chunk, "content": content[:MAX_BATCH_CHARS]}
                content_chars = MAX_BATCH_CHARS

            # 检查是否需要开始新批次（字符长度或数量限制）
            should_start_new_batch = False
            if current_batch_chars + content_chars > MAX_BATCH_CHARS and current_batch:
                should_start_new_batch = True
            elif len(current_batch) >= MAX_BATCH_SIZE:
                should_start_new_batch = True

            if should_start_new_batch:
                # 处理当前批次
                batch_embeddings = await self._process_batch(current_batch)
                results.extend(batch_embeddings)
                # 开始新批次
                current_batch = [chunk]
                current_batch_chars = content_chars
            else:
                current_batch.append(chunk)
                current_batch_chars += content_chars

        # 处理最后一批
        if current_batch:
            batch_embeddings = await self._process_batch(current_batch)
            results.extend(batch_embeddings)

        logger.info(f"Generated embeddings for {len(results)} chunks")
        return results

    async def _process_batch(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理一批 chunks，生成 embedding"""
        texts = [chunk.get("content", "") for chunk in chunks]
        logger.debug(f"Processing batch: {len(chunks)} chunks, total chars: {sum(len(t) for t in texts)}")
        embeddings = await self._call_embedding_api(texts)
        logger.debug(f"Got {len(embeddings)} embeddings from API")

        # 将 embedding 添加到每个 chunk
        results = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_copy = dict(chunk)  # 避免修改原始数据
            chunk_copy["embedding"] = embedding
            results.append(chunk_copy)

        return results

    async def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """调用 Embedding API

        根据配置自动选择 DashScope 或 OpenAI API

        Args:
            texts: 要生成 embedding 的文本列表

        Returns:
            embedding 向量列表

        Raises:
            Exception: API 调用失败时抛出异常
        """
        try:
            client = await self._get_client()

            # 根据配置选择 API
            if self.settings.DASHSCOPE_API_KEY and self.settings.DASHSCOPE_API_KEY != "":
                logger.debug(f"Using DashScope API for {len(texts)} texts")
                return await self._call_dashscope(client, texts)
            elif self.settings.OPENAI_API_KEY and self.settings.OPENAI_API_KEY != "":
                logger.debug(f"Using OpenAI API for {len(texts)} texts")
                return await self._call_openai(client, texts)
            else:
                raise ValueError(
                    "No API key configured. Please set DASHSCOPE_API_KEY or OPENAI_API_KEY"
                )

        except Exception as e:
            logger.error(f"Failed to call embedding API: {e}")
            raise

    async def _call_dashscope(
        self, client: httpx.AsyncClient, texts: List[str]
    ) -> List[List[float]]:
        """调用 DashScope Embedding API

        Args:
            client: HTTP 客户端
            texts: 要生成 embedding 的文本列表

        Returns:
            embedding 向量列表
        """
        url = f"{self.settings.DASHSCOPE_BASE_URL}/embeddings"

        headers = {
            "Authorization": f"Bearer {self.settings.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.settings.EMBEDDING_MODEL,
            "input": texts,
        }

        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()

            # DashScope 兼容模式返回 OpenAI 格式: {"data": [{"embedding": [...]}]}
            # 原生格式: {"outputs": {"embeddings": [{"embedding": [...]}]}}
            if "data" in result:
                # OpenAI 兼容模式
                embeddings = result.get("data", [])
                return [item["embedding"] for item in embeddings]
            else:
                # DashScope 原生格式
                embeddings = result.get("outputs", {}).get("embeddings", [])
                return [item["embedding"] for item in embeddings]

        except httpx.HTTPStatusError as e:
            logger.error(f"DashScope API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to call DashScope API: {e}")
            raise

    async def _call_openai(
        self, client: httpx.AsyncClient, texts: List[str]
    ) -> List[List[float]]:
        """调用 OpenAI Embedding API

        Args:
            client: HTTP 客户端
            texts: 要生成 embedding 的文本列表

        Returns:
            embedding 向量列表
        """
        url = "https://api.openai.com/v1/embeddings"

        headers = {
            "Authorization": f"Bearer {self.settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.settings.EMBEDDING_MODEL,
            "input": texts,
        }

        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()

            # OpenAI 响应格式: {"data": [{"embedding": [...]}]}
            embeddings = result.get("data", [])
            return [item["embedding"] for item in embeddings]

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to call OpenAI API: {e}")
            raise

    async def close(self):
        """关闭客户端连接"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.debug("EmbeddingService client closed")

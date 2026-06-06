"""RAG agent for technical document Q&A with full RAG capabilities."""

from typing import Any, Dict, Optional
import asyncpg

from i3d_agent.agents.base import AgentConfig, BaseAgent
from i3d_agent.rag.controller import AgenticRAGController
from i3d_agent.rag.retrieval import RetrievalEngine
from i3d_agent.rag.source_format import chunk_to_source
from i3d_agent.llm import get_llm_client, Message
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class RAGAgent(BaseAgent):
    """RAG agent for technical document Q&A with full retrieval capabilities.

    This agent wraps AgenticRAGController for advanced retrieval capabilities
    and handles answer generation using LLM.
    """

    def __init__(self, config: Optional[AgentConfig] = None, pool: Optional[asyncpg.Pool] = None):
        if config is None:
            config = AgentConfig(
                name="rag",
                role="technical_assistant",
                instructions=(
                    "Provide technical assistance by retrieving and synthesizing "
                    "information from the knowledge base. Answer questions about "
                    "API documentation, deployment guides, and troubleshooting."
                ),
            )

        tools = [
            {"name": "retrieve_documents", "description": "Retrieve technical documents"},
            {"name": "search_api_reference", "description": "Search API documentation"},
            {"name": "get_deployment_guide", "description": "Get deployment guides"},
            {"name": "find_troubleshooting_steps", "description": "Find troubleshooting steps"},
        ]

        super().__init__(config=config, tools=tools)

        # Initialize AgenticRAGController with retrieval engine
        retrieval_engine = RetrievalEngine(pool=pool)
        self.controller = AgenticRAGController(retrieval_engine=retrieval_engine)

    async def answer(
        self,
        question: str,
        tenant_id: Optional[str] = None,
        top_k: int = 5,
        enable_multi_step: bool = False,
    ) -> Dict[str, Any]:
        """
        回答技术问题

        Args:
            question: 问题
            tenant_id: 租户 ID
            top_k: 检索文档数
            enable_multi_step: 是否启用多步推理（质量评估+查询重写）

        Returns:
            答案响应
        """
        if not question or not question.strip():
            return {
                "question": question,
                "answer": "",
                "sources": [],
                "status": "error",
                "error": "Question cannot be empty"
            }

        try:
            # Use AgenticRAGController for retrieval
            if enable_multi_step:
                result = await self.controller.retrieve_with_multi_step(
                    query=question,
                    tenant_id=tenant_id or "default",
                    top_k=top_k,
                    enable_expansion=True,
                    enable_hyde=True,
                    enable_rerank=True
                )
            else:
                result = await self.controller.retrieve(
                    query=question,
                    tenant_id=tenant_id or "default",
                    top_k=top_k,
                    enable_expansion=True,
                    enable_hyde=True,
                    enable_rerank=True
                )

            results = result.results

            if not results:
                return {
                    "question": question,
                    "answer": "抱歉，知识库中没有找到相关文档。",
                    "sources": [],
                    "status": "no_results"
                }

            # Build context from retrieved results
            context = self._build_context(results)

            # Generate answer using LLM
            answer = await self._generate_answer(question, context)

            # Extract sources
            sources = [chunk_to_source(r) for r in results[:3]]

            return {
                "question": question,
                "answer": answer,
                "sources": sources,
                "status": "success",
                "metadata": {
                    "num_retrieved": len(results),
                    "iterations": result.iterations,
                    "tenant_id": tenant_id,
                    "query_expansions": result.query_expansions,
                    "hypothetical_doc": result.hypothetical_doc
                }
            }

        except Exception as e:
            logger.error(f"RAG answer failed: {e}")
            return {
                "question": question,
                "answer": "",
                "sources": [],
                "status": "error",
                "error": str(e)
            }

    def _build_context(self, results: list) -> str:
        """Build LLM context from retrieval results"""
        context_parts = []
        for i, result in enumerate(results, 1):
            title = result.metadata.get("title", "Unknown Document")
            content = result.content
            score = result.final_score or 0
            context_parts.append(f"[文档 {i}] {title} (相关度: {score:.2f})\n{content}")

        return "\n\n".join(context_parts)

    async def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using LLM"""
        system_prompt = """你是一个技术文档助手，专门回答关于 3D CAD 系统、搜索服务、部署和故障排查的问题。

请根据提供的文档上下文回答用户问题。如果文档中没有相关信息，请诚实地说明。

回答要求：
1. 准确、简洁、专业
2. 引用相关的文档来源
3. 如果需要步骤，请按顺序列出
4. 使用中文回答"""

        user_prompt = f"""问题: {question}

相关文档:
{context}

请根据上述文档回答问题。"""

        llm_client = get_llm_client()
        answer = await llm_client.generate(
            messages=[Message(role="user", content=user_prompt)],
            system_prompt=system_prompt,
            temperature=0.7
        )

        return answer

    async def close(self):
        """Close connections"""
        # Close controller's rerank service
        if hasattr(self.controller, 'rerank_service'):
            await self.controller.rerank_service.close()
        # Close embedding service
        if hasattr(self.controller, 'embedding_service'):
            await self.controller.embedding_service.close()


__all__ = ["RAGAgent"]

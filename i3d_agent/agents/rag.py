"""RAG agent for technical document Q&A."""

from typing import Any, Dict, List, Optional

from i3d_agent.agents.base import AgentConfig, BaseAgent
from i3d_agent.tools.rag_tools import (
    retrieve_documents,
    search_api_reference,
    get_deployment_guide,
    find_troubleshooting_steps,
)
from i3d_agent.llm import get_llm_client, Message


class RAGAgent(BaseAgent):
    """RAG agent for technical document Q&A.

    This agent provides capabilities for:
    - Retrieving technical documents from the knowledge base
    - Searching API reference documentation
    - Getting deployment guides
    - Finding troubleshooting steps

    The agent uses retrieval-augmented generation (RAG) to provide
    accurate, context-aware answers based on the technical documentation.
    """

    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the RAG agent.

        Args:
            config: Optional agent configuration. Uses default if not provided.
        """
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

        # Initialize tools
        tools = [
            {
                "name": "retrieve_documents",
                "description": "Retrieve technical documents from the RAG knowledge base",
            },
            {
                "name": "search_api_reference",
                "description": "Search API documentation for specific endpoints and methods",
            },
            {
                "name": "get_deployment_guide",
                "description": "Get deployment guide for a specific system component",
            },
            {
                "name": "find_troubleshooting_steps",
                "description": "Find troubleshooting steps for specific errors and components",
            },
        ]

        super().__init__(config=config, tools=tools)

    async def answer(
        self,
        question: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Answer a technical question using RAG.

        This method retrieves relevant documents and synthesizes an answer.
        Currently returns a stub response pending full LLM integration.

        Args:
            question: The technical question to answer
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            Dictionary with keys:
                - question: The original question
                - answer: The generated answer (stub for now)
                - sources: List of source documents used
                - status: "success", "no_results", or "error"
                - error: Error message if status is "error"

        Raises:
            ValueError: If question is empty
        """
        if not question or not question.strip():
            return {
                "question": question,
                "answer": "",
                "sources": [],
                "status": "error",
                "error": "Question cannot be empty",
            }

        try:
            # Retrieve relevant documents
            docs = retrieve_documents(
                query=question,
                knowledge_base="default",
                top_k=5,
                tenant_id=tenant_id,
            )

            if not docs:
                return {
                    "question": question,
                    "answer": "抱歉，知识库中没有找到相关文档。",
                    "sources": [],
                    "status": "no_results",
                }

            # Build context from retrieved documents
            context_parts = []
            for i, doc in enumerate(docs, 1):
                title = doc.get("title", "未知文档")
                content = doc.get("content", doc.get("text", ""))
                score = doc.get("score", 0)
                context_parts.append(f"[文档 {i}] {title} (相关度: {score:.2f})\n{content}")

            context = "\n\n".join(context_parts)

            # Generate answer using LLM
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
                temperature=0.7,
            )

            return {
                "question": question,
                "answer": answer,
                "sources": [
                    {
                        "doc_id": doc.get("doc_id"),
                        "title": doc.get("title"),
                        "score": doc.get("score"),
                    }
                    for doc in docs
                ],
                "status": "success",
                "metadata": {
                    "num_docs_retrieved": len(docs),
                    "tenant_id": tenant_id,
                },
            }

        except Exception as e:
            return {
                "question": question,
                "answer": "",
                "sources": [],
                "status": "error",
                "error": str(e),
            }

    def get_api_info(
        self,
        endpoint: str,
        method: str = "GET",
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get API reference information for an endpoint.

        Args:
            endpoint: The API endpoint path (e.g., "/api/v1/search/3d")
            method: HTTP method (GET, POST, PUT, DELETE). Defaults to "GET"
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            API reference information dictionary
        """
        try:
            return {
                "status": "success",
                "data": search_api_reference(
                    endpoint=endpoint,
                    method=method,
                    tenant_id=tenant_id,
                ),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "endpoint": endpoint,
                "method": method,
            }

    def get_deployment_info(
        self,
        component: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get deployment guide for a component.

        Args:
            component: The component name (e.g., "infer-engineer", "rag-service")
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            Deployment guide dictionary
        """
        try:
            return {
                "status": "success",
                "data": get_deployment_guide(
                    component=component,
                    tenant_id=tenant_id,
                ),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "component": component,
            }

    def get_troubleshooting_info(
        self,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        component: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get troubleshooting information for an error.

        Args:
            error_code: Optional error code (e.g., "ERR-5001", "E001")
            error_message: Optional error message or pattern to search for
            component: Optional component name to narrow search scope
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            Troubleshooting information dictionary
        """
        try:
            return {
                "status": "success",
                "data": find_troubleshooting_steps(
                    error_code=error_code,
                    error_message=error_message,
                    component=component,
                    tenant_id=tenant_id,
                ),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_code": error_code,
                "component": component,
            }


__all__ = ["RAGAgent"]

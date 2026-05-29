"""RAG agent for technical document Q&A."""

from typing import Any, Dict, List, Optional

from i3d_agent.agents.base import AgentConfig, BaseAgent
from i3d_agent.tools.rag_tools import (
    retrieve_documents,
    search_api_reference,
    get_deployment_guide,
    find_troubleshooting_steps,
)


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

    def answer(
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
                    "answer": "No relevant documents found in the knowledge base.",
                    "sources": [],
                    "status": "no_results",
                }

            # Stub implementation - pending full LLM integration
            # In the full implementation, this would:
            # 1. Use the retrieved documents as context
            # 2. Call an LLM to generate a comprehensive answer
            # 3. Return the answer with citations

            return {
                "question": question,
                "answer": (
                    f"This is a stub response for question: {question}. "
                    "The full RAG implementation will use LLM to generate "
                    "comprehensive answers based on retrieved documents."
                ),
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

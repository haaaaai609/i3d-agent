"""
RAG (Retrieval-Augmented Generation) tools for i3d-agent-system.

This module provides LangChain-compatible tools for interacting with
the RAG knowledge base, including document retrieval, API reference search,
deployment guides, and troubleshooting steps.

These tools now integrate with the full RAG module.
"""

from typing import Any, Dict, List, Optional
import asyncio
import asyncpg

from langchain_core.tools import tool
from i3d_agent.config.settings import get_settings


# ========== 全局数据库池 ==========

_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """获取或创建数据库连接池"""
    global _db_pool
    if _db_pool is None:
        settings = get_settings()
        _db_pool = await asyncpg.create_pool(
            settings.get_database_url(async_driver=True),
            min_size=2,
            max_size=10
        )
    return _db_pool


@tool
def retrieve_documents(
    query: str,
    knowledge_base: str = "default",
    top_k: int = 10,
    tenant_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve technical documents from the RAG knowledge base.

    Performs semantic search on the document knowledge base to find relevant
    technical documentation, guides, and reference materials.

    Now uses the full Agentic RAG capabilities including query expansion,
    HyDE, and reranking.

    Args:
        query: The search query for retrieving relevant documents
        knowledge_base: Name of the knowledge base to search (default: "default")
        top_k: Maximum number of documents to return (default: 10, max: 100)
        tenant_id: Optional tenant ID for multi-tenancy support

    Returns:
        List[Dict[str, Any]]: List of retrieved documents with keys:
            - doc_id: Unique document identifier
            - title: Document title
            - content: Relevant content snippet
            - score: Relevance score (0-1)
            - metadata: Additional document information (source, author, etc.)

    Raises:
        ValueError: If query is empty or top_k is invalid

    Example:
        >>> docs = retrieve_documents("How to configure 3D search API?")
        >>> print(f"Found {len(docs)} relevant documents")

    Note:
        Uses the AgenticRAGController for advanced retrieval capabilities.
    """
    if not query or not query.strip():
        raise ValueError("query cannot be empty")

    if top_k < 1 or top_k > 100:
        raise ValueError("top_k must be between 1 and 100")

    async def _retrieve():
        from i3d_agent.rag.controller import AgenticRAGController
        from i3d_agent.rag.retrieval import RetrievalEngine
        from i3d_agent.rag.embedding import EmbeddingService

        pool = await get_db_pool()
        controller = AgenticRAGController(retrieval_engine=RetrievalEngine(pool=pool))

        # Generate query vector
        embedding_service = EmbeddingService()
        query_vector = await embedding_service.embed_text(query)

        # Perform retrieval with all features enabled
        result = await controller.retrieve(
            query=query,
            tenant_id=tenant_id or knowledge_base,
            top_k=top_k,
            enable_expansion=True,
            enable_hyde=True,
            enable_rerank=True
        )

        await controller.close()
        await embedding_service.close()

        return [
            {
                "doc_id": r.doc_id,
                "title": r.metadata.get("title", "Unknown"),
                "content": r.content,
                "score": r.final_score,
                "metadata": r.metadata
            }
            for r in result.results
        ]

    return asyncio.run(_retrieve())


@tool
def search_api_reference(
    endpoint: str,
    method: str = "GET",
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search API documentation for specific endpoints and methods.

    Retrieves API reference documentation including request/response schemas,
    authentication requirements, rate limits, and code examples.

    Args:
        endpoint: The API endpoint path (e.g., "/api/v1/search/3d")
        method: HTTP method (GET, POST, PUT, DELETE). Defaults to "GET"
        tenant_id: Optional tenant ID for multi-tenancy support

    Returns:
        Dict[str, Any]: API reference documentation with keys:
            - endpoint: API endpoint path
            - method: HTTP method
            - description: Endpoint description
            - parameters: Request parameters (query, path, body)
            - responses: Expected response schemas
            - examples: Code examples in multiple languages
            - rate_limit: Rate limiting information
            - authentication: Auth requirements

    Raises:
        ValueError: If endpoint is empty or method is invalid
        NotImplementedError: Until RAG service is implemented

    Example:
        >>> ref = search_api_reference("/api/v1/search/3d", method="POST")
        >>> print(ref["description"])

    Note:
        This is a stub implementation. The actual RAG integration will search
        through OpenAPI/Swagger specs and API documentation.
    """
    if not endpoint or not endpoint.strip():
        raise ValueError("endpoint cannot be empty")

    valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
    if method.upper() not in valid_methods:
        raise ValueError(f"method must be one of {valid_methods}")

    # Stub implementation - RAG service integration pending
    return {
        "endpoint": endpoint,
        "method": method.upper(),
        "description": "API reference for this endpoint is not yet available.",
        "parameters": {},
        "responses": {},
        "examples": [],
        "rate_limit": "TBD",
        "authentication": "TBD",
        "metadata": {
            "source": "stub",
            "tenant_id": tenant_id,
        },
    }


@tool
def get_deployment_guide(
    component: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get deployment guide for a specific system component.

    Retrieves comprehensive deployment documentation including prerequisites,
    installation steps, configuration options, and verification procedures.

    Args:
        component: The component name (e.g., "infer-engineer", "rag-service")
        tenant_id: Optional tenant ID for multi-tenancy support

    Returns:
        Dict[str, Any]: Deployment guide with keys:
            - component: Component name
            - overview: Brief component description
            - prerequisites: System requirements and dependencies
            - installation: Step-by-step installation instructions
            - configuration: Configuration options and environment variables
            - verification: Steps to verify successful deployment
            - troubleshooting: Common issues and solutions

    Raises:
        ValueError: If component is empty
        NotImplementedError: Until RAG service is implemented

    Example:
        >>> guide = get_deployment_guide("infer-engineer")
        >>> for step in guide["installation"]:
        ...     print(step)

    Note:
        This is a stub implementation. The actual RAG integration will retrieve
        structured deployment documentation from the knowledge base.
    """
    if not component or not component.strip():
        raise ValueError("component cannot be empty")

    # Stub implementation - RAG service integration pending
    return {
        "component": component,
        "overview": f"Deployment guide for {component} is not yet available.",
        "prerequisites": [
            "RAG service integration pending",
            "Prerequisites will be documented here",
        ],
        "installation": [
            "Step 1: Placeholder - RAG service not implemented",
            "Step 2: Installation steps will be provided",
        ],
        "configuration": {
            "environment_variables": {},
            "config_files": [],
        },
        "verification": [
            "Placeholder verification steps",
        ],
        "troubleshooting": {
            "common_issues": [],
            "solutions": [],
        },
        "metadata": {
            "source": "stub",
            "tenant_id": tenant_id,
        },
    }


@tool
def find_troubleshooting_steps(
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    component: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Find troubleshooting steps for specific errors and components.

    Searches the knowledge base for diagnostic procedures and solutions
    for known errors, organized by error codes, messages, and components.

    Args:
        error_code: Optional error code (e.g., "ERR-5001", "E001")
        error_message: Optional error message or pattern to search for
        component: Optional component name to narrow search scope
        tenant_id: Optional tenant ID for multi-tenancy support

    Returns:
        List[Dict[str, Any]]: Troubleshooting steps with keys:
            - error_code: Associated error code
            - error_pattern: Error message pattern
            - component: Affected component
            - diagnosis: Diagnostic steps
            - solutions: List of potential solutions
            - related_docs: Links to related documentation
            - severity: Error severity (critical/warning/info)

    Raises:
        ValueError: If all search parameters are empty
        NotImplementedError: Until RAG service is implemented

    Example:
        >>> steps = find_troubleshooting_steps(
        ...     error_code="ERR-5001",
        ...     component="infer-engineer"
        ... )
        >>> for step in steps:
        ...     print(f"{step['error_code']}: {step['diagnosis']}")

    Note:
        This is a stub implementation. The actual RAG integration will
        perform semantic search on error logs and troubleshooting docs.
    """
    if not any([error_code, error_message, component]):
        raise ValueError(
            "At least one of error_code, error_message, or component must be provided"
        )

    # Stub implementation - RAG service integration pending
    return [
        {
            "error_code": error_code or "UNKNOWN",
            "error_pattern": error_message or "No pattern provided",
            "component": component or "Unknown",
            "diagnosis": "RAG service not yet implemented - troubleshooting pending",
            "solutions": [
                "Solution 1: Placeholder - RAG integration required",
                "Solution 2: Check system logs when service is available",
            ],
            "related_docs": [],
            "severity": "info",
            "metadata": {
                "source": "stub",
                "tenant_id": tenant_id,
            },
        }
    ]


__all__ = [
    "retrieve_documents",
    "search_api_reference",
    "get_deployment_guide",
    "find_troubleshooting_steps",
]

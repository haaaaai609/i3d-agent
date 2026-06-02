"""RAG (Retrieval-Augmented Generation) module for i3d-agent-system.

This module provides:
- Document management with version control
- Incremental indexing with async workers
- Hybrid retrieval (vector + BM25)
- Agentic RAG capabilities (query expansion, HyDE, reranking, multi-step reasoning)
- Monitoring and quality feedback
"""

__version__ = "0.1.0"

from i3d_agent.rag.models import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    Chunk,
    SearchRequest,
    AskRequest,
    FeedbackRequest,
    RetrievalResult,
)

__all__ = [
    "__version__",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "Chunk",
    "SearchRequest",
    "AskRequest",
    "FeedbackRequest",
    "RetrievalResult",
]
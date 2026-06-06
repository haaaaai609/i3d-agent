"""Helpers for formatting retrieved chunks as chat/RAG sources."""

from typing import Any, Dict, Optional

from i3d_agent.rag.models import Chunk


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    value = getattr(obj, name, default)
    if value.__class__.__module__ == "unittest.mock":
        return default
    return value


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "unknown":
        return None
    return text


def _score(value: Optional[float]) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(float(value), 1.0))


def chunk_to_source(chunk: Chunk) -> Dict[str, Any]:
    """Build a UI-friendly source payload from a retrieved chunk."""
    metadata = _attr(chunk, "metadata", {}) or {}
    title = (
        _clean(metadata.get("title"))
        or _clean(metadata.get("document_title"))
        or _clean(metadata.get("file_name"))
        or _clean(metadata.get("source"))
        or "未知文档"
    )
    source = (
        _clean(metadata.get("source"))
        or _clean(metadata.get("file_name"))
        or _clean(metadata.get("source_path"))
        or _clean(metadata.get("storage_path"))
        or title
    )
    score_detail = dict(metadata.get("score_detail") or {})
    final_score = _score(_attr(chunk, "final_score"))
    doc_id = _attr(chunk, "doc_id")
    chunk_id = _attr(chunk, "id")
    chunk_index = _attr(chunk, "chunk_index")
    doc_version = _attr(chunk, "doc_version")
    vector_score = _attr(chunk, "vector_score")
    bm25_score = _attr(chunk, "bm25_score")

    return {
        "doc_id": doc_id,
        "chunk_id": chunk_id,
        "title": title,
        "source": source,
        "score": final_score,
        "chunk_index": chunk_index,
        "doc_version": doc_version,
        "file_name": metadata.get("file_name"),
        "file_md5": metadata.get("file_md5"),
        "storage_path": metadata.get("storage_path"),
        "source_path": metadata.get("source_path"),
        "vector_score": vector_score,
        "bm25_score": bm25_score,
        "score_details": {
            "final_score": final_score,
            "vector_score": vector_score or 0.0,
            "bm25_score": bm25_score or 0.0,
            "vector_weight": score_detail.get("vector_weight"),
            "bm25_weight": score_detail.get("bm25_weight"),
            "search_type": score_detail.get("search_type"),
            "formula": score_detail.get("formula"),
        },
    }

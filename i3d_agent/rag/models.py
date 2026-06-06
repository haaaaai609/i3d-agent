"""RAG data models for document management and retrieval."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid


class DocumentCreate(BaseModel):
    """文档创建请求"""
    tenant_id: str = Field(..., description="租户 ID")
    title: str = Field(..., min_length=1, max_length=500, description="文档标题")
    content: str = Field(..., min_length=1, description="文档内容")
    doc_type: str = Field(..., description="文档类型: technical, business, api")
    source_type: Optional[str] = Field(None, description="来源类型: md, pdf, html, json")
    description: Optional[str] = Field(None, description="文档描述")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")
    language: Optional[str] = Field("zh", description="语言")

    @field_validator('doc_type')
    @classmethod
    def validate_doc_type(cls, v):
        valid_types = {'technical', 'business', 'api'}
        if v not in valid_types:
            raise ValueError(f'doc_type must be one of {valid_types}')
        return v


class DocumentUpdate(BaseModel):
    """文档更新请求"""
    content: Optional[str] = Field(None, min_length=1, description="新内容")
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="新标题")
    description: Optional[str] = Field(None, description="新描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="新元数据")
    tags: Optional[List[str]] = Field(None, description="新标签")


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    tenant_id: str
    title: str
    description: Optional[str]
    doc_type: str
    source_type: Optional[str]
    version: int
    is_latest: bool
    status: str
    metadata: Dict[str, Any]
    tags: List[str]
    language: str
    file_md5: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    storage_path: Optional[str] = None
    source_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BatchImportRequest(BaseModel):
    """Request for importing documents from a mounted host directory."""

    host_dir: str = Field(..., min_length=1, description="Container path under an allowed import root")
    tenant_id: str = Field(..., description="Tenant ID")
    doc_type: str = Field(..., description="Document type: technical, business, api")
    source_type: Optional[str] = Field(None, description="Source type override")
    recursive: bool = Field(True, description="Scan subdirectories")
    include_patterns: Optional[List[str]] = Field(None, description="Glob include patterns")
    exclude_patterns: Optional[List[str]] = Field(None, description="Glob exclude patterns")
    dry_run: bool = Field(False, description="Only scan and report, without writing")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Shared metadata")
    tags: Optional[List[str]] = Field(default_factory=list, description="Shared tags")
    language: Optional[str] = Field("zh", description="Language")

    @field_validator('doc_type')
    @classmethod
    def validate_doc_type(cls, v):
        valid_types = {'technical', 'business', 'api'}
        if v not in valid_types:
            raise ValueError(f'doc_type must be one of {valid_types}')
        return v


class ImportItemResult(BaseModel):
    """Result for one scanned or imported file."""

    file_name: str
    file_md5: Optional[str] = None
    source_path: Optional[str] = None
    storage_path: Optional[str] = None
    status: str
    reason: Optional[str] = None
    doc_id: Optional[str] = None


class BatchImportResponse(BaseModel):
    """Batch import summary."""

    scanned: int
    imported: int
    skipped: int
    failed: int
    dry_run: bool
    results: List[ImportItemResult]


class Chunk(BaseModel):
    """文档分块"""
    id: str
    doc_id: str
    tenant_id: str
    content: str
    embedding: List[float]
    chunk_index: int
    token_count: Optional[int]
    metadata: Dict[str, Any]
    doc_version: int
    vector_score: Optional[float] = None
    bm25_score: Optional[float] = None
    final_score: Optional[float] = None


class SearchRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., min_length=1, description="检索查询")
    tenant_id: str = Field(..., description="租户 ID")
    top_k: int = Field(10, ge=1, le=100, description="返回结果数")
    enable_expansion: bool = Field(True, description="启用查询扩展")
    enable_hyde: bool = Field(True, description="启用 HyDE")
    enable_rerank: bool = Field(True, description="启用重排序")
    search_type: str = Field("balanced", description="检索类型: semantic, keyword, balanced, exact_match")


class AskRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, description="问题")
    tenant_id: str = Field(..., description="租户 ID")
    session_id: Optional[str] = Field(None, description="会话 ID")
    top_k: int = Field(5, ge=1, le=50, description="检索文档数")
    enable_multi_step: bool = Field(True, description="启用多步推理")


class FeedbackRequest(BaseModel):
    """质量反馈请求"""
    session_id: str
    query: str
    retrieved_doc_ids: Optional[List[str]] = None
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分 1-5")
    is_helpful: Optional[bool] = None
    thumb_up: Optional[bool] = None
    feedback_text: Optional[str] = None


class RetrievalResult(BaseModel):
    """检索结果"""
    results: List[Chunk]
    query: str
    iterations: int = 1
    query_expansions: List[str] = []
    hypothetical_doc: Optional[str] = None

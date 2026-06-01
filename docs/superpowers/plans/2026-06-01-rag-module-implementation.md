# RAG Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的 RAG 模块，支持混合文档类型、增量索引、Agentic RAG（查询扩展、HyDE、重排序、多步推理）、混合检索（向量+BM25）、版本管理和监控仪表板。

**Architecture:** RAG 模块作为独立子系统集成到现有的 LangGraph 工作流中，使用 PostgreSQL + pgvector 进行向量存储和全文检索，通过 Agentic RAG Controller 协调查询扩展、HyDE、重排序等多步推理流程，Document Manager 负责文档 CRUD 和版本管理，异步 Worker 处理增量索引。

**Tech Stack:** PostgreSQL + pgvector、Redis、DashScope LLM、Cohere Rerank、FastAPI、LangGraph、OpenTelemetry

---

## Phase 1: 基础设施

### Task 1.1: 创建 RAG 数据模型

**Files:**
- Create: `i3d_agent/rag/models.py`
- Test: `i3d_agent/tests/test_rag/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_models.py
import pytest
from i3d_agent.rag.models import (
    DocumentCreate, DocumentUpdate, DocumentResponse,
    Chunk, SearchRequest, AskRequest, FeedbackRequest
)

def test_document_create_validation():
    """测试文档创建请求验证"""
    request = DocumentCreate(
        tenant_id="default",
        title="Test Document",
        content="This is a test document content.",
        doc_type="technical",
        source_type="md"
    )
    assert request.tenant_id == "default"
    assert request.title == "Test Document"
    assert request.doc_type == "technical"

def test_document_create_missing_required_fields():
    """测试缺少必填字段"""
    with pytest.raises(ValueError):
        DocumentCreate(
            tenant_id="default",
            title="",  # Empty title should fail
            content="Content",
            doc_type="technical"
        )

def test_chunk_model():
    """测试 Chunk 模型"""
    chunk = Chunk(
        id="uuid-1",
        doc_id="uuid-doc-1",
        tenant_id="default",
        content="Chunk content",
        embedding=[0.1] * 1536,
        metadata={"title": "Test", "chunk_index": 0}
    )
    assert chunk.doc_id == "uuid-doc-1"
    assert len(chunk.embedding) == 1536

def test_search_request():
    """测试搜索请求模型"""
    request = SearchRequest(
        query="如何配置 API？",
        tenant_id="default",
        top_k=10,
        enable_expansion=True,
        enable_hyde=True,
        enable_rerank=True
    )
    assert request.enable_expansion is True
    assert request.top_k == 10

def test_ask_request():
    """测试问答请求模型"""
    request = AskRequest(
        question="如何部署系统？",
        tenant_id="default",
        top_k=5,
        enable_multi_step=True
    )
    assert request.enable_multi_step is True

def test_feedback_request():
    """测试反馈请求模型"""
    request = FeedbackRequest(
        session_id="session-1",
        query="测试查询",
        rating=5,
        is_helpful=True,
        feedback_text="非常有帮助"
    )
    assert request.rating == 5
    assert request.is_helpful is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /data/yzh/i3d-agent-system
pytest tests/test_rag/test_models.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.models'"

- [ ] **Step 3: Create the module with minimal implementation**

```python
# i3d_agent/rag/models.py
"""RAG data models for document management and retrieval."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
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

    @validator('doc_type')
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
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_models.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/models.py tests/test_rag/test_models.py
git commit -m "feat(rag): add RAG data models with tests"
```

---

### Task 1.2: 创建数据库迁移文件

**Files:**
- Create: `i3d_agent/migrations/versions/002_add_rag_tables.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- i3d_agent/migrations/versions/002_add_rag_tables.sql
-- RAG Module Tables
-- This migration creates all tables needed for the RAG module

-- ============================================
-- rag_documents: 文档元数据表
-- ============================================
CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,

    -- 基本信息
    title VARCHAR(500) NOT NULL,
    description TEXT,
    doc_type VARCHAR(50) NOT NULL,
    source_type VARCHAR(50),

    -- 内容
    raw_content TEXT,
    content_hash VARCHAR(64),

    -- 版本控制
    version INT NOT NULL DEFAULT 1,
    is_latest BOOLEAN DEFAULT true,
    parent_doc_id UUID,

    -- 状态
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,

    -- 元数据
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    language VARCHAR(10) DEFAULT 'zh',

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,

    -- 外键约束
    CONSTRAINT fk_rag_doc_parent FOREIGN KEY (parent_doc_id)
        REFERENCES rag_documents(id) ON DELETE SET NULL,

    -- 检查约束
    CONSTRAINT chk_rag_doc_type CHECK (doc_type IN ('technical', 'business', 'api')),
    CONSTRAINT chk_rag_doc_status CHECK (status IN ('pending', 'indexing', 'ready', 'failed')),
    CONSTRAINT chk_rag_doc_version CHECK (version > 0)
);

-- 文档表索引
CREATE INDEX idx_rag_docs_tenant_latest ON rag_documents(tenant_id, is_latest) WHERE deleted_at IS NULL;
CREATE INDEX idx_rag_docs_type ON rag_documents(doc_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_rag_docs_tags ON rag_documents USING GIN(tags);
CREATE INDEX idx_rag_docs_hash ON rag_documents(content_hash);
CREATE INDEX idx_rag_docs_parent ON rag_documents(parent_doc_id) WHERE parent_doc_id IS NOT NULL;

-- ============================================
-- rag_chunks: 文档分块表
-- ============================================
CREATE TABLE IF NOT EXISTS rag_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL,
    tenant_id VARCHAR(100) NOT NULL,

    -- 内容
    content TEXT NOT NULL,
    embedding vector(1536),

    -- 全文检索
    content_tsv tsvector GENERATED ALWAYS AS
        (to_tsvector('simple', coalesce(content, ''))) STORED,

    -- 元数据
    chunk_index INT NOT NULL,
    token_count INT,
    metadata JSONB DEFAULT '{}',

    -- 版本关联
    doc_version INT NOT NULL,

    -- 状态
    deleted_at TIMESTAMP,

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),

    -- 外键约束
    CONSTRAINT fk_rag_chunk_doc FOREIGN KEY (doc_id)
        REFERENCES rag_documents(id) ON DELETE CASCADE,

    -- 唯一约束
    CONSTRAINT uq_rag_chunk_version UNIQUE(doc_id, chunk_index, doc_version),

    -- 检查约束
    CONSTRAINT chk_rag_chunk_index CHECK (chunk_index >= 0),
    CONSTRAINT chk_rag_chunk_tokens CHECK (token_count IS NULL OR token_count > 0)
);

-- 向量索引 (HNSW)
CREATE INDEX idx_rag_chunks_embedding
ON rag_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 全文索引
CREATE INDEX idx_rag_chunks_tsv
ON rag_chunks USING gin (content_tsv);

-- 租户索引
CREATE INDEX idx_rag_chunks_tenant
ON rag_chunks(tenant_id) WHERE deleted_at IS NULL;

-- 文档关联索引
CREATE INDEX idx_rag_chunks_doc
ON rag_chunks(doc_id, doc_version) WHERE deleted_at IS NULL;

-- ============================================
-- rag_versions: 版本历史表
-- ============================================
CREATE TABLE IF NOT EXISTS rag_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL,
    tenant_id VARCHAR(100) NOT NULL,

    -- 版本信息
    version INT NOT NULL,

    -- 快照
    content_snapshot TEXT,
    chunk_count INT,

    -- 变更说明
    change_type VARCHAR(20),
    change_reason TEXT,
    changed_by VARCHAR(100),

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),

    -- 外键约束
    CONSTRAINT fk_rag_version_doc FOREIGN KEY (doc_id)
        REFERENCES rag_documents(id) ON DELETE CASCADE,

    -- 检查约束
    CONSTRAINT chk_rag_version_type CHECK (change_type IN ('create', 'update', 'delete', 'restore'))
);

-- 版本索引
CREATE INDEX idx_rag_versions_doc ON rag_versions(doc_id, version);
CREATE INDEX idx_rag_versions_tenant ON rag_versions(tenant_id);

-- ============================================
-- rag_index_queue: 索引队列表
-- ============================================
CREATE TABLE IF NOT EXISTS rag_index_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL,
    tenant_id VARCHAR(100) NOT NULL,

    -- 任务信息
    status VARCHAR(20) DEFAULT 'pending',
    operation VARCHAR(20) NOT NULL,
    priority INT DEFAULT 5,

    -- 重试
    retry_count INT DEFAULT 0,
    error_message TEXT,

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- 外键约束
    CONSTRAINT fk_rag_queue_doc FOREIGN KEY (doc_id)
        REFERENCES rag_documents(id) ON DELETE CASCADE,

    -- 检查约束
    CONSTRAINT chk_rag_queue_status CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    CONSTRAINT chk_rag_queue_operation CHECK (operation IN ('create', 'update', 'delete')),
    CONSTRAINT chk_rag_queue_priority CHECK (priority BETWEEN 0 AND 9),
    CONSTRAINT chk_rag_queue_retry CHECK (retry_count >= 0)
);

-- 队列索引
CREATE INDEX idx_rag_queue_status ON rag_index_queue(status, priority, created_at)
    WHERE status IN ('pending', 'processing');
CREATE INDEX idx_rag_queue_doc ON rag_index_queue(doc_id);
CREATE INDEX idx_rag_queue_tenant ON rag_index_queue(tenant_id);

-- ============================================
-- rag_metrics: 监控指标表
-- ============================================
CREATE TABLE IF NOT EXISTS rag_metrics (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(100),
    metric_name VARCHAR(100) NOT NULL,
    metric_value JSONB NOT NULL,
    tags JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW()
);

-- 指标索引
CREATE INDEX idx_rag_metrics_name ON rag_metrics(metric_name, timestamp DESC);
CREATE INDEX idx_rag_metrics_tenant ON rag_metrics(tenant_id, timestamp DESC);

-- ============================================
-- rag_feedback: 质量反馈表
-- ============================================
CREATE TABLE IF NOT EXISTS rag_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,

    -- 关联信息
    session_id VARCHAR(100),
    query TEXT NOT NULL,
    retrieved_doc_ids UUID[],

    -- 反馈信息
    rating INT CHECK (rating BETWEEN 1 AND 5),
    is_helpful BOOLEAN,
    thumb_up BOOLEAN,
    feedback_text TEXT,

    -- 推理链路
    answer TEXT,
    sources JSONB,

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW()
);

-- 反馈索引
CREATE INDEX idx_rag_feedback_tenant ON rag_feedback(tenant_id, created_at DESC);
CREATE INDEX idx_rag_feedback_session ON rag_feedback(session_id, created_at);

-- ============================================
-- Row Level Security (RLS) - 租户隔离
-- ============================================

-- 启用 RLS
ALTER TABLE rag_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_index_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_feedback ENABLE ROW LEVEL SECURITY;

-- 创建 RLS 策略
CREATE POLICY rag_documents_tenant_policy ON rag_documents
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY rag_chunks_tenant_policy ON rag_chunks
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY rag_versions_tenant_policy ON rag_versions
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY rag_index_queue_tenant_policy ON rag_index_queue
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY rag_feedback_tenant_policy ON rag_feedback
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

-- ============================================
-- 自动更新 updated_at 触发器
-- ============================================

CREATE OR REPLACE FUNCTION update_rag_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_rag_documents_updated_at
    BEFORE UPDATE ON rag_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_rag_updated_at_column();

-- ============================================
-- 完成标记
-- ============================================

DO $$
BEGIN
    RAISE NOTICE 'RAG tables created successfully';
END $$;
```

- [ ] **Step 2: Commit**

```bash
git add i3d_agent/migrations/versions/002_add_rag_tables.sql
git commit -m "feat(rag): add database migration for RAG tables"
```

---

### Task 1.3: 创建 RAG 模块初始化

**Files:**
- Create: `i3d_agent/rag/__init__.py`

- [ ] **Step 1: Create the module init file**

```python
# i3d_agent/rag/__init__.py
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
```

- [ ] **Step 2: Commit**

```bash
git add i3d_agent/rag/__init__.py
git commit -m "feat(rag): add RAG module initialization"
```

---

### Task 1.4: 创建文档处理器（切分和解析）

**Files:**
- Create: `i3d_agent/rag/processor.py`
- Test: `i3d_agent/tests/test_rag/test_processor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_processor.py
import pytest
from i3d_agent.rag.processor import DocumentProcessor, ChunkSizeConfig

def test_chunk_size_config_defaults():
    """测试默认分块配置"""
    config = ChunkSizeConfig()
    assert config.default_size == 800
    assert config.default_overlap == 150
    assert config.technical_size == 1000
    assert config.business_size == 600

def test_processor_markdown_splitting():
    """测试 Markdown 文档切分"""
    processor = DocumentProcessor()

    markdown_content = """
# 第一章

这是第一章的内容，包含一些文字描述。

## 1.1 小节

这是小节的内容。

# 第二章

这是第二章的内容。
    """

    chunks = processor.split_markdown(markdown_content)

    assert len(chunks) > 0
    assert all('content' in c for c in chunks)
    assert all('metadata' in c for c in chunks)
    # 检查章节信息被保留
    assert any('第一章' in c.get('metadata', {}).get('section', '') for c in chunks)

def test_processor_code_block_preservation():
    """测试代码块保留"""
    processor = DocumentProcessor()

    content = """
# API 文档

## 示例代码

```python
def hello_world():
    print("Hello, World!")
    return True
```

这段代码实现了问候功能。
    """

    chunks = processor.split_content(content, doc_type="technical")

    # 代码块应该完整保留在单个 chunk 中
    code_chunks = [c for c in chunks if '```' in c['content']]
    assert len(code_chunks) == 1
    assert 'def hello_world' in code_chunks[0]['content']

def test_processor_api_endpoint_splitting():
    """测试 API 文档按端点切分"""
    processor = DocumentProcessor()

    api_doc = """
# API Reference

## GET /api/v1/models

获取模型列表。

## POST /api/v1/models

创建新模型。
    """

    chunks = processor.split_api_document(api_doc)

    # 每个 API 端点应该是独立的 chunk
    assert len(chunks) == 2
    assert any('/api/v1/models' in c['content'] for c in chunks)

def test_metadata_extraction():
    """测试元数据提取"""
    processor = DocumentProcessor()

    chunks = processor.split_content(
        "Test content here",
        doc_type="technical",
        doc_id="test-doc-1",
        title="Test Document"
    )

    for i, chunk in enumerate(chunks):
        assert chunk['metadata']['doc_type'] == 'technical'
        assert chunk['metadata']['doc_id'] == 'test-doc-1'
        assert chunk['metadata']['title'] == 'Test Document'
        assert chunk['metadata']['chunk_index'] == i

def test_token_count_estimation():
    """测试 token 数量估算"""
    processor = DocumentProcessor()

    text = "This is a test sentence. " * 20
    count = processor.estimate_tokens(text)

    assert count > 0
    assert count < len(text)  # token 数应该少于字符数
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_processor.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.processor'"

- [ ] **Step 3: Create the processor module**

```python
# i3d_agent/rag/processor.py
"""Document processor for parsing, chunking, and metadata extraction."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib


@dataclass
class ChunkSizeConfig:
    """分块大小配置"""
    default_size: int = 800
    default_overlap: int = 150
    technical_size: int = 1000
    technical_overlap: int = 200
    business_size: int = 600
    business_overlap: int = 100
    api_size: int = 500
    api_overlap: int = 0


class DocumentProcessor:
    """文档处理器 - 负责文档解析、切分和元数据提取"""

    def __init__(self, config: Optional[ChunkSizeConfig] = None):
        self.config = config or ChunkSizeConfig()

    def split_content(
        self,
        content: str,
        doc_type: str = "technical",
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """
        根据文档类型切分内容

        Args:
            content: 文档内容
            doc_type: 文档类型 (technical, business, api)
            doc_id: 文档 ID
            title: 文档标题
            language: 语言

        Returns:
            分块列表
        """
        if doc_type == "api":
            return self.split_api_document(content, doc_id, title, language)
        elif doc_type == "business":
            return self.split_paragraph(content, doc_id, title, language)
        else:  # technical
            return self.split_markdown(content, doc_id, title, language)

    def split_markdown(
        self,
        content: str,
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """
        切分 Markdown 文档 - 按标题层级和语义边界

        保留代码块、表格完整，在章节标题处切分
        """
        chunks = []
        current_section = "Introduction"

        # 提取代码块并标记位置
        content, code_blocks = self._extract_code_blocks(content)

        # 按标题分割
        sections = self._split_by_headings(content)

        for section_heading, section_content in sections:
            if section_heading:
                current_section = section_heading

            # 进一步切分大章节
            section_chunks = self._split_section(
                section_content,
                chunk_size=self.config.technical_size,
                overlap=self.config.technical_overlap
            )

            # 恢复代码块标记
            section_chunks = self._restore_code_blocks(section_chunks, code_blocks)

            # 创建分块
            for i, chunk_content in enumerate(section_chunks):
                chunk = {
                    "content": chunk_content.strip(),
                    "metadata": {
                        "doc_type": "technical",
                        "doc_id": doc_id,
                        "title": title or "",
                        "section": current_section,
                        "chunk_index": i,
                        "source_type": "md",
                        "language": language,
                        "token_count": self.estimate_tokens(chunk_content)
                    }
                }
                chunks.append(chunk)

        return chunks

    def split_api_document(
        self,
        content: str,
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """
        切分 API 文档 - 按端点切分

        每个 API 端点作为独立 chunk
        """
        chunks = []

        # 匹配 API 端点模式 (如: GET /api/v1/models, POST /api/v1/users)
        api_pattern = r'##?\s+(GET|POST|PUT|DELETE|PATCH)\s+([^\n]+)(.*?)(?=##?\s+(?:GET|POST|PUT|DELETE|PATCH)|\Z)'
        matches = re.finditer(api_pattern, content, re.DOTALL)

        chunk_index = 0
        for match in matches:
            method = match.group(1)
            endpoint = match.group(2).strip()
            description = match.group(3).strip()

            chunk_content = f"{method} {endpoint}\n\n{description}"

            chunk = {
                "content": chunk_content,
                "metadata": {
                    "doc_type": "api",
                    "doc_id": doc_id,
                    "title": title or "",
                    "api_method": method,
                    "api_endpoint": endpoint,
                    "chunk_index": chunk_index,
                    "source_type": "md",
                    "language": language,
                    "token_count": self.estimate_tokens(chunk_content)
                }
            }
            chunks.append(chunk)
            chunk_index += 1

        # 如果没有找到端点，按常规方式处理
        if not chunks:
            return self.split_paragraph(content, doc_id, title, language)

        return chunks

    def split_paragraph(
        self,
        content: str,
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """
        按段落切分文档

        适用于业务文档，保持段落完整性
        """
        chunks = []
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        current_chunk = ""
        chunk_index = 0
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)

            # 如果单个段落超过目标大小，独立成块
            if para_tokens > self.config.business_size:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk.strip(),
                        chunk_index,
                        "business",
                        doc_id,
                        title,
                        language,
                        current_tokens
                    ))
                    chunk_index += 1
                    current_chunk = ""
                    current_tokens = 0

                # 大段落按句子切分
                sub_chunks = self._split_by_sentences(para, self.config.business_size)
                for sub_chunk in sub_chunks:
                    chunks.append(self._create_chunk(
                        sub_chunk.strip(),
                        chunk_index,
                        "business",
                        doc_id,
                        title,
                        language
                    ))
                    chunk_index += 1
                continue

            # 检查是否需要开始新块
            if current_tokens + para_tokens > self.config.business_size and current_chunk:
                chunks.append(self._create_chunk(
                    current_chunk.strip(),
                    chunk_index,
                    "business",
                    doc_id,
                    title,
                    language,
                    current_tokens
                ))
                chunk_index += 1
                current_chunk = ""
                current_tokens = 0

            current_chunk += para + "\n\n"
            current_tokens += para_tokens

        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(self._create_chunk(
                current_chunk.strip(),
                chunk_index,
                "business",
                doc_id,
                title,
                language,
                current_tokens
            ))

        return chunks

    def _split_section(self, content: str, chunk_size: int, overlap: int) -> List[str]:
        """切分章节内容为多个块"""
        chunks = []
        sentences = re.split(r'([。！？.!?]\s+)', content)

        current_chunk = ""
        current_size = 0

        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]

            sentence_size = self.estimate_tokens(sentence)

            if current_size + sentence_size > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())

                # 添加 overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk, overlap
                )
                current_chunk = overlap_sentences
                current_size = self.estimate_tokens(current_chunk)

            current_chunk += sentence
            current_size += sentence_size

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_sentences(self, text: str, max_size: int) -> List[str]:
        """按句子切分文本"""
        sentences = re.split(r'([。！？.!?]\s+)', text)
        chunks = []
        current = ""

        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]

            if self.estimate_tokens(current + sentence) > max_size and current:
                chunks.append(current.strip())
                current = ""
            current += sentence

        if current.strip():
            chunks.append(current.strip())

        return chunks

    def _extract_code_blocks(self, content: str) -> tuple:
        """提取代码块并替换为标记"""
        pattern = r'```(\w+)?\n(.*?)```'
        code_blocks = []

        def replace_with_marker(match):
            lang = match.group(1) or ''
            code = match.group(2)
            marker = f"__CODE_BLOCK_{len(code_blocks)}__"
            code_blocks.append((marker, lang, code))
            return marker

        extracted = re.sub(pattern, replace_with_marker, content, flags=re.DOTALL)
        return extracted, code_blocks

    def _restore_code_blocks(self, chunks: List[str], code_blocks: List[tuple]) -> List[str]:
        """恢复代码块标记为实际代码"""
        restored_chunks = []
        for chunk in chunks:
            for marker, lang, code in code_blocks:
                if marker in chunk:
                    chunk = chunk.replace(marker, f"```{lang}\n{code}\n```")
            restored_chunks.append(chunk)
        return restored_chunks

    def _split_by_headings(self, content: str) -> List[tuple]:
        """按标题分割内容"""
        pattern = r'^(#{1,3}\s+.+)$'
        sections = []
        current_heading = "Introduction"
        current_content = []

        lines = content.split('\n')
        for line in lines:
            match = re.match(pattern, line)
            if match:
                # 保存上一个章节
                if current_content:
                    sections.append((current_heading, '\n'.join(current_content)))
                    current_content = []
                current_heading = match.group(1).strip()
            else:
                current_content.append(line)

        # 添加最后一个章节
        if current_content:
            sections.append((current_heading, '\n'.join(current_content)))

        return sections

    def _get_overlap_sentences(self, text: str, overlap_tokens: int) -> str:
        """获取重叠部分的句子"""
        sentences = re.split(r'([。！？.!?]\s+)', text)
        overlap = ""
        total = 0

        for i in range(len(sentences) - 1, -1, -1):
            sentence = sentences[i] if i % 2 == 0 else ""
            sentence_size = self.estimate_tokens(sentence)

            if total + sentence_size > overlap_tokens:
                break

            overlap = sentence + overlap
            total += sentence_size

        return overlap

    def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        doc_type: str,
        doc_id: Optional[str],
        title: Optional[str],
        language: str,
        token_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """创建分块"""
        return {
            "content": content,
            "metadata": {
                "doc_type": doc_type,
                "doc_id": doc_id,
                "title": title or "",
                "chunk_index": chunk_index,
                "source_type": "md",
                "language": language,
                "token_count": token_count or self.estimate_tokens(content)
            }
        }

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数量

        中文：约 1.5 字符 = 1 token
        英文：约 4 字符 = 1 token
        混合：按比例估算
        """
        if not text:
            return 0

        # 统计中文字符
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        # 统计英文字符
        english_chars = len(re.findall(r'[a-zA-Z]', text))

        chinese_tokens = chinese_chars / 1.5
        english_tokens = english_chars / 4

        return int(chinese_tokens + english_tokens)

    def calculate_content_hash(self, content: str) -> str:
        """计算内容哈希用于变更检测"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_processor.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/processor.py tests/test_rag/test_processor.py
git commit -m "feat(rag): add document processor with chunking support"
```

---

### Task 1.5: 创建 Embedding 服务

**Files:**
- Create: `i3d_agent/rag/embedding.py`
- Test: `i3d_agent/tests/test_rag/test_embedding.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_embedding.py
import pytest
from unittest.mock import Mock, patch
from i3d_agent.rag.embedding import EmbeddingService

@pytest.mark.asyncio
async def test_embedding_single_text():
    """测试单个文本 embedding"""
    service = EmbeddingService()

    with patch.object(service, '_call_embedding_api') as mock_api:
        mock_api.return_value = [[0.1] * 1536]

        result = await service.embed_text("测试文本")

        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
        mock_api.assert_called_once()

@pytest.mark.asyncio
async def test_embedding_batch():
    """测试批量 embedding"""
    service = EmbeddingService()

    texts = ["文本1", "文本2", "文本3"]

    with patch.object(service, '_call_embedding_api') as mock_api:
        mock_api.return_value = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]

        results = await service.embed_batch(texts)

        assert len(results) == 3
        assert all(len(r) == 1536 for r in results)

@pytest.mark.asyncio
async def test_embedding_chunks():
    """测试 chunk 列表 embedding"""
    service = EmbeddingService()

    chunks = [
        {"content": "内容1", "metadata": {"chunk_index": 0}},
        {"content": "内容2", "metadata": {"chunk_index": 1}}
    ]

    with patch.object(service, '_call_embedding_api') as mock_api:
        mock_api.return_value = [[0.1] * 1536, [0.2] * 1536]

        results = await service.embed_chunks(chunks)

        assert len(results) == 2
        assert results[0]["embedding"] == [0.1] * 1536
        assert results[1]["embedding"] == [0.2] * 1536
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_embedding.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.embedding'"

- [ ] **Step 3: Create the embedding service**

```python
# i3d_agent/rag/embedding.py
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
        self.client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=60.0)
        return self.client

    async def embed_text(self, text: str) -> List[float]:
        """
        为单个文本生成 embedding

        Args:
            text: 输入文本

        Returns:
            向量表示 (1536 维)
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成 embedding

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        if not texts:
            return []

        # 过滤空文本
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return [[] for _ in texts]

        try:
            embeddings = await self._call_embedding_api(valid_texts)

            # 如果有文本被过滤，填充空向量
            result = []
            text_iter = iter(embeddings)
            for original_text in texts:
                if original_text and original_text.strip():
                    result.append(next(text_iter))
                else:
                    result.append([])

            return result

        except Exception as e:
            logger.error(f"Embedding API call failed: {e}")
            raise

    async def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为 chunk 列表生成 embedding

        Args:
            chunks: chunk 列表，每个 chunk 包含 content 和 metadata

        Returns:
            添加了 embedding 的 chunk 列表
        """
        texts = [chunk["content"] for chunk in chunks]
        embeddings = await self.embed_batch(texts)

        result = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_with_embedding = chunk.copy()
            chunk_with_embedding["embedding"] = embedding
            result.append(chunk_with_embedding)

        return result

    async def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """
        调用 Embedding API

        支持 DashScope 和 OpenAI 格式
        """
        client = await self._get_client()

        provider = self.settings.DEFAULT_LLM_PROVIDER

        if provider == "dashscope":
            return await self._call_dashscope(client, texts)
        elif provider == "openai":
            return await self._call_openai(client, texts)
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    async def _call_dashscope(self, client: httpx.AsyncClient, texts: List[str]) -> List[List[float]]:
        """调用 DashScope Embedding API"""
        url = f"{self.settings.DASHSCOPE_BASE_URL}/embeddings"

        payload = {
            "model": "text-embedding-v3",
            "input": texts,
            "encoding_format": "float"
        }

        headers = {
            "Authorization": f"Bearer {self.settings.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }

        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()

        # DashScope 返回格式
        embeddings = []
        for item in data.get("data", []):
            embeddings.append(item.get("embedding", []))

        return embeddings

    async def _call_openai(self, client: httpx.AsyncClient, texts: List[str]) -> List[List[float]]:
        """调用 OpenAI Embedding API"""
        url = "https://api.openai.com/v1/embeddings"

        payload = {
            "model": self.settings.EMBEDDING_MODEL,
            "input": texts
        }

        headers = {
            "Authorization": f"Bearer {self.settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()

        # OpenAI 返回格式
        embeddings = []
        for item in data.get("data", []):
            embeddings.append(item.get("embedding", []))

        return embeddings

    async def close(self):
        """关闭客户端连接"""
        if self.client:
            await self.client.aclose()
            self.client = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_embedding.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/embedding.py tests/test_rag/test_embedding.py
git commit -m "feat(rag): add embedding service with batch support"
```

---

### Task 1.6: 创建文档管理器

**Files:**
- Create: `i3d_agent/rag/document_manager.py`
- Test: `i3d_agent/tests/test_rag/test_document_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_document_manager.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from i3d_agent.rag.document_manager import DocumentManager

@pytest.mark.asyncio
async def test_create_document():
    """测试创建文档"""
    manager = DocumentManager()

    with patch.object(manager, '_db_insert') as mock_insert, \
         patch.object(manager, '_add_index_task') as mock_task:

        mock_insert.return_value = Mock(id="doc-1", version=1)

        doc = await manager.create_document(
            tenant_id="default",
            title="Test Doc",
            content="Content here",
            doc_type="technical"
        )

        assert doc.id == "doc-1"
        mock_task.assert_called_once()

@pytest.mark.asyncio
async def test_update_document_creates_new_version():
    """测试更新文档创建新版本"""
    manager = DocumentManager()

    with patch.object(manager, '_get_document') as mock_get, \
         patch.object(manager, '_db_insert') as mock_insert, \
         patch.object(manager, '_db_update') as mock_update, \
         patch.object(manager, '_save_version_snapshot') as mock_snapshot, \
         patch.object(manager, '_add_index_task') as mock_task:

        # Mock current document
        current = Mock()
        current.id = "doc-1"
        current.version = 1
        current.content_hash = "old-hash"
        mock_get.return_value = current

        # Mock new document
        new_doc = Mock()
        new_doc.id = "doc-2"
        new_doc.version = 2
        mock_insert.return_value = new_doc

        updated = await manager.update_document("doc-1", content="New content")

        assert updated.version == 2
        mock_update.assert_called_once()
        mock_snapshot.assert_called_once()

@pytest.mark.asyncio
async def test_delete_document_soft_delete():
    """测试软删除文档"""
    manager = DocumentManager()

    with patch.object(manager, '_db_update') as mock_update, \
         patch.object(manager, '_add_index_task') as mock_task:

        await manager.delete_document("doc-1", hard_delete=False)

        mock_update.assert_called_once()
        # 检查 deleted_at 被设置
        call_args = mock_update.call_args
        assert 'deleted_at' in call_args[1]['data']

@pytest.mark.asyncio
async def test_restore_document():
    """测试恢复文档"""
    manager = DocumentManager()

    with patch.object(manager, '_db_update') as mock_update, \
         patch.object(manager, '_add_index_task') as mock_task:

        await manager.restore_document("doc-1")

        mock_update.assert_called_once()
        mock_task.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_document_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.document_manager'"

- [ ] **Step 3: Create the document manager**

```python
# i3d_agent/rag/document_manager.py
"""Document manager for CRUD operations and version control."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import hashlib
import asyncpg

from i3d_agent.rag.models import DocumentResponse, DocumentCreate, DocumentUpdate
from i3d_agent.rag.processor import DocumentProcessor
from i3d_agent.utils.logger import get_logger
from i3d_agent.config.settings import get_settings

logger = get_logger(__name__)


class DocumentManager:
    """文档管理器 - 负责 CRUD 操作和版本管理"""

    def __init__(self):
        self.settings = get_settings()
        self.processor = DocumentProcessor()
        self._pool = None

    async def _get_pool(self) -> asyncpg.Pool:
        """获取数据库连接池"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.settings.DATABASE_URL)
        return self._pool

    async def create_document(
        self,
        tenant_id: str,
        title: str,
        content: str,
        doc_type: str,
        source_type: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        language: str = "zh"
    ) -> DocumentResponse:
        """
        创建新文档

        Args:
            tenant_id: 租户 ID
            title: 文档标题
            content: 文档内容
            doc_type: 文档类型
            source_type: 来源类型
            description: 描述
            metadata: 元数据
            tags: 标签
            language: 语言

        Returns:
            创建的文档
        """
        # 计算内容哈希
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        pool = await self._get_pool()

        async with pool.acquire() as conn:
            doc_id = str(uuid4())

            # 创建文档记录
            row = await conn.fetchrow("""
                INSERT INTO rag_documents (
                    id, tenant_id, title, description, doc_type, source_type,
                    raw_content, content_hash, version, is_latest, status,
                    metadata, tags, language
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id, tenant_id, title, description, doc_type, source_type,
                          version, is_latest, status, metadata, tags, language,
                          created_at, updated_at
            """, doc_id, tenant_id, title, description, doc_type, source_type,
                 content, content_hash, 1, True, 'pending',
                 metadata or {}, tags or [], language)

        # 添加索引任务
        await self._add_index_task(doc_id, "create", tenant_id)

        logger.info(f"Created document {doc_id} for tenant {tenant_id}")

        return self._row_to_response(row)

    async def update_document(
        self,
        doc_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> DocumentResponse:
        """
        更新文档（创建新版本）

        Args:
            doc_id: 文档 ID
            content: 新内容
            title: 新标题
            description: 新描述
            metadata: 新元数据
            tags: 新标签

        Returns:
            更新后的文档
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # 获取当前文档
            current = await conn.fetchrow(
                "SELECT * FROM rag_documents WHERE id = $1 AND deleted_at IS NULL",
                doc_id
            )

            if not current:
                raise ValueError(f"Document {doc_id} not found")

            # 检查内容是否变化
            new_content = content if content is not None else current['raw_content']
            new_hash = hashlib.sha256(new_content.encode('utf-8')).hexdigest()

            if new_hash == current['content_hash'] and title is None:
                # 内容无变化，返回当前文档
                return self._row_to_response(current)

            # 创建新版本
            new_doc_id = str(uuid4())
            new_version = current['version'] + 1

            # 保存旧版本快照
            await self._save_version_snapshot(conn, current)

            # 标记旧版本不是最新
            await conn.execute(
                "UPDATE rag_documents SET is_latest = false WHERE id = $1",
                doc_id
            )

            # 创建新版本文档
            new_title = title if title is not None else current['title']
            new_description = description if description is not None else current['description']
            new_metadata = metadata if metadata is not None else current['metadata']
            new_tags = tags if tags is not None else current['tags']

            row = await conn.fetchrow("""
                INSERT INTO rag_documents (
                    id, tenant_id, title, description, doc_type, source_type,
                    raw_content, content_hash, version, is_latest, status,
                    metadata, tags, language, parent_doc_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING id, tenant_id, title, description, doc_type, source_type,
                          version, is_latest, status, metadata, tags, language,
                          created_at, updated_at
            """, new_doc_id, current['tenant_id'], new_title, new_description,
                 current['doc_type'], current['source_type'], new_content, new_hash,
                 new_version, True, 'pending', new_metadata, new_tags,
                 current['language'], doc_id)

        # 添加索引任务
        await self._add_index_task(new_doc_id, "update", current['tenant_id'])

        logger.info(f"Updated document {doc_id} to version {new_version}")

        return self._row_to_response(row)

    async def delete_document(
        self,
        doc_id: str,
        hard_delete: bool = False
    ) -> bool:
        """
        删除文档

        Args:
            doc_id: 文档 ID
            hard_delete: 是否物理删除

        Returns:
            是否成功
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            if hard_delete:
                # 物理删除
                await conn.execute("DELETE FROM rag_documents WHERE id = $1", doc_id)
                logger.warning(f"Hard deleted document {doc_id}")
            else:
                # 软删除
                await conn.execute(
                    "UPDATE rag_documents SET deleted_at = NOW() WHERE id = $1",
                    doc_id
                )
                logger.info(f"Soft deleted document {doc_id}")

        # 添加删除索引任务
        await self._add_index_task(doc_id, "delete")

        return True

    async def restore_document(
        self,
        doc_id: str,
        version: Optional[int] = None
    ) -> DocumentResponse:
        """
        恢复文档

        Args:
            doc_id: 文档 ID
            version: 恢复到指定版本

        Returns:
            恢复后的文档
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            if version:
                # 恢复到历史版本
                snapshot = await conn.fetchrow("""
                    SELECT * FROM rag_versions
                    WHERE doc_id = $1 AND version = $2
                """, doc_id, version)

                if not snapshot:
                    raise ValueError(f"Version {version} not found for document {doc_id}")

                # 创建新文档作为恢复版本
                return await self.create_document(
                    tenant_id=snapshot['tenant_id'],
                    title=f"{snapshot['metadata'].get('title', 'Restored')} (v{version})",
                    content=snapshot['content_snapshot'],
                    doc_type=snapshot['metadata'].get('doc_type', 'technical'),
                    metadata={**snapshot['metadata'], 'restored_from': version}
                )
            else:
                # 恢复软删除的文档
                await conn.execute(
                    "UPDATE rag_documents SET deleted_at = NULL WHERE id = $1",
                    doc_id
                )

                row = await conn.fetchrow(
                    "SELECT * FROM rag_documents WHERE id = $1",
                    doc_id
                )

                # 添加索引任务
                await self._add_index_task(doc_id, "update")

                return self._row_to_response(row)

    async def get_document(self, doc_id: str) -> Optional[DocumentResponse]:
        """获取文档详情"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM rag_documents WHERE id = $1 AND deleted_at IS NULL",
                doc_id
            )

            if not row:
                return None

            return self._row_to_response(row)

    async def get_document_history(
        self,
        doc_id: str
    ) -> List[Dict[str, Any]]:
        """获取文档版本历史"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT version, change_type, change_reason, changed_by, created_at
                FROM rag_versions
                WHERE doc_id = $1
                ORDER BY version DESC
            """, doc_id)

            return [dict(row) for row in rows]

    async def list_documents(
        self,
        tenant_id: str,
        doc_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """列出文档（分页）"""
        pool = await self._get_pool()

        offset = (page - 1) * page_size

        async with pool.acquire() as conn:
            # 构建查询条件
            conditions = ["tenant_id = $1", "deleted_at IS NULL", "is_latest = true"]
            params = [tenant_id]
            param_count = 1

            if doc_type:
                param_count += 1
                conditions.append(f"doc_type = ${param_count}")
                params.append(doc_type)

            # 查询总数
            count_query = f"SELECT COUNT(*) FROM rag_documents WHERE {' AND '.join(conditions)}"
            total = await conn.fetchval(count_query, *params)

            # 查询文档
            query = f"""
                SELECT * FROM rag_documents
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            params.extend([page_size, offset])

            rows = await conn.fetch(query, *params)

            documents = [self._row_to_response(row) for row in rows]

            return {
                "documents": documents,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

    async def _add_index_task(
        self,
        doc_id: str,
        operation: str,
        tenant_id: Optional[str] = None
    ):
        """添加索引任务到队列"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO rag_index_queue (doc_id, tenant_id, operation, status)
                VALUES ($1, $2, $3, 'pending')
            """, doc_id, tenant_id, operation)

    async def _save_version_snapshot(self, conn: asyncpg.Connection, doc: Dict[str, Any]):
        """保存版本快照"""
        await conn.execute("""
            INSERT INTO rag_versions (doc_id, tenant_id, version, content_snapshot, metadata, change_type)
            VALUES ($1, $2, $3, $4, $5, 'update')
        """, doc['id'], doc['tenant_id'], doc['version'],
             doc['raw_content'], doc['metadata'])

    def _row_to_response(self, row: asyncpg.Record) -> DocumentResponse:
        """转换数据库行到响应对象"""
        return DocumentResponse(
            id=str(row['id']),
            tenant_id=row['tenant_id'],
            title=row['title'],
            description=row['description'],
            doc_type=row['doc_type'],
            source_type=row['source_type'],
            version=row['version'],
            is_latest=row['is_latest'],
            status=row['status'],
            metadata=dict(row['metadata']) if row['metadata'] else {},
            tags=list(row['tags']) if row['tags'] else [],
            language=row['language'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    async def close(self):
        """关闭数据库连接"""
        if self._pool:
            await self._pool.close()
            self._pool = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_document_manager.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/document_manager.py tests/test_rag/test_document_manager.py
git commit -m "feat(rag): add document manager with version control"
```

---

### Task 1.7: 创建索引 Worker

**Files:**
- Create: `i3d_agent/rag/index_worker.py`
- Test: `i3d_agent/tests/test_rag/test_index_worker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_index_worker.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from i3d_agent.rag.index_worker import IndexWorker

@pytest.mark.asyncio
async def test_process_document_create():
    """测试处理文档创建"""
    worker = IndexWorker()

    with patch.object(worker, '_get_document') as mock_get, \
         patch.object(worker, '_split_and_embed') as mock_embed, \
         patch.object(worker, '_save_chunks') as mock_save, \
         patch.object(worker, '_mark_completed') as mock_complete:

        mock_get.return_value = Mock(
            id="doc-1",
            raw_content="Test content",
            doc_type="technical",
            tenant_id="default",
            version=1
        )
        mock_embed.return_value = [
            {"content": "Chunk 1", "embedding": [0.1] * 1536, "metadata": {}}
        ]

        await worker.process_task("task-1")

        mock_embed.assert_called_once()
        mock_save.assert_called_once()
        mock_complete.assert_called_once()

@pytest.mark.asyncio
async def test_process_document_update():
    """测试处理文档更新"""
    worker = IndexWorker()

    with patch.object(worker, '_get_document') as mock_get, \
         patch.object(worker, '_soft_delete_old_chunks') as mock_delete, \
         patch.object(worker, '_split_and_embed') as mock_embed, \
         patch.object(worker, '_save_chunks') as mock_save:

        mock_get.return_value = Mock(
            id="doc-1",
            raw_content="New content",
            doc_type="technical",
            tenant_id="default",
            version=2,
            parent_doc_id="old-doc-1"
        )

        await worker.process_task("task-1", operation="update")

        mock_delete.assert_called_once_with("old-doc-1")
        mock_embed.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_index_worker.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.index_worker'"

- [ ] **Step 3: Create the index worker**

```python
# i3d_agent/rag/index_worker.py
"""Index worker for processing document indexing tasks."""

from typing import Optional, Dict, Any
import asyncio
from i3d_agent.rag.processor import DocumentProcessor
from i3d_agent.rag.embedding import EmbeddingService
from i3d_agent.utils.logger import get_logger
from i3d_agent.config.settings import get_settings
import asyncpg

logger = get_logger(__name__)


class IndexWorker:
    """索引 Worker - 处理文档索引任务"""

    def __init__(self):
        self.settings = get_settings()
        self.processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
        self._pool = None
        self._running = False

    async def _get_pool(self) -> asyncpg.Pool:
        """获取数据库连接池"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.settings.DATABASE_URL)
        return self._pool

    async def process_task(self, task_id: str) -> bool:
        """
        处理单个索引任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # 获取任务信息
            task = await conn.fetchrow("""
                SELECT id, doc_id, tenant_id, operation, status, retry_count
                FROM rag_index_queue
                WHERE id = $1
            """, task_id)

            if not task:
                logger.warning(f"Task {task_id} not found")
                return False

            if task['status'] == 'completed':
                logger.info(f"Task {task_id} already completed")
                return True

            try:
                # 标记为处理中
                await conn.execute("""
                    UPDATE rag_index_queue
                    SET status = 'processing', started_at = NOW()
                    WHERE id = $1
                """, task_id)

                # 获取文档信息
                doc = await self._get_document(conn, task['doc_id'])

                if not doc:
                    raise ValueError(f"Document {task['doc_id']} not found")

                # 根据操作类型处理
                if task['operation'] == 'create':
                    await self._process_create(conn, doc)
                elif task['operation'] == 'update':
                    await self._process_update(conn, doc)
                elif task['operation'] == 'delete':
                    await self._process_delete(conn, doc)

                # 标记为完成
                await conn.execute("""
                    UPDATE rag_index_queue
                    SET status = 'completed', completed_at = NOW()
                    WHERE id = $1
                """, task_id)

                # 更新文档状态
                await conn.execute("""
                    UPDATE rag_documents
                    SET status = 'ready'
                    WHERE id = $1
                """, task['doc_id'])

                logger.info(f"Task {task_id} completed successfully")
                return True

            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")

                # 标记为失败
                await conn.execute("""
                    UPDATE rag_index_queue
                    SET status = 'failed',
                        error_message = $1,
                        retry_count = retry_count + 1
                    WHERE id = $2
                """, str(e), task_id)

                # 更新文档状态
                await conn.execute("""
                    UPDATE rag_documents
                    SET status = 'failed', error_message = $1
                    WHERE id = $2
                """, str(e), task['doc_id'])

                return False

    async def _get_document(self, conn: asyncpg.Connection, doc_id: str) -> Optional[Dict]:
        """获取文档信息"""
        row = await conn.fetchrow("""
            SELECT id, tenant_id, title, raw_content, doc_type,
                   language, version, parent_doc_id, metadata
            FROM rag_documents
            WHERE id = $1
        """, doc_id)

        if not row:
            return None

        return dict(row)

    async def _process_create(self, conn: asyncpg.Connection, doc: Dict[str, Any]):
        """处理文档创建"""
        # 切分文档
        chunks = self.processor.split_content(
            doc['raw_content'],
            doc_type=doc['doc_type'],
            doc_id=doc['id'],
            title=doc['title'],
            language=doc['language']
        )

        # 生成 embedding
        chunks_with_embeddings = await self.embedding_service.embed_chunks(chunks)

        # 保存 chunks
        await self._save_chunks(conn, doc, chunks_with_embeddings)

        logger.info(f"Indexed {len(chunks)} chunks for document {doc['id']}")

    async def _process_update(self, conn: asyncpg.Connection, doc: Dict[str, Any]):
        """处理文档更新"""
        # 软删除旧版本的 chunks
        if doc.get('parent_doc_id'):
            await self._soft_delete_old_chunks(conn, doc['parent_doc_id'])

        # 处理新版本
        await self._process_create(conn, doc)

    async def _process_delete(self, conn: asyncpg.Connection, doc: Dict[str, Any]):
        """处理文档删除"""
        await self._soft_delete_old_chunks(conn, doc['id'])

    async def _soft_delete_old_chunks(self, conn: asyncpg.Connection, doc_id: str):
        """软删除旧的 chunks"""
        await conn.execute("""
            UPDATE rag_chunks
            SET deleted_at = NOW()
            WHERE doc_id = $1
        """, doc_id)

    async def _save_chunks(
        self,
        conn: asyncpg.Connection,
        doc: Dict[str, Any],
        chunks: list
    ):
        """保存 chunks 到数据库"""
        for chunk in chunks:
            chunk_id = await conn.fetchval("""
                INSERT INTO rag_chunks (
                    id, doc_id, tenant_id, content, embedding,
                    chunk_index, token_count, metadata, doc_version
                ) VALUES (
                    gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8
                ) RETURNING id
            """, doc['id'], doc['tenant_id'], chunk['content'],
                 chunk['embedding'], chunk['metadata']['chunk_index'],
                 chunk['metadata'].get('token_count'),
                 chunk['metadata'], doc['version'])

    async def run_worker(self, concurrency: int = 2):
        """
        运行 Worker 持续处理队列

        Args:
            concurrency: 并发处理数
        """
        self._running = True
        logger.info(f"Index worker started with concurrency {concurrency}")

        while self._running:
            try:
                pool = await self._get_pool()

                # 获取待处理任务
                async with pool.acquire() as conn:
                    tasks = await conn.fetch("""
                        SELECT id
                        FROM rag_index_queue
                        WHERE status = 'pending'
                        ORDER BY priority DESC, created_at ASC
                        LIMIT $1
                    """, concurrency)

                if not tasks:
                    await asyncio.sleep(1)
                    continue

                # 并发处理任务
                await asyncio.gather(
                    *[self.process_task(str(task['id'])) for task in tasks]
                )

            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(5)

    def stop_worker(self):
        """停止 Worker"""
        self._running = False
        logger.info("Index worker stopping...")

    async def close(self):
        """关闭连接"""
        self.stop_worker()
        if self._pool:
            await self._pool.close()
            self._pool = None
        await self.embedding_service.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_index_worker.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/index_worker.py tests/test_rag/test_index_worker.py
git commit -m "feat(rag): add index worker for async document processing"
```

---

## Phase 2: 核心检索

### Task 2.1: 创建检索引擎（向量 + BM25）

**Files:**
- Create: `i3d_agent/rag/retrieval.py`
- Test: `i3d_agent/tests/test_rag/test_retrieval.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_retrieval.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from i3d_agent.rag.retrieval import RetrievalEngine

@pytest.mark.asyncio
async def test_vector_search():
    """测试向量检索"""
    engine = RetrievalEngine()

    with patch.object(engine, '_db_fetch') as mock_fetch:
        mock_fetch.return_value = [
            Mock(id="c1", doc_id="d1", content="Content 1", score=0.9),
            Mock(id="c2", doc_id="d2", content="Content 2", score=0.8)
        ]

        results = await engine.vector_search(
            query_vector=[0.1] * 1536,
            tenant_id="default",
            top_k=10
        )

        assert len(results) == 2

@pytest.mark.asyncio
async def test_bm25_search():
    """测试 BM25 检索"""
    engine = RetrievalEngine()

    with patch.object(engine, '_db_fetch') as mock_fetch:
        mock_fetch.return_value = [
            Mock(id="c1", doc_id="d1", content="Content 1", score=0.9)
        ]

        results = await engine.bm25_search(
            query="test query",
            tenant_id="default",
            top_k=10
        )

        assert len(results) == 1

@pytest.mark.asyncio
async def test_hybrid_retrieval():
    """测试混合检索"""
    engine = RetrievalEngine()

    with patch.object(engine, 'vector_search') as mock_vector, \
         patch.object(engine, 'bm25_search') as mock_bm25:

        mock_vector.return_value = [
            Mock(id="c1", final_score=0.9, vector_score=0.9, bm25_score=0.0),
            Mock(id="c2", final_score=0.8, vector_score=0.8, bm25_score=0.0)
        ]
        mock_bm25.return_value = [
            Mock(id="c1", final_score=0.7, vector_score=0.0, bm25_score=0.7),
            Mock(id="c3", final_score=0.6, vector_score=0.0, bm25_score=0.6)
        ]

        results = await engine.hybrid_retrieval(
            query="test query",
            query_vector=[0.1] * 1536,
            tenant_id="default",
            top_k=10
        )

        # 应该去重并融合分数
        assert len(results) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_retrieval.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.retrieval'"

- [ ] **Step 3: Create the retrieval engine**

```python
# i3d_agent/rag/retrieval.py
"""Retrieval engine for hybrid vector and BM25 search."""

from typing import List, Dict, Any, Optional, Tuple
import asyncpg
from i3d_agent.rag.models import Chunk
from i3d_agent.utils.logger import get_logger
from i3d_agent.config.settings import get_settings

logger = get_logger(__name__)


class RetrievalEngine:
    """检索引擎 - 支持向量检索、BM25 检索和混合检索"""

    def __init__(self):
        self.settings = get_settings()
        self._pool = None

    async def _get_pool(self) -> asyncpg.Pool:
        """获取数据库连接池"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.settings.DATABASE_URL)
        return self._pool

    async def vector_search(
        self,
        query_vector: List[float],
        tenant_id: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        向量检索（使用 pgvector HNSW 索引）

        Args:
            query_vector: 查询向量
            tenant_id: 租户 ID
            top_k: 返回结果数
            filters: 额外过滤条件

        Returns:
            检索结果列表
        """
        if len(query_vector) != self.settings.VECTOR_DIMENSION:
            raise ValueError(f"Vector dimension must be {self.settings.VECTOR_DIMENSION}")

        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # 构建查询条件
            conditions = ["tenant_id = $1", "deleted_at IS NULL"]
            params = [tenant_id]
            param_count = 1

            if filters:
                if 'doc_type' in filters:
                    param_count += 1
                    conditions.append(f"metadata->>'doc_type' = ${param_count}")
                    params.append(filters['doc_type'])

            # 执行向量检索
            query = f"""
                SELECT id, doc_id, tenant_id, content, chunk_index,
                       metadata, doc_version, token_count,
                       1 - (embedding <=> ${param_count + 1}) AS similarity
                FROM rag_chunks
                WHERE {' AND '.join(conditions)}
                ORDER BY embedding <=> ${param_count + 1}
                LIMIT ${param_count + 2}
            """
            params.extend([query_vector, top_k])

            rows = await conn.fetch(query, *params)

        results = []
        for row in rows:
            chunk = Chunk(
                id=str(row['id']),
                doc_id=str(row['doc_id']),
                tenant_id=row['tenant_id'],
                content=row['content'],
                embedding=[],
                chunk_index=row['chunk_index'],
                token_count=row['token_count'],
                metadata=dict(row['metadata']) if row['metadata'] else {},
                doc_version=row['doc_version'],
                vector_score=float(row['similarity']),
                bm25_score=None,
                final_score=float(row['similarity'])
            )
            results.append(chunk)

        return results

    async def bm25_search(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        BM25 全文检索（使用 PostgreSQL tsvector）

        Args:
            query: 查询文本
            tenant_id: 租户 ID
            top_k: 返回结果数
            filters: 额外过滤条件

        Returns:
            检索结果列表
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # 转换查询为 tsquery
            query_terms = self._parse_query(query)
            tsquery = " & ".join(query_terms)

            # 构建条件
            conditions = ["c.tenant_id = $1", "c.deleted_at IS NULL"]
            params = [tenant_id]
            param_count = 1

            if filters:
                if 'doc_type' in filters:
                    param_count += 1
                    conditions.append(f"c.metadata->>'doc_type' = ${param_count}")
                    params.append(filters['doc_type'])

            # 执行 BM25 检索
            query_sql = f"""
                SELECT c.id, c.doc_id, c.tenant_id, c.content,
                       c.chunk_index, c.metadata, c.doc_version, c.token_count,
                       ts_rank(c.content_tsv, to_tsquery('simple', ${param_count + 1})) AS bm25_score
                FROM rag_chunks c
                WHERE {' AND '.join(conditions)}
                  AND c.content_tsv @@ to_tsquery('simple', ${param_count + 1})
                ORDER BY bm25_score DESC
                LIMIT ${param_count + 2}
            """
            params.extend([tsquery, top_k])

            rows = await conn.fetch(query_sql, *params)

        results = []
        for row in rows:
            chunk = Chunk(
                id=str(row['id']),
                doc_id=str(row['doc_id']),
                tenant_id=row['tenant_id'],
                content=row['content'],
                embedding=[],
                chunk_index=row['chunk_index'],
                token_count=row['token_count'],
                metadata=dict(row['metadata']) if row['metadata'] else {},
                doc_version=row['doc_version'],
                vector_score=None,
                bm25_score=float(row['bm25_score']),
                final_score=float(row['bm25_score'])
            )
            results.append(chunk)

        return results

    async def hybrid_retrieval(
        self,
        query: str,
        query_vector: List[float],
        tenant_id: str,
        top_k: int = 20,
        search_type: str = "balanced",
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        混合检索（向量 + BM25）

        Args:
            query: 查询文本
            query_vector: 查询向量
            tenant_id: 租户 ID
            top_k: 返回结果数
            search_type: 检索类型（semantic, keyword, balanced, exact_match）
            filters: 额外过滤条件

        Returns:
            检索结果列表
        """
        # 获取动态权重
        alpha, beta = self._get_dynamic_weights(search_type)

        # 并行执行两种检索
        import asyncio
        vector_results, bm25_results = await asyncio.gather(
            self.vector_search(query_vector, tenant_id, top_k * 2, filters),
            self.bm25_search(query, tenant_id, top_k * 2, filters)
        )

        # 合并去重
        merged = self._merge_and_deduplicate(vector_results, bm25_results)

        # 分数融合
        for chunk in merged:
            vec_score = chunk.vector_score or 0
            bm25_score = chunk.bm25_score or 0

            # 归一化分数
            norm_vec = vec_score  # cosine similarity 已经在 [0, 1]
            norm_bm25 = self._normalize_bm25(bm25_score)

            chunk.final_score = alpha * norm_vec + beta * norm_bm25

        # 排序并返回 Top-K
        results = sorted(merged, key=lambda x: x.final_score, reverse=True)[:top_k]

        return results

    def _get_dynamic_weights(self, search_type: str) -> Tuple[float, float]:
        """根据检索类型获取动态权重"""
        weights = {
            "semantic": (0.8, 0.2),
            "keyword": (0.3, 0.7),
            "balanced": (0.5, 0.5),
            "exact_match": (0.1, 0.9)
        }
        return weights.get(search_type, (0.6, 0.4))

    def _normalize_bm25(self, score: float) -> float:
        """归一化 BM25 分数"""
        # BM25 分数通常在 0-10 范围内
        return min(score / 10.0, 1.0)

    def _parse_query(self, query: str) -> List[str]:
        """解析查询为搜索词"""
        # 简单的分词，实际可以使用更复杂的 NLP
        import re
        # 移除特殊字符，保留中英文和数字
        cleaned = re.sub(r'[^\w\s一-鿿]', ' ', query)
        # 分词
        terms = [t.strip() for t in cleaned.split() if t.strip()]
        return terms

    def _merge_and_deduplicate(
        self,
        vector_results: List[Chunk],
        bm25_results: List[Chunk]
    ) -> List[Chunk]:
        """合并并去重结果"""
        seen_ids = set()
        merged = []

        # 先添加向量检索结果
        for chunk in vector_results:
            if chunk.id not in seen_ids:
                merged.append(chunk)
                seen_ids.add(chunk.id)

        # 添加 BM25 结果，合并分数
        for chunk in bm25_results:
            if chunk.id in seen_ids:
                # 已存在，更新 BM25 分数
                for existing in merged:
                    if existing.id == chunk.id:
                        existing.bm25_score = chunk.bm25_score
                        break
            else:
                merged.append(chunk)
                seen_ids.add(chunk.id)

        return merged

    def classify_query(self, query: str) -> str:
        """
        自动识别查询类型

        Returns:
            查询类型（semantic, keyword, balanced, exact_match）
        """
        import re

        # 精确匹配模式（错误代码、API 端点、版本号）
        if re.search(r'(ERR-\d+|E\d+|/api/|v\d+\.\d+)', query):
            return "exact_match"

        # 关键词模式（专有名词密集）
        if len(re.findall(r'\b[A-Z]{2,}\b', query)) >= 2:
            return "keyword"

        # 语义问题（包含疑问词）
        question_words = ['如何', '怎样', '怎么', '为什么', 'what', 'how', 'why']
        if any(word in query.lower() for word in question_words):
            return "semantic"

        return "balanced"

    async def close(self):
        """关闭连接"""
        if self._pool:
            await self._pool.close()
            self._pool = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_retrieval.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/retrieval.py tests/test_rag/test_retrieval.py
git commit -m "feat(rag): add retrieval engine with hybrid search support"
```

---

### Task 2.2: 创建重排序服务

**Files:**
- Create: `i3d_agent/rag/rerank.py`
- Test: `i3d_agent/tests/test_rag/test_rerank.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_rerank.py
import pytest
from unittest.mock import Mock, patch
from i3d_agent.rag.rerank import RerankService

@pytest.mark.asyncio
async def test_rerank_with_cohere():
    """测试使用 Cohere 重排序"""
    service = RerankService()

    with patch.object(service, '_call_cohere_rerank') as mock_cohere:
        mock_cohere.return_value = [
            {"index": 2, "relevance_score": 0.95},
            {"index": 0, "relevance_score": 0.85},
            {"index": 1, "relevance_score": 0.75}
        ]

        chunks = [
            Mock(id="c1", content="Content 1"),
            Mock(id="c2", content="Content 2"),
            Mock(id="c3", content="Content 3")
        ]

        results = await service.rerank(
            query="test query",
            chunks=chunks,
            top_k=3
        )

        assert results[0].id == "c3"  # index 2
        assert results[1].id == "c1"  # index 0

@pytest.mark.asyncio
async def test_rerank_fallback_to_original():
    """测试重排序失败时回退到原始顺序"""
    service = RerankService()

    with patch.object(service, '_call_cohere_rerank') as mock_cohere:
        mock_cohere.side_effect = Exception("API error")

        chunks = [
            Mock(id="c1", content="Content 1"),
            Mock(id="c2", content="Content 2")
        ]

        results = await service.rerank(
            query="test query",
            chunks=chunks,
            top_k=2
        )

        # 应该返回原始顺序
        assert results[0].id == "c1"
        assert results[1].id == "c2"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_rerank.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.rerank'"

- [ ] **Step 3: Create the rerank service**

```python
# i3d_agent/rag/rerank.py
"""Reranking service for improving retrieval quality."""

from typing import List, Dict, Any, Optional
import httpx
from i3d_agent.rag.models import Chunk
from i3d_agent.utils.logger import get_logger
from i3d_agent.config.settings import get_settings

logger = get_logger(__name__)


class RerankService:
    """重排序服务 - 使用 Cohere Rerank API 或本地模型"""

    def __init__(self):
        self.settings = get_settings()
        self.client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client

    async def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int = 10
    ) -> List[Chunk]:
        """
        对检索结果进行重排序

        Args:
            query: 原始查询
            chunks: 检索结果
            top_k: 保留的结果数

        Returns:
            重排序后的结果
        """
        if not chunks:
            return chunks

        if len(chunks) <= top_k:
            return chunks

        try:
            provider = self.settings.RERANK_PROVIDER

            if provider == "cohere":
                return await self._rerank_with_cohere(query, chunks, top_k)
            else:
                logger.warning(f"Unknown rerank provider: {provider}")
                return chunks[:top_k]

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            # 回退到原始顺序
            return chunks[:top_k]

    async def _rerank_with_cohere(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int
    ) -> List[Chunk]:
        """使用 Cohere Rerank API 重排序"""
        if not self.settings.COHERE_API_KEY:
            logger.warning("Cohere API key not configured")
            return chunks[:top_k]

        client = await self._get_client()

        # 准备文档
        docs = [chunk.content for chunk in chunks]

        payload = {
            "model": self.settings.RERANK_MODEL,
            "query": query,
            "documents": docs,
            "top_n": top_k,
            "return_documents": False
        }

        headers = {
            "Authorization": f"Bearer {self.settings.COHERE_API_KEY}",
            "Content-Type": "application/json"
        }

        response = await client.post(
            "https://api.cohere.ai/v1/rerank",
            json=payload,
            headers=headers
        )
        response.raise_for_status()

        data = response.json()

        # 根据返回的索引重新排序
        reranked = []
        for result in data.get("results", []):
            index = result.get("index")
            if 0 <= index < len(chunks):
                chunk = chunks[index]
                chunk.final_score = result.get("relevance_score", chunk.final_score)
                reranked.append(chunk)

        return reranked

    async def close(self):
        """关闭客户端连接"""
        if self.client:
            await self.client.aclose()
            self.client = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_rerank.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/rerank.py tests/test_rag/test_rerank.py
git commit -m "feat(rag): add reranking service with Cohere integration"
```

---

### Task 2.3: 更新 RAG Agent

**Files:**
- Modify: `i3d_agent/agents/rag.py`

- [ ] **Step 1: Update RAG Agent to use new RAG module**

```python
# i3d_agent/agents/rag.py
"""RAG agent for technical document Q&A with full RAG capabilities."""

from typing import Any, Dict, Optional
from i3d_agent.agents.base import AgentConfig, BaseAgent
from i3d_agent.rag.retrieval import RetrievalEngine
from i3d_agent.rag.rerank import RerankService
from i3d_agent.rag.models import Chunk, RetrievalResult
from i3d_agent.llm import get_llm_client, Message
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class RAGAgent(BaseAgent):
    """RAG agent for technical document Q&A with full retrieval capabilities."""

    def __init__(self, config: Optional[AgentConfig] = None):
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

        # 初始化 RAG 组件
        self.retrieval_engine = RetrievalEngine()
        self.rerank_service = RerankService()

    async def answer(
        self,
        question: str,
        tenant_id: Optional[str] = None,
        top_k: int = 5,
        enable_rerank: bool = True,
    ) -> Dict[str, Any]:
        """
        回答技术问题

        Args:
            question: 问题
            tenant_id: 租户 ID
            top_k: 检索文档数
            enable_rerank: 是否启用重排序

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
            # 生成查询向量
            from i3d_agent.rag.embedding import EmbeddingService
            embedding_service = EmbeddingService()
            query_vector = await embedding_service.embed_text(question)

            # 执行检索
            search_type = self.retrieval_engine.classify_query(question)
            results = await self.retrieval_engine.hybrid_retrieval(
                query=question,
                query_vector=query_vector,
                tenant_id=tenant_id or "default",
                top_k=top_k * 2,  # 获取更多结果用于重排序
                search_type=search_type
            )

            if not results:
                return {
                    "question": question,
                    "answer": "抱歉，知识库中没有找到相关文档。",
                    "sources": [],
                    "status": "no_results"
                }

            # 重排序
            if enable_rerank:
                results = await self.rerank_service.rerank(
                    query=question,
                    chunks=results,
                    top_k=top_k
                )

            # 构建上下文
            context = self._build_context(results)

            # 生成答案
            answer = await self._generate_answer(question, context)

            # 提取来源
            sources = [
                {
                    "doc_id": r.doc_id,
                    "title": r.metadata.get("title", "Unknown"),
                    "score": r.final_score,
                    "chunk_index": r.chunk_index
                }
                for r in results[:3]  # Top 3 来源
            ]

            return {
                "question": question,
                "answer": answer,
                "sources": sources,
                "status": "success",
                "metadata": {
                    "num_retrieved": len(results),
                    "search_type": search_type,
                    "tenant_id": tenant_id
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
        """构建 LLM 上下文"""
        context_parts = []
        for i, result in enumerate(results, 1):
            title = result.metadata.get("title", "Unknown Document")
            content = result.content
            score = result.final_score or 0
            context_parts.append(f"[文档 {i}] {title} (相关度: {score:.2f})\n{content}")

        return "\n\n".join(context_parts)

    async def _generate_answer(self, question: str, context: str) -> str:
        """使用 LLM 生成答案"""
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
        """关闭连接"""
        await self.retrieval_engine.close()
        await self.rerank_service.close()
```

- [ ] **Step 2: Update tests for RAG Agent**

```python
# tests/test_agents/test_rag.py
# 更新现有测试以使用新的 RAG 实现
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_agents/test_rag.py -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add i3d_agent/agents/rag.py tests/test_agents/test_rag.py
git commit -m "feat(rag): update RAG agent with full retrieval capabilities"
```

---

## Phase 3: Agentic 特性

### Task 3.1: 创建查询扩展模块

**Files:**
- Create: `i3d_agent/rag/query_expansion.py`
- Test: `i3d_agent/tests/test_rag/test_query_expansion.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_query_expansion.py
import pytest
from unittest.mock import patch
from i3d_agent.rag.query_expansion import QueryExpansionService

@pytest.mark.asyncio
async def test_query_expansion():
    """测试查询扩展"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = """
        1. 3D 搜索 API 配置方法
        2. 设置 3D 搜索 API 的步骤
        3. 怎样配置三维搜索接口
        """

        variations = await service.expand_query("如何配置 3D 搜索 API？")

        assert len(variations) >= 3
        assert "如何配置 3D 搜索 API？" in variations

@pytest.mark.asyncio
async def test_query_expansion_with_custom_count():
    """测试自定义扩展数量"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = "Variation 1\nVariation 2"

        variations = await service.expand_query("test", num_variations=2)

        assert len(variations) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_query_expansion.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.query_expansion'"

- [ ] **Step 3: Create the query expansion service**

```python
# i3d_agent/rag/query_expansion.py
"""Query expansion service for generating query variations."""

from typing import List
from i3d_agent.llm import get_llm_client, Message
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class QueryExpansionService:
    """查询扩展服务 - 生成查询的不同表述"""

    def __init__(self):
        pass

    async def expand_query(
        self,
        query: str,
        num_variations: int = 3
    ) -> List[str]:
        """
        生成查询变体

        Args:
            query: 原始查询
            num_variations: 生成变体数量

        Returns:
            查询列表（包含原始查询）
        """
        if not query or not query.strip():
            return [query]

        try:
            prompt = f"""为以下查询生成 {num_variations} 个不同表述，保持原意不变。每行一个表述。

查询：{query}

变体："""

            llm_client = get_llm_client()
            response = await llm_client.generate(
                messages=[Message(role="user", content=prompt)],
                temperature=0.7
            )

            # 解析变体
            variations = [query]  # 包含原始查询
            lines = response.strip().split('\n')

            for line in lines:
                line = line.strip()
                # 移除序号
                line = line.lstrip('123456789.-)•、.')
                if line and line not in variations:
                    variations.append(line)
                    if len(variations) >= num_variations + 1:
                        break

            logger.debug(f"Expanded query to {len(variations)} variations")
            return variations

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [query]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_query_expansion.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/query_expansion.py tests/test_rag/test_query_expansion.py
git commit -m "feat(rag): add query expansion service"
```

---

### Task 3.2: 创建 HyDE 模块

**Files:**
- Create: `i3d_agent/rag/hyde.py`
- Test: `i3d_agent/tests/test_rag/test_hyde.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_hyde.py
import pytest
from unittest.mock import patch
from i3d_agent.rag.hyde import HyDEService

@pytest.mark.asyncio
async def test_hyde_generation():
    """测试 HyDE 假设文档生成"""
    service = HyDEService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = """RAG 检索质量差的原因包括：
1. 文档切分策略不当
2. 缺少混合检索
3. 未使用重排序

改进方法：
1. 调整 chunk size
2. 结合向量检索和 BM25
3. 使用 Cohere Rerank API"""

        result = await service.generate_hypothetical("如何提高 RAG 检索质量？")

        assert result is not None
        assert "原因" in result or "改进" in result

@pytest.mark.asyncio
async def test_hyde_for_non_question():
    """测试非疑问句不生成 HyDE"""
    service = HyDEService()

    result = await service.generate_hypothetical("API 文档")

    assert result is None

@pytest.mark.asyncio
async def test_detect_question():
    """测试疑问句检测"""
    service = HyDEService()

    assert service._is_question("如何配置 API？")
    assert service._is_question("怎样使用这个功能")
    assert not service._is_question("API 文档")
    assert not service._is_question("系统配置")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_hyde.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.hyde'"

- [ ] **Step 3: Create the HyDE service**

```python
# i3d_agent/rag/hyde.py
"""HyDE (Hypothetical Document Embeddings) service."""

from typing import Optional
from i3d_agent.llm import get_llm_client, Message
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class HyDEService:
    """HyDE 服务 - 生成假设性文档用于检索"""

    # 疑问词列表
    QUESTION_WORDS = [
        '如何', '怎样', '怎么', '为什么', '是什么', '哪里', '哪个',
        'what', 'how', 'why', 'where', 'which', 'who', 'when'
    ]

    def __init__(self):
        pass

    def _is_question(self, text: str) -> bool:
        """检测是否为疑问句"""
        text_lower = text.lower()
        return any(word in text_lower for word in self.QUESTION_WORDS)

    async def generate_hypothetical(self, query: str) -> Optional[str]:
        """
        生成假设性文档

        Args:
            query: 用户查询

        Returns:
            假设性文档，如果不是疑问句则返回 None
        """
        if not self._is_question(query):
            return None

        try:
            prompt = f"""假设你是一个专家，针对以下问题给出一个详细的回答。包含具体的步骤、参数、代码示例或技术细节。

问题：{query}

假设回答："""

            llm_client = get_llm_client()
            response = await llm_client.generate(
                messages=[Message(role="user", content=prompt)],
                temperature=0.7
            )

            logger.debug(f"Generated hypothetical document for query: {query}")
            return response.strip()

        except Exception as e:
            logger.error(f"HyDE generation failed: {e}")
            return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_hyde.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/hyde.py tests/test_rag/test_hyde.py
git commit -m "feat(rag): add HyDE service for hypothetical document generation"
```

---

### Task 3.3: 创建 Agentic RAG Controller

**Files:**
- Create: `i3d_agent/rag/controller.py`
- Test: `i3d_agent/tests/test_rag/test_controller.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_controller.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from i3d_agent.rag.controller import AgenticRAGController

@pytest.mark.asyncio
async def test_retrieve_with_all_features():
    """测试使用所有特性的检索"""
    controller = AgenticRAGController()

    with patch.object(controller, 'query_expansion') as mock_expansion, \
         patch.object(controller, 'hyde_service') as mock_hyde, \
         patch.object(controller, 'retrieval_engine') as mock_retrieval, \
         patch.object(controller, 'rerank_service') as mock_rerank:

        mock_expansion.expand_query.return_value = ["query", "variation 1", "variation 2"]
        mock_hyde.generate_hypothetical.return_value = "hypothetical document"

        # 模拟检索结果
        mock_chunks = [
            Mock(id="c1", content="Content 1", final_score=0.9),
            Mock(id="c2", content="Content 2", final_score=0.8)
        ]

        async def mock_hybrid(*args, **kwargs):
            return mock_chunks

        mock_retrieval.hybrid_retrieval = mock_hybrid
        mock_rerank.rerank.return_value = mock_chunks

        result = await controller.retrieve(
            query="test query",
            tenant_id="default",
            enable_expansion=True,
            enable_hyde=True,
            enable_rerank=True,
            top_k=5
        )

        assert len(result.results) > 0
        assert result.query == "test query"

@pytest.mark.asyncio
async def test_multi_step_reasoning():
    """测试多步推理"""
    controller = AgenticRAGController()

    with patch.object(controller, '_assess_quality') as mock_assess, \
         patch.object(controller, 'retrieval_engine') as mock_retrieval:

        # 第一次迭代质量低，第二次高
        mock_assess.side_effect = [
            Mock(is_satisfactory=False, issue="low_relevance", feedback="需要更精确的关键词"),
            Mock(is_satisfactory=True)
        ]

        async def mock_hybrid(*args, **kwargs):
            return [Mock(id="c1", content="Content")]

        mock_retrieval.hybrid_retrieval = mock_hybrid

        result = await controller.retrieve_with_multi_step(
            query="test",
            query_vector=[0.1] * 1536,
            tenant_id="default",
            max_iterations=3
        )

        assert result.iterations >= 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_controller.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.controller'"

- [ ] **Step 3: Create the Agentic RAG controller**

```python
# i3d_agent/rag/controller.py
"""Agentic RAG controller coordinating all RAG capabilities."""

from typing import List, Optional, Dict, Any
import asyncio
from i3d_agent.rag.models import Chunk, RetrievalResult
from i3d_agent.rag.retrieval import RetrievalEngine
from i3d_agent.rag.rerank import RerankService
from i3d_agent.rag.query_expansion import QueryExpansionService
from i3d_agent.rag.hyde import HyDEService
from i3d_agent.rag.embedding import EmbeddingService
from i3d_agent.llm import get_llm_client, Message
from i3d_agent.utils.logger import get_logger
from i3d_agent.config.settings import get_settings

logger = get_logger(__name__)


class QualityAssessment:
    """质量评估结果"""
    def __init__(self, is_satisfactory: bool, issue: Optional[str] = None, feedback: str = ""):
        self.is_satisfactory = is_satisfactory
        self.issue = issue
        self.feedback = feedback


class AgenticRAGController:
    """Agentic RAG 控制器 - 协调查询扩展、HyDE、重排序、多步推理"""

    def __init__(self):
        self.settings = get_settings()
        self.retrieval_engine = RetrievalEngine()
        self.rerank_service = RerankService()
        self.query_expansion = QueryExpansionService()
        self.hyde_service = HyDEService()
        self.embedding_service = EmbeddingService()

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 10,
        enable_expansion: bool = True,
        enable_hyde: bool = True,
        enable_rerank: bool = True,
        enable_multi_step: bool = False,
        search_type: str = "balanced"
    ) -> RetrievalResult:
        """
        统一检索入口

        Args:
            query: 查询文本
            tenant_id: 租户 ID
            top_k: 返回结果数
            enable_expansion: 启用查询扩展
            enable_hyde: 启用 HyDE
            enable_rerank: 启用重排序
            enable_multi_step: 启用多步推理
            search_type: 检索类型

        Returns:
            检索结果
        """
        # 1. 查询扩展
        queries = [query]
        query_expansions = []
        hypothetical_doc = None

        if enable_expansion:
            variations = await self.query_expansion.expand_query(
                query,
                num_variations=self.settings.AGENTIC_QUERY_EXPANSION_COUNT
            )
            queries = variations
            query_expansions = [v for v in variations if v != query]

        # 2. HyDE
        if enable_hyde:
            hypothetical_doc = await self.hyde_service.generate_hypothetical(query)
            if hypothetical_doc:
                queries.append(hypothetical_doc)

        # 3. 生成所有查询的向量
        query_vectors = await asyncio.gather(
            *[self.embedding_service.embed_text(q) for q in set(queries)]
        )

        # 4. 并行检索
        all_results = []
        for query_text, query_vector in zip(queries, query_vectors):
            results = await self.retrieval_engine.hybrid_retrieval(
                query=query_text,
                query_vector=query_vector,
                tenant_id=tenant_id,
                top_k=top_k * 2,
                search_type=search_type
            )
            all_results.extend(results)

        # 5. 去重合并
        merged = self._deduplicate_and_merge(all_results)

        # 6. 重排序
        if enable_rerank and merged:
            merged = await self.rerank_service.rerank(
                query=query,
                chunks=merged,
                top_k=top_k
            )

        # 7. 多步推理（可选）
        if enable_multi_step:
            return await self.retrieve_with_multi_step(
                query=query,
                query_vector=query_vectors[0],
                tenant_id=tenant_id,
                top_k=top_k,
                search_type=search_type
            )

        return RetrievalResult(
            results=merged[:top_k],
            query=query,
            iterations=1,
            query_expansions=query_expansions,
            hypothetical_doc=hypothetical_doc
        )

    async def retrieve_with_multi_step(
        self,
        query: str,
        query_vector: List[float],
        tenant_id: str,
        top_k: int = 10,
        max_iterations: int = 3,
        search_type: str = "balanced"
    ) -> RetrievalResult:
        """
        多步推理检索

        Args:
            query: 查询文本
            query_vector: 查询向量
            tenant_id: 租户 ID
            top_k: 返回结果数
            max_iterations: 最大迭代次数
            search_type: 检索类型

        Returns:
            检索结果
        """
        for iteration in range(1, max_iterations + 1):
            # 执行检索
            results = await self.retrieval_engine.hybrid_retrieval(
                query=query,
                query_vector=query_vector,
                tenant_id=tenant_id,
                top_k=top_k,
                search_type=search_type
            )

            if not results:
                return RetrievalResult(
                    results=[],
                    query=query,
                    iterations=iteration,
                    status="no_results"
                )

            # 质量评估
            quality = await self._assess_quality(query, results)

            if quality.is_satisfactory:
                return RetrievalResult(
                    results=results,
                    query=query,
                    iterations=iteration,
                    status="success"
                )

            # 调整策略
            if quality.issue == "low_relevance":
                # 使用不同关键词重新检索
                query = await self._rewrite_query(query, quality.feedback)
                query_vector = await self.embedding_service.embed_text(query)
            elif quality.issue == "insufficient_results":
                # 扩大检索范围（降低阈值）
                search_type = "semantic"  # 使用语义搜索扩大范围

        # 达到最大迭代次数
        return RetrievalResult(
            results=results,
            query=query,
            iterations=max_iterations,
            status="max_iterations_reached"
        )

    def _deduplicate_and_merge(self, chunks: List[Chunk]) -> List[Chunk]:
        """去重并合并结果"""
        seen_ids = set()
        seen_contents = {}
        deduped = []

        for chunk in chunks:
            if chunk.id in seen_ids:
                continue

            # 检查内容相似度
            is_duplicate = False
            content_lower = chunk.content.lower()

            for seen_id, seen_content in seen_contents.items():
                if self._content_similarity(content_lower, seen_content) > 0.95:
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduped.append(chunk)
                seen_ids.add(chunk.id)
                seen_contents[chunk.id] = content_lower

        return deduped

    def _content_similarity(self, content1: str, content2: str) -> float:
        """计算内容相似度"""
        # 简单实现：使用字符重叠
        set1 = set(content1)
        set2 = set(content2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0

    async def _assess_quality(self, query: str, results: List[Chunk]) -> QualityAssessment:
        """评估检索结果质量"""
        if not results:
            return QualityAssessment(
                is_satisfactory=False,
                issue="no_results",
                feedback="未找到相关结果"
            )

        # 检查平均相关性
        avg_score = sum(r.final_score or 0 for r in results) / len(results)

        if avg_score < 0.5:
            return QualityAssessment(
                is_satisfactory=False,
                issue="low_relevance",
                feedback="结果相关性较低，建议使用更精确的关键词"
            )

        if len(results) < 3:
            return QualityAssessment(
                is_satisfactory=False,
                issue="insufficient_results",
                feedback="结果数量不足"
            )

        return QualityAssessment(is_satisfactory=True)

    async def _rewrite_query(self, query: str, feedback: str) -> str:
        """根据反馈重写查询"""
        try:
            prompt = f"""根据以下反馈，重写查询以提高检索质量。

原始查询：{query}
反馈：{feedback}

重写后的查询："""

            llm_client = get_llm_client()
            response = await llm_client.generate(
                messages=[Message(role="user", content=prompt)],
                temperature=0.7
            )

            logger.info(f"Rewrote query: {query} -> {response}")
            return response.strip()

        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
            return query

    async def close(self):
        """关闭所有连接"""
        await self.retrieval_engine.close()
        await self.rerank_service.close()
        await self.embedding_service.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_controller.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/controller.py tests/test_rag/test_controller.py
git commit -m "feat(rag): add Agentic RAG controller with multi-step reasoning"
```

---

## Phase 4: 高级功能

### Task 4.1: 创建监控服务

**Files:**
- Create: `i3d_agent/rag/monitor.py`
- Test: `i3d_agent/tests/test_rag/test_monitor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_monitor.py
import pytest
from unittest.mock import patch, Mock
from i3d_agent.rag.monitor import MonitorService

@pytest.mark.asyncio
async def test_get_index_stats():
    """测试获取索引状态统计"""
    service = MonitorService()

    with patch.object(service, '_db_fetchrow') as mock_fetch:
        mock_fetch.return_value = {
            "total_documents": 100,
            "total_chunks": 500,
            "pending_index": 5,
            "failed_index": 2,
            "indexing_docs": 3
        }

        stats = await service.get_index_stats()

        assert stats["total_documents"] == 100
        assert stats["total_chunks"] == 500

@pytest.mark.asyncio
async def test_record_metric():
    """测试记录指标"""
    service = MonitorService()

    with patch.object(service, '_db_execute') as mock_execute:
        await service.record_metric(
            tenant_id="default",
            metric_name="rag检索延迟",
            value={"p50": 100, "p95": 200, "p99": 500}
        )

        mock_execute.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_monitor.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.monitor'"

- [ ] **Step 3: Create the monitor service**

```python
# i3d_agent/rag/monitor.py
"""Monitoring service for RAG performance and quality metrics."""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncpg
from i3d_agent.utils.logger import get_logger
from i3d_agent.config.settings import get_settings
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider

logger = get_logger(__name__)


class MonitorService:
    """监控服务 - 记录和查询 RAG 性能指标"""

    def __init__(self):
        self.settings = get_settings()
        self._pool = None

        # OpenTelemetry 指标
        self._setup_metrics()

    def _setup_metrics(self):
        """设置 OpenTelemetry 指标"""
        try:
            from opentelemetry import metrics
            meter = metrics.get_meter(__name__)

            self.rag_latency = meter.create_histogram(
                "rag检索延迟",
                description="RAG 检索请求处理时间",
                unit="ms"
            )

            self.rag_requests = meter.create_counter(
                "rag检索请求数",
                description="RAG 检索总请求数"
            )

            self.rag_empty_results = meter.create_counter(
                "rag空结果数",
                description="返回空结果的检索数"
            )

        except Exception as e:
            logger.warning(f"Failed to setup OpenTelemetry metrics: {e}")

    async def _get_pool(self) -> asyncpg.Pool:
        """获取数据库连接池"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.settings.DATABASE_URL)
        return self._pool

    async def get_index_stats(self) -> Dict[str, Any]:
        """获取索引状态统计"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # 总文档数
            total_documents = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_documents
                WHERE is_latest = true AND deleted_at IS NULL
            """)

            # 总 chunk 数
            total_chunks = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_chunks
                WHERE deleted_at IS NULL
            """)

            # 待处理索引
            pending_index = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_index_queue
                WHERE status = 'pending'
            """)

            # 失败索引
            failed_index = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_index_queue
                WHERE status = 'failed'
            """)

            # 正在索引中
            indexing_docs = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_documents
                WHERE status = 'indexing'
            """)

            # 平均 chunk 大小
            avg_chunk_size = await conn.fetchval("""
                SELECT AVG(token_count) FROM rag_chunks
                WHERE deleted_at IS NULL
            """)

            # 文档类型分布
            type_distribution = await conn.fetch("""
                SELECT doc_type, COUNT(*) as count
                FROM rag_documents
                WHERE is_latest = true AND deleted_at IS NULL
                GROUP BY doc_type
            """)

            return {
                "total_documents": total_documents or 0,
                "total_chunks": total_chunks or 0,
                "pending_index": pending_index or 0,
                "failed_index": failed_index or 0,
                "indexing_docs": indexing_docs or 0,
                "avg_chunk_size": int(avg_chunk_size) if avg_chunk_size else 0,
                "doc_type_distribution": {row['doc_type']: row['count'] for row in type_distribution}
            }

    async def record_metric(
        self,
        tenant_id: str,
        metric_name: str,
        value: Dict[str, Any],
        tags: Optional[Dict[str, Any]] = None
    ):
        """记录指标到数据库"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO rag_metrics (tenant_id, metric_name, metric_value, tags)
                VALUES ($1, $2, $3, $4)
            """, tenant_id, metric_name, value, tags or {})

    async def record_latency(self, tenant_id: str, latency_ms: float):
        """记录检索延迟"""
        if hasattr(self, 'rag_latency'):
            self.rag_latency.record(latency_ms, {"tenant_id": tenant_id})

    async def record_request(self, tenant_id: str, has_results: bool):
        """记录检索请求"""
        if hasattr(self, 'rag_requests'):
            self.rag_requests.add(1, {"tenant_id": tenant_id})

        if not has_results and hasattr(self, 'rag_empty_results'):
            self.rag_empty_results.add(1, {"tenant_id": tenant_id})

    async def get_metrics(
        self,
        tenant_id: str,
        metric_name: Optional[str] = None,
        time_range: str = "24h"
    ) -> list:
        """获取监控指标"""
        pool = await self._get_pool()

        # 解析时间范围
        time_delta = self._parse_time_range(time_range)
        since = datetime.now() - time_delta

        async with pool.acquire() as conn:
            conditions = ["timestamp >= $1"]
            params = [since]
            param_count = 1

            if tenant_id:
                param_count += 1
                conditions.append(f"tenant_id = ${param_count}")
                params.append(tenant_id)

            if metric_name:
                param_count += 1
                conditions.append(f"metric_name = ${param_count}")
                params.append(metric_name)

            query = f"""
                SELECT * FROM rag_metrics
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
                LIMIT 1000
            """

            rows = await conn.fetch(query, *params)

            return [dict(row) for row in rows]

    def _parse_time_range(self, time_range: str) -> timedelta:
        """解析时间范围"""
        units = {
            'h': 'hours',
            'd': 'days',
            'w': 'weeks'
        }

        for suffix, unit in units.items():
            if time_range.endswith(suffix):
                value = int(time_range[:-1])
                kwargs = {unit: value}
                return timedelta(**kwargs)

        return timedelta(hours=24)  # 默认 24 小时

    async def get_quality_metrics(self, tenant_id: str, days: int = 7) -> Dict[str, Any]:
        """获取质量指标"""
        pool = await self._get_pool()

        since = datetime.now() - timedelta(days=days)

        async with pool.acquire() as conn:
            # 平均评分
            avg_rating = await conn.fetchval("""
                SELECT AVG(rating) FROM rag_feedback
                WHERE tenant_id = $1 AND created_at >= $2 AND rating IS NOT NULL
            """, tenant_id, since)

            # 有用率
            helpful_count = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_feedback
                WHERE tenant_id = $1 AND created_at >= $2 AND is_helpful = true
            """, tenant_id, since)

            total_count = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_feedback
                WHERE tenant_id = $1 AND created_at >= $2
            """, tenant_id, since)

            helpful_rate = helpful_count / total_count if total_count > 0 else 0

            # 点赞率
            thumb_up_count = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_feedback
                WHERE tenant_id = $1 AND created_at >= $2 AND thumb_up = true
            """, tenant_id, since)

            thumb_up_rate = thumb_up_count / total_count if total_count > 0 else 0

            return {
                "avg_rating": float(avg_rating) if avg_rating else None,
                "helpful_rate": helpful_rate,
                "thumb_up_rate": thumb_up_rate,
                "total_feedbacks": total_count
            }

    async def save_feedback(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        retrieved_doc_ids: Optional[list],
        rating: Optional[int],
        is_helpful: Optional[bool],
        thumb_up: Optional[bool],
        feedback_text: Optional[str],
        answer: Optional[str],
        sources: Optional[dict]
    ):
        """保存质量反馈"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO rag_feedback (
                    tenant_id, session_id, query, retrieved_doc_ids,
                    rating, is_helpful, thumb_up, feedback_text, answer, sources
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, tenant_id, session_id, query, retrieved_doc_ids,
                 rating, is_helpful, thumb_up, feedback_text, answer, sources)

    async def close(self):
        """关闭连接"""
        if self._pool:
            await self._pool.close()
            self._pool = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag/test_monitor.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add i3d_agent/rag/monitor.py tests/test_rag/test_monitor.py
git commit -m "feat(rag): add monitoring service with OpenTelemetry integration"
```

---

### Task 4.2: 创建 RAG API 路由

**Files:**
- Create: `i3d_agent/rag/api.py`
- Test: `i3d_agent/tests/test_rag/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag/test_api.py
import pytest
from httpx import AsyncClient
from i3d_agent.api.main import create_app

@pytest.mark.asyncio
async def test_create_document():
    """测试创建文档 API"""
    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/rag/documents",
            json={
                "tenant_id": "default",
                "title": "Test Document",
                "content": "Test content",
                "doc_type": "technical"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Document"

@pytest.mark.asyncio
async def test_search():
    """测试检索 API"""
    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/rag/search",
            json={
                "query": "test query",
                "tenant_id": "default",
                "top_k": 10
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

@pytest.mark.asyncio
async def test_ask():
    """测试问答 API"""
    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/rag/ask",
            json={
                "question": "How to configure API?",
                "tenant_id": "default"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag/test_api.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'i3d_agent.rag.api'"

- [ ] **Step 3: Create the RAG API routes**

```python
# i3d_agent/rag/api.py
"""RAG API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from i3d_agent.rag.models import (
    DocumentCreate, DocumentUpdate, DocumentResponse,
    SearchRequest, AskRequest, FeedbackRequest
)
from i3d_agent.rag.document_manager import DocumentManager
from i3d_agent.rag.controller import AgenticRAGController
from i3d_agent.rag.monitor import MonitorService
from i3d_agent.rag.index_worker import IndexWorker
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


# ========== 依赖注入 ==========

async def get_document_manager() -> DocumentManager:
    """获取文档管理器实例"""
    return DocumentManager()


async def get_rag_controller() -> AgenticRAGController:
    """获取 RAG 控制器实例"""
    return AgenticRAGController()


async def get_monitor_service() -> MonitorService:
    """获取监控服务实例"""
    return MonitorService()


# ========== 文档管理 API ==========

@router.post("/documents", response_model=DocumentResponse)
async def create_document(
    request: DocumentCreate,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """创建新文档"""
    try:
        doc = await document_manager.create_document(
            tenant_id=request.tenant_id,
            title=request.title,
            content=request.content,
            doc_type=request.doc_type,
            source_type=request.source_type,
            description=request.description,
            metadata=request.metadata,
            tags=request.tags,
            language=request.language
        )
        return doc
    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """获取文档详情"""
    doc = await document_manager.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    request: DocumentUpdate,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """更新文档"""
    try:
        doc = await document_manager.update_document(
            doc_id=doc_id,
            content=request.content,
            title=request.title,
            description=request.description,
            metadata=request.metadata,
            tags=request.tags
        )
        return doc
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    hard_delete: bool = False,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """删除文档"""
    try:
        await document_manager.delete_document(doc_id, hard_delete=hard_delete)
        return {"message": "Document deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{doc_id}/restore", response_model=DocumentResponse)
async def restore_document(
    doc_id: str,
    version: Optional[int] = None,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """恢复文档"""
    try:
        doc = await document_manager.restore_document(doc_id, version)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}/history")
async def get_document_history(
    doc_id: str,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """获取文档版本历史"""
    try:
        history = await document_manager.get_document_history(doc_id)
        return {"history": history}
    except Exception as e:
        logger.error(f"Failed to get document history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents(
    tenant_id: str,
    doc_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """列出文档（分页）"""
    try:
        result = await document_manager.list_documents(
            tenant_id=tenant_id,
            doc_type=doc_type,
            page=page,
            page_size=page_size
        )
        return result
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 检索与问答 API ==========

@router.post("/search")
async def search(
    request: SearchRequest,
    rag_controller: AgenticRAGController = Depends(get_rag_controller)
):
    """检索接口（返回文档片段）"""
    try:
        from i3d_agent.rag.embedding import EmbeddingService
        embedding_service = EmbeddingService()

        # 生成查询向量
        query_vector = await embedding_service.embed_text(request.query)

        # 执行检索
        result = await rag_controller.retrieve(
            query=request.query,
            tenant_id=request.tenant_id,
            top_k=request.top_k,
            enable_expansion=request.enable_expansion,
            enable_hyde=request.enable_hyde,
            enable_rerank=request.enable_rerank,
            search_type=request.search_type
        )

        return {
            "query": result.query,
            "results": [
                {
                    "chunk_id": r.id,
                    "doc_id": r.doc_id,
                    "content": r.content,
                    "score": r.final_score,
                    "metadata": r.metadata
                }
                for r in result.results
            ],
            "total": len(result.results),
            "iterations": result.iterations,
            "query_expansions": result.query_expansions
        }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask")
async def ask(
    request: AskRequest,
    rag_controller: AgenticRAGController = Depends(get_rag_controller)
):
    """RAG 问答（返回完整答案）"""
    try:
        from i3d_agent.rag.embedding import EmbeddingService
        embedding_service = EmbeddingService()

        # 生成查询向量
        query_vector = await embedding_service.embed_text(request.question)

        # 执行检索
        result = await rag_controller.retrieve(
            query=request.question,
            tenant_id=request.tenant_id,
            top_k=request.top_k,
            enable_expansion=True,
            enable_hyde=True,
            enable_rerank=True,
            enable_multi_step=request.enable_multi_step
        )

        if not result.results:
            return {
                "question": request.question,
                "answer": "抱歉，知识库中没有找到相关文档。",
                "sources": [],
                "status": "no_results"
            }

        # 构建上下文
        context_parts = []
        for i, r in enumerate(result.results, 1):
            title = r.metadata.get("title", "Unknown")
            content = r.content
            score = r.final_score or 0
            context_parts.append(f"[文档 {i}] {title} (相关度: {score:.2f})\n{content}")

        context = "\n\n".join(context_parts)

        # 生成答案
        from i3d_agent.llm import get_llm_client, Message

        system_prompt = """你是一个技术文档助手，专门回答关于 3D CAD 系统、搜索服务、部署和故障排查的问题。

请根据提供的文档上下文回答用户问题。如果文档中没有相关信息，请诚实地说明。

回答要求：
1. 准确、简洁、专业
2. 引用相关的文档来源
3. 如果需要步骤，请按顺序列出
4. 使用中文回答"""

        user_prompt = f"""问题: {request.question}

相关文档:
{context}

请根据上述文档回答问题。"""

        llm_client = get_llm_client()
        answer = await llm_client.generate(
            messages=[Message(role="user", content=user_prompt)],
            system_prompt=system_prompt,
            temperature=0.7
        )

        return {
            "question": request.question,
            "answer": answer,
            "sources": [
                {
                    "doc_id": r.doc_id,
                    "title": r.metadata.get("title", "Unknown"),
                    "score": r.final_score
                }
                for r in result.results[:3]
            ],
            "status": "success",
            "metadata": {
                "iterations": result.iterations,
                "num_retrieved": len(result.results)
            }
        }

    except Exception as e:
        logger.error(f"Ask failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 监控 API ==========

@router.get("/index/status")
async def get_index_status(
    tenant_id: str,
    monitor: MonitorService = Depends(get_monitor_service)
):
    """获取索引状态"""
    try:
        stats = await monitor.get_index_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get index status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/queue")
async def get_index_queue(
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = 50
):
    """获取索引队列"""
    try:
        from i3d_agent.config.settings import get_settings
        settings = get_settings()
        pool = await (await DocumentManager()._get_pool()).acquire()

        conditions = ["tenant_id = $1"]
        params = [tenant_id]
        param_count = 1

        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status)

        query = f"""
            SELECT id, doc_id, operation, status, priority,
                   retry_count, error_message, created_at, started_at
            FROM rag_index_queue
            WHERE {' AND '.join(conditions)}
            ORDER BY priority DESC, created_at ASC
            LIMIT ${param_count + 1}
        """
        params.append(limit)

        rows = await pool.fetch(query, *params)
        return {"tasks": [dict(row) for row in rows]}

    except Exception as e:
        logger.error(f"Failed to get index queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_metrics(
    tenant_id: str,
    metric_name: Optional[str] = None,
    time_range: str = "24h",
    monitor: MonitorService = Depends(get_monitor_service)
):
    """获取监控指标"""
    try:
        metrics = await monitor.get_metrics(tenant_id, metric_name, time_range)
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality")
async def get_quality_metrics(
    tenant_id: str,
    days: int = 7,
    monitor: MonitorService = Depends(get_monitor_service)
):
    """获取质量指标"""
    try:
        metrics = await monitor.get_quality_metrics(tenant_id, days)
        return metrics
    except Exception as e:
        logger.error(f"Failed to get quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    monitor: MonitorService = Depends(get_monitor_service)
):
    """提交质量反馈"""
    try:
        await monitor.save_feedback(
            tenant_id="default",  # TODO: 从请求中获取
            session_id=request.session_id,
            query=request.query,
            retrieved_doc_ids=request.retrieved_doc_ids,
            rating=request.rating,
            is_helpful=request.is_helpful,
            thumb_up=request.thumb_up,
            feedback_text=request.feedback_text,
            answer=None,
            sources=None
        )
        return {"message": "Feedback recorded successfully"}
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Update main app to include RAG router**

```python
# i3d_agent/api/main.py - 更新
# 在现有路由后添加：
from i3d_agent.rag.api import router as rag_router

app.include_router(rag_router)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_rag/test_api.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add i3d_agent/rag/api.py i3d_agent/api/main.py tests/test_rag/test_api.py
git commit -m "feat(rag): add RAG API routes"
```

---

### Task 4.3: 更新配置文件

**Files:**
- Modify: `i3d_agent/config/settings.py`

- [ ] **Step 1: Add RAG configuration settings**

```python
# i3d_agent/config/settings.py - 添加到 Settings 类

# ========== RAG 配置 ==========

# 文档存储路径
RAG_DATA_PATH: str = Field(default="./data/rag", description="RAG 数据目录")
RAG_DOCUMENTS_PATH: str = Field(default="./data/rag/documents", description="文档存储路径")

# 切分配置
CHUNK_SIZE_DEFAULT: int = Field(default=800, description="默认 chunk 大小")
CHUNK_OVERLAP_DEFAULT: int = Field(default=150, description="默认 overlap 大小")

# 检索配置
RAG_TOP_K_RESULTS: int = Field(default=10, description="检索返回结果数")
RAG_SIMILARITY_THRESHOLD: float = Field(default=0.7, description="相似度阈值")
RAG_RERANK_TOP_K: int = Field(default=5, description="重排序后保留结果数")

# 混合检索权重
HYBRID_ALPHA_SEMANTIC: float = Field(default=0.7, description="语义检索权重")
HYBRID_ALPHA_KEYWORD: float = Field(default=0.3, description="关键词检索权重")
HYBRID_ALPHA_EXACT: float = Field(default=0.1, description="精确匹配权重")

# Agentic 配置
AGENTIC_QUERY_EXPANSION_COUNT: int = Field(default=3, description="查询扩展数量")
AGENTIC_MAX_ITERATIONS: int = Field(default=3, description="多步推理最大迭代次数")
AGENTIC_ENABLE_HYDE: bool = Field(default=True, description="启用 HyDE")
AGENTIC_ENABLE_RERANK: bool = Field(default=True, description="启用重排序")

# Rerank 配置
RERANK_PROVIDER: str = Field(default="cohere", description="Rerank 服务提供商")
RERANK_MODEL: str = Field(default="rerank-english-v2.0", description="Rerank 模型")
COHERE_API_KEY: str = Field(default="", description="Cohere API Key")

# 索引配置
INDEX_BATCH_SIZE: int = Field(default=10, description="索引批处理大小")
INDEX_WORKER_CONCURRENCY: int = Field(default=2, description="索引 Worker 并发数")
```

- [ ] **Step 2: Update .env.example**

```bash
# .env.example - 添加

# ========== RAG Configuration ==========
RAG_DATA_PATH=./data/rag
CHUNK_SIZE_DEFAULT=800
RAG_TOP_K_RESULTS=10
RERANK_PROVIDER=cohere
COHERE_API_KEY=your-cohere-api-key
```

- [ ] **Step 3: Commit**

```bash
git add i3d_agent/config/settings.py .env.example
git commit -m "feat(rag): add RAG configuration settings"
```

---

### Task 4.4: 更新依赖文件

**Files:**
- Modify: `requirements.txt` 或 `pyproject.toml`

- [ ] **Step 1: Add RAG dependencies**

```txt
# requirements.txt - 添加

# RAG 相关
cohere>=4.0
rank-bm25>=0.2.3
unstructured>=0.10.0
python-magic>=0.4.27
pikepdf>=8.0.0

# 任务队列（可选）
celery>=5.3.0
```

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "feat(rag): add RAG dependencies"
```

---

### Task 4.5: 更新 RAG tools

**Files:**
- Modify: `i3d_agent/tools/rag_tools.py`

- [ ] **Step 1: Update RAG tools to use new module**

```python
# i3d_agent/tools/rag_tools.py - 更新
"""RAG (Retrieval-Augmented Generation) tools for i3d-agent-system.

These tools now integrate with the full RAG module.
"""

from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

from i3d_agent.rag.document_manager import DocumentManager
from i3d_agent.rag.controller import AgenticRAGController


@tool
def retrieve_documents(
    query: str,
    knowledge_base: str = "default",
    top_k: int = 10,
    tenant_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve technical documents from the RAG knowledge base.

    Now uses the full Agentic RAG capabilities.
    """
    import asyncio

    async def _retrieve():
        controller = AgenticRAGController()
        result = await controller.retrieve(
            query=query,
            tenant_id=tenant_id or knowledge_base,
            top_k=top_k,
            enable_expansion=True,
            enable_hyde=True,
            enable_rerank=True
        )
        await controller.close()
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
```

- [ ] **Step 2: Commit**

```bash
git add i3d_agent/tools/rag_tools.py
git commit -m "feat(rag): update RAG tools to use new module"
```

---

## Phase 5: 完成与验证

### Task 5.1: 创建集成测试

**Files:**
- Create: `i3d_agent/tests/test_rag/integration_test.py`

- [ ] **Step 1: Create integration test**

```python
# tests/test_rag/integration_test.py
"""Integration tests for RAG module."""

import pytest
import asyncio
from i3d_agent.rag.document_manager import DocumentManager
from i3d_agent.rag.controller import AgenticRAGController
from i3d_agent.rag.monitor import MonitorService
from i3d_agent.rag.index_worker import IndexWorker


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_rag_workflow():
    """测试完整的 RAG 工作流"""
    # 1. 创建文档
    manager = DocumentManager()
    doc = await manager.create_document(
        tenant_id="test",
        title="Test API Document",
        content="# API Reference\n\n## GET /api/test\n\nThis is a test endpoint.",
        doc_type="technical",
        source_type="md"
    )

    # 2. 等待索引完成
    worker = IndexWorker()
    # 模拟处理队列
    await asyncio.sleep(1)

    # 3. 执行检索
    controller = AgenticRAGController()
    result = await controller.retrieve(
        query="test endpoint",
        tenant_id="test",
        top_k=5
    )

    # 4. 验证结果
    assert len(result.results) > 0
    assert any("test" in r.content.lower() for r in result.results)

    # 清理
    await manager.delete_document(doc.id)
    await manager.close()
    await controller.close()
    await worker.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agentic_rag_features():
    """测试 Agentic RAG 特性"""
    controller = AgenticRAGController()

    # 测试查询扩展
    result = await controller.retrieve(
        query="如何配置 API？",
        tenant_id="test",
        enable_expansion=True,
        enable_hyde=True,
        top_k=5
    )

    assert result.query_expansions is not None
    assert len(result.query_expansions) >= 0

    await controller.close()
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_rag/integration_test.py
git commit -m "test(rag): add integration tests"
```

---

### Task 5.2: 创建启动脚本

**Files:**
- Create: `scripts/run_rag_worker.py`

- [ ] **Step 1: Create RAG worker startup script**

```python
#!/usr/bin/env python3
"""RAG Index Worker startup script."""

import asyncio
import sys
from i3d_agent.rag.index_worker import IndexWorker
from i3d_agent.config.settings import get_settings
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """主函数"""
    settings = get_settings()

    logger.info("Starting RAG Index Worker...")
    logger.info(f"Concurrency: {settings.INDEX_WORKER_CONCURRENCY}")

    worker = IndexWorker()

    try:
        await worker.run_worker(concurrency=settings.INDEX_WORKER_CONCURRENCY)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        worker.stop_worker()
        await worker.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add scripts/run_rag_worker.py
git commit -m "feat(rag): add RAG worker startup script"
```

---

### Task 5.3: 更新 Docker 配置

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add RAG worker service**

```yaml
# docker-compose.yml - 添加

services:
  # ... 现有服务 ...

  rag-worker:
    build: .
    command: python scripts/run_rag_worker.py
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - DEFAULT_LLM_PROVIDER=${DEFAULT_LLM_PROVIDER}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(rag): add RAG worker service to docker-compose"
```

---

### Task 5.4: 创建 README 文档

**Files:**
- Create: `docs/RAG_MODULE.md`

- [ ] **Step 1: Create RAG module documentation**

```markdown
# RAG Module Documentation

## Overview

The RAG (Retrieval-Augmented Generation) module provides intelligent document search and Q&A capabilities.

## Features

- **Document Management**: Upload, update, delete with version control
- **Incremental Indexing**: Async worker processes new documents
- **Hybrid Retrieval**: Vector search + BM25 full-text search
- **Agentic RAG**: Query expansion, HyDE, reranking, multi-step reasoning
- **Monitoring**: Performance metrics and quality feedback

## Quick Start

### 1. Run Database Migration

\`\`\`bash
psql -U postgres -d i3d_agent -f migrations/versions/002_add_rag_tables.sql
\`\`\`

### 2. Start Index Worker

\`\`\`bash
python scripts/run_rag_worker.py
\`\`\`

### 3. Upload a Document

\`\`\`bash
curl -X POST http://localhost:8000/api/v1/rag/documents \\
  -H "Content-Type: application/json" \\
  -d '{
    "tenant_id": "default",
    "title": "API Documentation",
    "content": "# API Reference\\n\\n## GET /api/test",
    "doc_type": "technical"
  }'
\`\`\`

### 4. Search

\`\`\`bash
curl -X POST http://localhost:8000/api/v1/rag/search \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "API endpoint",
    "tenant_id": "default"
  }'
\`\`\`

## API Reference

See [API Documentation](../docs/superpowers/specs/2026-06-01-rag-module-design.md) for details.
```

- [ ] **Step 2: Commit**

```bash
git add docs/RAG_MODULE.md
git commit -m "docs(rag): add RAG module documentation"
```

---

## 实施完成检查

### 验证所有任务完成

- [ ] Phase 1: 基础设施（7 个任务）
- [ ] Phase 2: 核心检索（3 个任务）
- [ ] Phase 3: Agentic 特性（3 个任务）
- [ ] Phase 4: 高级功能（5 个任务）
- [ ] Phase 5: 完成与验证（4 个任务）

### 运行完整测试套件

\`\`\`bash
pytest tests/test_rag/ -v
pytest tests/test_agents/test_rag.py -v
\`\`\`

### 验证部署

\`\`\`bash
# 启动服务
docker-compose up -d

# 验证健康检查
curl http://localhost:8000/health

# 测试 RAG API
curl -X POST http://localhost:8000/api/v1/rag/search \\
  -H "Content-Type: application/json" \\
  -d '{"query": "test", "tenant_id": "default"}'
\`\`\`

---

*实施计划结束*

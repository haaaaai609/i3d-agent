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
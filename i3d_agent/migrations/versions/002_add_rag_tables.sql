-- ============================================================================
-- i3d-agent-system RAG Module Migration
-- ============================================================================
-- This migration creates comprehensive RAG module tables, replacing the
-- simple rag_documents table from the initial migration.
--
-- BREAKING CHANGE: This migration drops and recreates the rag_documents table
-- with a completely new schema that supports:
-- - Version control and document history
-- - Document metadata tracking
-- - Incremental indexing
-- - Multiple chunk versions
-- - Separate tables for chunks, versions, index queue, metrics, and feedback
--
-- Requirements:
-- - PostgreSQL 15+ with pgvector extension
-- - All tables support multi-tenancy via tenant_id column
-- - Row-Level Security (RLS) enabled on all tables
-- - Vector columns use 1536 dimensions for local gte-Qwen2-1.5B-instruct embeddings
-- ============================================================================

-- ============================================================================
-- SECTION 1: Drop Existing RAG Objects
-- ============================================================================
-- This section drops all objects related to the old rag_documents table
-- to allow recreation with the new schema.
--
-- Objects being dropped:
-- - Table: rag_documents (with old schema: BIGSERIAL id, VECTOR(512), document_id, chunk_id)
-- - Indexes: All indexes on rag_documents
-- - Trigger: trigger_rag_documents_updated_at
-- - Policy: rag_documents_tenant_policy
-- ============================================================================

-- Drop trigger (if exists)
DROP TRIGGER IF EXISTS trigger_rag_documents_updated_at ON rag_documents;

-- Drop RLS policy (if exists)
DROP POLICY IF EXISTS rag_documents_tenant_policy ON rag_documents;

-- Drop indexes (PostgreSQL automatically drops indexes when table is dropped, but we list them for documentation)
-- The following indexes will be automatically dropped:
-- - idx_rag_documents_content_vector_hnsw (HNSW vector index)
-- - idx_rag_documents_tenant_document (B-tree index)
-- - idx_rag_documents_agent_id (B-tree index)
-- - idx_rag_documents_source_type (B-tree index)
-- - idx_rag_documents_metadata (GIN index)

-- Drop the old rag_documents table
DROP TABLE IF EXISTS rag_documents CASCADE;

-- ============================================================================
-- SECTION 2: Create RAG Module Tables
-- ============================================================================

-- ============================================================================
-- rag_documents: Document metadata table with version control
-- ============================================================================
CREATE TABLE rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,

    -- Basic information
    title VARCHAR(500) NOT NULL,
    description TEXT,
    doc_type VARCHAR(50) NOT NULL,
    source_type VARCHAR(50),

    -- Content
    raw_content TEXT,
    content_hash VARCHAR(64),

    -- Version control
    version INT NOT NULL DEFAULT 1,
    is_latest BOOLEAN DEFAULT true,
    parent_doc_id UUID,

    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    language VARCHAR(10) DEFAULT 'zh',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_rag_doc_parent FOREIGN KEY (parent_doc_id)
        REFERENCES rag_documents(id) ON DELETE SET NULL,

    -- Check constraints
    CONSTRAINT chk_rag_doc_type CHECK (doc_type IN ('technical', 'business', 'api')),
    CONSTRAINT chk_rag_doc_status CHECK (status IN ('pending', 'indexing', 'ready', 'failed')),
    CONSTRAINT chk_rag_doc_version CHECK (version > 0)
);

-- Document table indexes
CREATE INDEX idx_rag_docs_tenant_latest ON rag_documents(tenant_id, is_latest) WHERE deleted_at IS NULL;
CREATE INDEX idx_rag_docs_type ON rag_documents(doc_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_rag_docs_tags ON rag_documents USING GIN(tags);
CREATE INDEX idx_rag_docs_hash ON rag_documents(content_hash);
CREATE INDEX idx_rag_docs_parent ON rag_documents(parent_doc_id) WHERE parent_doc_id IS NOT NULL;

-- ============================================================================
-- rag_chunks: Document chunks with embeddings
-- ============================================================================
CREATE TABLE rag_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL,
    tenant_id TEXT NOT NULL,

    -- Content
    content TEXT NOT NULL,
    embedding vector(1536),

    -- Full-text search
    content_tsv tsvector GENERATED ALWAYS AS
        (to_tsvector('simple', coalesce(content, ''))) STORED,

    -- Metadata
    chunk_index INT NOT NULL,
    token_count INT,
    metadata JSONB DEFAULT '{}',

    -- Version association
    doc_version INT NOT NULL,

    -- Status
    deleted_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- Foreign key constraint
    CONSTRAINT fk_rag_chunk_doc FOREIGN KEY (doc_id)
        REFERENCES rag_documents(id) ON DELETE CASCADE,

    -- Unique constraint
    CONSTRAINT uq_rag_chunk_version UNIQUE(doc_id, chunk_index, doc_version),

    -- Check constraints
    CONSTRAINT chk_rag_chunk_index CHECK (chunk_index >= 0),
    CONSTRAINT chk_rag_chunk_tokens CHECK (token_count IS NULL OR token_count > 0)
);

-- Vector index (HNSW)
CREATE INDEX idx_rag_chunks_embedding
ON rag_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text index
CREATE INDEX idx_rag_chunks_tsv
ON rag_chunks USING gin (content_tsv);

-- Tenant index
CREATE INDEX idx_rag_chunks_tenant
ON rag_chunks(tenant_id) WHERE deleted_at IS NULL;

-- Document association index
CREATE INDEX idx_rag_chunks_doc
ON rag_chunks(doc_id, doc_version) WHERE deleted_at IS NULL;

-- ============================================================================
-- rag_versions: Version history table
-- ============================================================================
CREATE TABLE rag_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL,
    tenant_id TEXT NOT NULL,

    -- Version information
    version INT NOT NULL,

    -- Snapshot
    content_snapshot TEXT,
    chunk_count INT,

    -- Change description
    change_type VARCHAR(20),
    change_reason TEXT,
    changed_by VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- Foreign key constraint
    CONSTRAINT fk_rag_version_doc FOREIGN KEY (doc_id)
        REFERENCES rag_documents(id) ON DELETE CASCADE,

    -- Check constraints
    CONSTRAINT chk_rag_version_type CHECK (change_type IN ('create', 'update', 'delete', 'restore'))
);

-- Version indexes
CREATE INDEX idx_rag_versions_doc ON rag_versions(doc_id, version);
CREATE INDEX idx_rag_versions_tenant ON rag_versions(tenant_id);

-- ============================================================================
-- rag_index_queue: Index queue for async processing
-- ============================================================================
CREATE TABLE rag_index_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL,
    tenant_id TEXT NOT NULL,

    -- Task information
    status VARCHAR(20) DEFAULT 'pending',
    operation VARCHAR(20) NOT NULL,
    priority INT DEFAULT 5,

    -- Retry logic
    retry_count INT DEFAULT 0,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_rag_queue_doc FOREIGN KEY (doc_id)
        REFERENCES rag_documents(id) ON DELETE CASCADE,

    -- Check constraints
    CONSTRAINT chk_rag_queue_status CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    CONSTRAINT chk_rag_queue_operation CHECK (operation IN ('create', 'update', 'delete')),
    CONSTRAINT chk_rag_queue_priority CHECK (priority BETWEEN 0 AND 9),
    CONSTRAINT chk_rag_queue_retry CHECK (retry_count >= 0)
);

-- Queue indexes
CREATE INDEX idx_rag_queue_status ON rag_index_queue(status, priority, created_at)
    WHERE status IN ('pending', 'processing');
CREATE INDEX idx_rag_queue_doc ON rag_index_queue(doc_id);
CREATE INDEX idx_rag_queue_tenant ON rag_index_queue(tenant_id);

-- ============================================================================
-- rag_metrics: Monitoring metrics table
-- ============================================================================
CREATE TABLE rag_metrics (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT,
    metric_name VARCHAR(100) NOT NULL,
    metric_value JSONB NOT NULL,
    tags JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Metric indexes
CREATE INDEX idx_rag_metrics_name ON rag_metrics(metric_name, timestamp DESC);
CREATE INDEX idx_rag_metrics_tenant ON rag_metrics(tenant_id, timestamp DESC);

-- ============================================================================
-- rag_feedback: Quality feedback table
-- ============================================================================
CREATE TABLE rag_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,

    -- Association information
    session_id VARCHAR(100),
    query TEXT NOT NULL,
    retrieved_doc_ids UUID[],

    -- Feedback information
    rating INT CHECK (rating BETWEEN 1 AND 5),
    is_helpful BOOLEAN,
    thumb_up BOOLEAN,
    feedback_text TEXT,

    -- Reasoning chain
    answer TEXT,
    sources JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- Feedback indexes
CREATE INDEX idx_rag_feedback_tenant ON rag_feedback(tenant_id, created_at DESC);
CREATE INDEX idx_rag_feedback_session ON rag_feedback(session_id, created_at);

-- ============================================================================
-- SECTION 3: Row Level Security (RLS) - Tenant Isolation
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE rag_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_index_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_feedback ENABLE ROW LEVEL SECURITY;

-- Create RLS policies with WITH CHECK clause for security
CREATE POLICY rag_documents_tenant_policy ON rag_documents
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY rag_chunks_tenant_policy ON rag_chunks
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY rag_versions_tenant_policy ON rag_versions
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY rag_index_queue_tenant_policy ON rag_index_queue
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY rag_metrics_tenant_policy ON rag_metrics
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY rag_feedback_tenant_policy ON rag_feedback
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- SECTION 4: Triggers
-- ============================================================================

-- Reuse existing trigger function for automatic updated_at timestamp
CREATE TRIGGER update_rag_documents_updated_at
    BEFORE UPDATE ON rag_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SECTION 5: Migration Completion
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'RAG module tables created successfully';
    RAISE NOTICE 'Tables created: 6 (rag_documents, rag_chunks, rag_versions, rag_index_queue, rag_metrics, rag_feedback)';
    RAISE NOTICE 'Indexes created: 19 (including HNSW vector index and GIN indexes)';
    RAISE NOTICE 'RLS policies created: 6 (one per table with WITH CHECK clause)';
    RAISE NOTICE 'Triggers created: 1 (reusing existing update_updated_at_column function)';
END $$;

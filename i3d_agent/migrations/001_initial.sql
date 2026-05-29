-- ============================================================================
-- i3d-agent-system Initial Database Schema
-- ============================================================================
-- This migration creates the initial database schema for the Agent system
-- with support for multi-tenancy, vector search, and RAG capabilities.
--
-- Requirements:
-- - PostgreSQL 15+ with pgvector extension
-- - All tables support multi-tenancy via tenant_id column
-- - Row-Level Security (RLS) enabled on all tables
-- - Vector columns use 512 dimensions for embeddings
-- ============================================================================

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Utility Functions and Types
-- ============================================================================

-- Create trigger function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Agent Semantic Memory Table
-- Stores long-term semantic memories for agents with vector similarity search
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_semantic_memory (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    memory_key TEXT NOT NULL,
    content TEXT NOT NULL,
    content_vector VECTOR(512),
    memory_type TEXT NOT NULL CHECK (memory_type IN ('fact', 'preference', 'context', 'skill')),
    importance_score DECIMAL(3, 2) DEFAULT 0.5 CHECK (importance_score >= 0 AND importance_score <= 1),
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create HNSW index for vector similarity search on content_vector
CREATE INDEX idx_agent_semantic_memory_content_vector_hnsw
ON agent_semantic_memory
USING hnsw (content_vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create index for tenant_id and agent_id lookups
CREATE INDEX idx_agent_semantic_memory_tenant_agent
ON agent_semantic_memory(tenant_id, agent_id);

-- Create index for memory_type lookups
CREATE INDEX idx_agent_semantic_memory_memory_type
ON agent_semantic_memory(memory_type);

-- Create GIN index for metadata queries
CREATE INDEX idx_agent_semantic_memory_metadata
ON agent_semantic_memory USING gin (metadata);

-- Create trigger for automatic updated_at
CREATE TRIGGER trigger_agent_semantic_memory_updated_at
BEFORE UPDATE ON agent_semantic_memory
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Enable Row-Level Security
ALTER TABLE agent_semantic_memory ENABLE ROW LEVEL SECURITY;

-- Create RLS policy: Users can only access records for their tenant
CREATE POLICY agent_semantic_memory_tenant_policy ON agent_semantic_memory
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true))
WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- Agent Conversation History Table
-- Stores conversation history between users and agents
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_conversation_history (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    user_id TEXT,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB DEFAULT '[]'::jsonb,
    tool_outputs JSONB DEFAULT '[]'::jsonb,
    tokens_used INTEGER DEFAULT 0,
    model_name TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for tenant_id and session_id lookups
CREATE INDEX idx_agent_conversation_history_tenant_session
ON agent_conversation_history(tenant_id, session_id);

-- Create index for agent_id lookups
CREATE INDEX idx_agent_conversation_history_agent_id
ON agent_conversation_history(agent_id);

-- Create index for user_id lookups
CREATE INDEX idx_agent_conversation_history_user_id
ON agent_conversation_history(user_id);

-- Create index for time-based queries
CREATE INDEX idx_agent_conversation_history_created_at
ON agent_conversation_history(created_at DESC);

-- Create GIN index for metadata queries
CREATE INDEX idx_agent_conversation_history_metadata
ON agent_conversation_history USING gin (metadata);

-- Create trigger for automatic updated_at
CREATE TRIGGER trigger_agent_conversation_history_updated_at
BEFORE UPDATE ON agent_conversation_history
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Enable Row-Level Security
ALTER TABLE agent_conversation_history ENABLE ROW LEVEL SECURITY;

-- Create RLS policy: Users can only access records for their tenant
CREATE POLICY agent_conversation_history_tenant_policy ON agent_conversation_history
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true))
WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- Agent Tasks Table
-- Stores tasks assigned to agents with their execution status
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_tasks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    user_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT NOT NULL CHECK (task_type IN ('query', 'action', 'analysis', 'generation', 'workflow')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_duration_seconds INTEGER,
    actual_duration_seconds INTEGER,
    parent_task_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT agent_tasks_task_id_tenant_id_key UNIQUE (task_id, tenant_id)
);

-- Create index for tenant_id and task_id lookups
CREATE INDEX idx_agent_tasks_tenant_task
ON agent_tasks(tenant_id, task_id);

-- Create index for agent_id lookups
CREATE INDEX idx_agent_tasks_agent_id
ON agent_tasks(agent_id);

-- Create index for user_id lookups
CREATE INDEX idx_agent_tasks_user_id
ON agent_tasks(user_id);

-- Create index for status queries
CREATE INDEX idx_agent_tasks_status
ON agent_tasks(status);

-- Create index for priority-based queries
CREATE INDEX idx_agent_tasks_priority
ON agent_tasks(priority);

-- Create index for parent_task_id lookups
CREATE INDEX idx_agent_tasks_parent_task_id
ON agent_tasks(parent_task_id);

-- Create index for time-based queries
CREATE INDEX idx_agent_tasks_created_at
ON agent_tasks(created_at DESC);

-- Create GIN index for metadata queries
CREATE INDEX idx_agent_tasks_metadata
ON agent_tasks USING gin (metadata);

-- Create GIN index for input_data queries
CREATE INDEX idx_agent_tasks_input_data
ON agent_tasks USING gin (input_data);

-- Create trigger for automatic updated_at
CREATE TRIGGER trigger_agent_tasks_updated_at
BEFORE UPDATE ON agent_tasks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Enable Row-Level Security
ALTER TABLE agent_tasks ENABLE ROW LEVEL SECURITY;

-- Create RLS policy: Users can only access records for their tenant
CREATE POLICY agent_tasks_tenant_policy ON agent_tasks
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true))
WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- RAG Documents Table
-- Stores documents for Retrieval-Augmented Generation with vector search
-- ============================================================================
CREATE TABLE IF NOT EXISTS rag_documents (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    chunk_id INTEGER NOT NULL,
    agent_id TEXT,
    title TEXT,
    content TEXT NOT NULL,
    content_vector VECTOR(512),
    source_type TEXT NOT NULL CHECK (source_type IN ('file', 'url', 'database', 'api', 'manual')),
    source_uri TEXT,
    document_type TEXT CHECK (document_type IN ('pdf', 'txt', 'md', 'html', 'docx', 'json', 'csv', 'other')),
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding_model TEXT,
    token_count INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT rag_documents_document_chunk_key UNIQUE (document_id, chunk_id, tenant_id)
);

-- Create HNSW index for vector similarity search on content_vector
CREATE INDEX idx_rag_documents_content_vector_hnsw
ON rag_documents
USING hnsw (content_vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create index for tenant_id and document_id lookups
CREATE INDEX idx_rag_documents_tenant_document
ON rag_documents(tenant_id, document_id);

-- Create index for agent_id lookups
CREATE INDEX idx_rag_documents_agent_id
ON rag_documents(agent_id);

-- Create index for source_type queries
CREATE INDEX idx_rag_documents_source_type
ON rag_documents(source_type);

-- Create GIN index for metadata queries
CREATE INDEX idx_rag_documents_metadata
ON rag_documents USING gin (metadata);

-- Create trigger for automatic updated_at
CREATE TRIGGER trigger_rag_documents_updated_at
BEFORE UPDATE ON rag_documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Enable Row-Level Security
ALTER TABLE rag_documents ENABLE ROW LEVEL SECURITY;

-- Create RLS policy: Users can only access records for their tenant
CREATE POLICY rag_documents_tenant_policy ON rag_documents
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true))
WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- Agent Feedback Table
-- Stores user feedback on agent responses for continuous improvement
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_feedback (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    user_id TEXT,
    conversation_message_id BIGINT,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('thumbs_up', 'thumbs_down', 'flag', 'rating', 'comment')),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    feedback_tags JSONB DEFAULT '[]'::jsonb,
    issue_category TEXT CHECK (issue_category IN ('accuracy', 'relevance', 'safety', 'clarity', 'other')),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for tenant_id and session_id lookups
CREATE INDEX idx_agent_feedback_tenant_session
ON agent_feedback(tenant_id, session_id);

-- Create index for agent_id lookups
CREATE INDEX idx_agent_feedback_agent_id
ON agent_feedback(agent_id);

-- Create index for user_id lookups
CREATE INDEX idx_agent_feedback_user_id
ON agent_feedback(user_id);

-- Create index for conversation_message_id lookups
CREATE INDEX idx_agent_feedback_conversation_message_id
ON agent_feedback(conversation_message_id);

-- Create index for feedback_type queries
CREATE INDEX idx_agent_feedback_feedback_type
ON agent_feedback(feedback_type);

-- Create index for time-based queries
CREATE INDEX idx_agent_feedback_created_at
ON agent_feedback(created_at DESC);

-- Create GIN index for feedback_tags queries
CREATE INDEX idx_agent_feedback_tags
ON agent_feedback USING gin (feedback_tags);

-- Create GIN index for metadata queries
CREATE INDEX idx_agent_feedback_metadata
ON agent_feedback USING gin (metadata);

-- Create trigger for automatic updated_at
CREATE TRIGGER trigger_agent_feedback_updated_at
BEFORE UPDATE ON agent_feedback
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Enable Row-Level Security
ALTER TABLE agent_feedback ENABLE ROW LEVEL SECURITY;

-- Create RLS policy: Users can only access records for their tenant
CREATE POLICY agent_feedback_tenant_policy ON agent_feedback
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true))
WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- Views
-- ============================================================================

-- Create view for user's recent sessions
CREATE OR REPLACE VIEW v_user_recent_sessions AS
SELECT
    ch.tenant_id,
    ch.session_id,
    ch.agent_id,
    MAX(ch.created_at) AS last_activity_at,
    COUNT(*) FILTER (WHERE ch.role = 'user') AS user_message_count,
    COUNT(*) FILTER (WHERE ch.role = 'assistant') AS assistant_message_count,
    SUM(ch.tokens_used) AS total_tokens_used
FROM agent_conversation_history ch
GROUP BY ch.tenant_id, ch.session_id, ch.agent_id
ORDER BY MAX(ch.created_at) DESC;

-- ============================================================================
-- Migration Summary
-- ============================================================================
-- Tables created: 5
--   - agent_semantic_memory
--   - agent_conversation_history
--   - agent_tasks
--   - rag_documents
--   - agent_feedback
--
-- Indexes created: 27
--   - 2 HNSW vector indexes (for semantic search)
--   - 25 B-tree and GIN indexes (for lookups and metadata queries)
--
-- RLS policies created: 5
--   - One per table for tenant isolation
--
-- Views created: 1
--   - v_user_recent_sessions
--
-- Functions created: 1
--   - update_updated_at_column()
--
-- Triggers created: 5
--   - One per table for automatic updated_at timestamp
-- ============================================================================

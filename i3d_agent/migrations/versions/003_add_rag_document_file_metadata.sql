-- ============================================================================
-- Migration: Add RAG document file metadata
-- Description: Stores original uploaded/imported file metadata for dedupe,
--              archive lookup, and batch import traceability.
-- ============================================================================

ALTER TABLE rag_documents
    ADD COLUMN IF NOT EXISTS file_md5 VARCHAR(32),
    ADD COLUMN IF NOT EXISTS file_name TEXT,
    ADD COLUMN IF NOT EXISTS file_size BIGINT,
    ADD COLUMN IF NOT EXISTS mime_type TEXT,
    ADD COLUMN IF NOT EXISTS storage_path TEXT,
    ADD COLUMN IF NOT EXISTS source_path TEXT;

CREATE INDEX IF NOT EXISTS idx_rag_docs_file_md5
ON rag_documents(tenant_id, file_md5)
WHERE file_md5 IS NOT NULL AND deleted_at IS NULL;

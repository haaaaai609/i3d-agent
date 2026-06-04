"""DocumentManager for CRUD operations with version control."""

from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import uuid
import json
import asyncpg


from i3d_agent.rag.models import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse
)


class DocumentManager:
    """
    Manages document CRUD operations with version control.

    Features:
    - Create documents with automatic indexing
    - Update documents with version tracking
    - Soft/hard delete with chunk management
    - Restore deleted documents
    - Document history tracking
    - Pagination support
    """

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        """
        Initialize DocumentManager.

        Args:
            pool: Optional asyncpg connection pool
        """
        self.pool = pool
        self._conn: Optional[asyncpg.Connection] = None

    async def _get_connection(self) -> asyncpg.Connection:
        """Get database connection."""
        if self._conn:
            return self._conn
        if self.pool:
            return await self.pool.acquire()
        raise RuntimeError("No database connection available")

    async def _release_connection(self, conn: asyncpg.Connection):
        """Release connection back to pool."""
        if self.pool and conn != self._conn:
            await self.pool.release(conn)

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
        Create a new document and add to index queue.

        Args:
            tenant_id: Tenant identifier
            title: Document title
            content: Document content
            doc_type: Document type (technical, business, api)
            source_type: Source type (md, pdf, html, json)
            description: Optional description
            metadata: Optional metadata dictionary
            tags: Optional tags list
            language: Document language (default: zh)

        Returns:
            DocumentResponse: Created document
        """
        content_hash = self._calculate_content_hash(content)
        doc_id = str(uuid.uuid4())

        metadata = metadata or {}
        tags = tags or []

        conn = await self._get_connection()
        try:
            doc = await self._db_insert(
                conn,
                doc_id=doc_id,
                tenant_id=tenant_id,
                title=title,
                content=content,
                content_hash=content_hash,
                doc_type=doc_type,
                source_type=source_type,
                description=description,
                metadata=metadata,
                tags=tags,
                language=language
            )

            # Add to index queue
            await self._add_index_task(conn, doc_id, tenant_id, "create")

            return doc

        finally:
            await self._release_connection(conn)

    async def update_document(
        self,
        doc_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        change_reason: Optional[str] = None
    ) -> Optional[DocumentResponse]:
        """
        Update document and create new version if content changed.

        Args:
            doc_id: Document ID
            content: New content (optional)
            title: New title (optional)
            description: New description (optional)
            metadata: New metadata (optional)
            tags: New tags (optional)
            change_reason: Reason for change (optional)

        Returns:
            DocumentResponse if updated, None if no changes
        """
        conn = await self._get_connection()
        try:
            # Get current document
            current = await self._get_document(conn, doc_id, include_deleted=False)
            if not current:
                raise ValueError(f"Document {doc_id} not found")

            # Calculate new content hash
            new_content = content if content is not None else current.get('raw_content')
            new_hash = self._calculate_content_hash(new_content)

            # Check if content actually changed
            if new_hash == current.get('content_hash') and title is None and description is None:
                return None  # No meaningful changes

            # Create new version
            new_version = current.get('version', 1) + 1
            new_doc_id = str(uuid.uuid4())

            # Save version snapshot
            await self._save_version_snapshot(
                conn,
                doc_id=current.get('id'),
                tenant_id=current.get('tenant_id'),
                version=current.get('version'),
                content_snapshot=current.get('raw_content'),
                change_type="update",
                change_reason=change_reason
            )

            # Soft delete old chunks
            await self._soft_delete_chunks(conn, current.get('id'))

            # Mark old version as not latest
            await self._db_update(
                conn,
                doc_id=current.get('id'),
                updates={"is_latest": False}
            )

            # Create new document version
            updated = await self._db_insert(
                conn,
                doc_id=new_doc_id,
                tenant_id=current.get('tenant_id'),
                title=title if title is not None else current.get('title'),
                content=new_content,
                content_hash=new_hash,
                doc_type=current.get('doc_type'),
                source_type=current.get('source_type'),
                description=description if description is not None else current.get('description'),
                metadata=metadata if metadata is not None else current.get('metadata'),
                tags=tags if tags is not None else current.get('tags'),
                language=current.get('language'),
                version=new_version,
                parent_doc_id=current.get('id'),
                is_latest=True
            )

            # Add to index queue
            await self._add_index_task(
                conn,
                new_doc_id,
                current.get('tenant_id'),
                "update"
            )

            return updated

        finally:
            await self._release_connection(conn)

    async def delete_document(
        self,
        doc_id: str,
        soft_delete: bool = True,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Delete document (soft or hard delete).

        Args:
            doc_id: Document ID
            soft_delete: If True, soft delete; if False, hard delete
            tenant_id: Tenant ID (for verification)

        Returns:
            bool: True if deleted successfully
        """
        conn = await self._get_connection()
        try:
            if soft_delete:
                # Soft delete: update deleted_at timestamp
                await self._db_update(
                    conn,
                    doc_id=doc_id,
                    updates={
                        "deleted_at": datetime.now(),
                        "is_latest": False
                    }
                )

                # Soft delete chunks
                await self._soft_delete_chunks(conn, doc_id)

            else:
                # Hard delete: remove from database
                await self._db_delete(conn, doc_id)

            # Add to index queue for cleanup
            doc = await self._get_document(conn, doc_id, include_deleted=True)
            if doc:
                await self._add_index_task(
                    conn,
                    doc_id,
                    doc.get('tenant_id'),
                    "delete"
                )

            return True

        finally:
            await self._release_connection(conn)

    async def restore_document(
        self,
        doc_id: str,
        version: Optional[int] = None
    ) -> DocumentResponse:
        """
        Restore deleted document or specific version.

        Args:
            doc_id: Document ID
            version: Specific version to restore (optional)

        Returns:
            DocumentResponse: Restored document
        """
        conn = await self._get_connection()
        try:
            # Get deleted document
            doc = await self._get_document(conn, doc_id, include_deleted=True)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")

            if not doc.get('deleted_at'):
                raise ValueError(f"Document {doc_id} is not deleted")

            # Restore document
            await self._db_update(
                conn,
                doc_id=doc_id,
                updates={
                    "deleted_at": None,
                    "is_latest": True
                }
            )

            # Restore chunks
            await self._restore_chunks(conn, doc_id)

            # Add to index queue
            await self._add_index_task(
                conn,
                doc_id,
                doc.get('tenant_id'),
                "create"
            )

            return await self.get_document(doc_id)

        finally:
            await self._release_connection(conn)

    async def get_document(
        self,
        doc_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[DocumentResponse]:
        """
        Get document details.

        Args:
            doc_id: Document ID
            tenant_id: Tenant ID for verification (optional)

        Returns:
            DocumentResponse if found, None otherwise
        """
        conn = await self._get_connection()
        try:
            doc = await self._get_document(
                conn,
                doc_id,
                tenant_id=tenant_id,
                include_deleted=False
            )

            if not doc:
                return None

            return self._row_to_document_response(doc)

        finally:
            await self._release_connection(conn)

    async def get_document_history(
        self,
        doc_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get document version history.

        Args:
            doc_id: Document ID
            tenant_id: Tenant ID for verification (optional)

        Returns:
            List of version history entries
        """
        conn = await self._get_connection()
        try:
            return await self._get_document_history(
                conn,
                doc_id,
                tenant_id
            )

        finally:
            await self._release_connection(conn)

    async def list_documents(
        self,
        tenant_id: str,
        limit: int = 20,
        offset: int = 0,
        doc_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[DocumentResponse]:
        """
        List documents with pagination.

        Args:
            tenant_id: Tenant ID
            limit: Maximum number of results (default: 20)
            offset: Pagination offset (default: 0)
            doc_type: Filter by document type (optional)
            tags: Filter by tags (optional)

        Returns:
            List of DocumentResponse objects
        """
        conn = await self._get_connection()
        try:
            rows = await self._list_documents(
                conn,
                tenant_id=tenant_id,
                limit=limit,
                offset=offset,
                doc_type=doc_type,
                tags=tags
            )

            return [self._row_to_document_response(row) for row in rows]

        finally:
            await self._release_connection(conn)

    # ========================================================================
    # Private helper methods
    # ========================================================================

    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def _db_insert(
        self,
        conn: asyncpg.Connection,
        doc_id: str,
        tenant_id: str,
        title: str,
        content: str,
        content_hash: str,
        doc_type: str,
        source_type: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        language: str = "zh",
        version: int = 1,
        parent_doc_id: Optional[str] = None,
        is_latest: bool = True
    ) -> DocumentResponse:
        """Insert document into database."""
        query = """
            INSERT INTO rag_documents (
                id, tenant_id, title, description, doc_type, source_type,
                raw_content, content_hash, version, is_latest, parent_doc_id,
                status, metadata, tags, language
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            RETURNING *
        """

        # Convert metadata and tags to JSON
        metadata_json = json.dumps(metadata) if metadata else None
        tags_array = list(tags) if tags else []

        row = await conn.fetchrow(
            query,
            doc_id, tenant_id, title, description, doc_type, source_type,
            content, content_hash, version, is_latest, parent_doc_id,
            'pending', metadata_json, tags_array, language
        )

        return self._row_to_document_response(row)

    async def _db_update(
        self,
        conn: asyncpg.Connection,
        doc_id: str,
        updates: Dict[str, Any]
    ):
        """Update document in database."""
        if not updates:
            return

        set_clauses = []
        params = []
        param_count = 1

        for key, value in updates.items():
            set_clauses.append(f"{key} = ${param_count}")
            params.append(value)
            param_count += 1

        params.append(doc_id)

        query = f"""
            UPDATE rag_documents
            SET {', '.join(set_clauses)}
            WHERE id = ${param_count}
        """

        await conn.execute(query, *params)

    async def _db_delete(
        self,
        conn: asyncpg.Connection,
        doc_id: str
    ):
        """Hard delete document from database."""
        query = "DELETE FROM rag_documents WHERE id = $1"
        await conn.execute(query, doc_id)

    async def _get_document(
        self,
        conn: asyncpg.Connection,
        doc_id: str,
        tenant_id: Optional[str] = None,
        include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get document from database."""
        query = "SELECT * FROM rag_documents WHERE id = $1"
        params = [doc_id]

        if not include_deleted:
            query += " AND deleted_at IS NULL"

        if tenant_id:
            query += " AND tenant_id = $2"
            params.append(tenant_id)

        row = await conn.fetchrow(query, *params)

        if not row:
            return None

        return dict(row)

    async def _list_documents(
        self,
        conn: asyncpg.Connection,
        tenant_id: str,
        limit: int = 20,
        offset: int = 0,
        doc_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List documents from database."""
        query = """
            SELECT * FROM rag_documents
            WHERE tenant_id = $1
            AND deleted_at IS NULL
            AND is_latest = true
        """
        params = [tenant_id]
        param_count = 2

        if doc_type:
            query += f" AND doc_type = ${param_count}"
            params.append(doc_type)
            param_count += 1

        if tags:
            query += f" AND tags && ${param_count}"
            params.append(tags)
            param_count += 1

        query += f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

    async def _save_version_snapshot(
        self,
        conn: asyncpg.Connection,
        doc_id: str,
        tenant_id: str,
        version: int,
        content_snapshot: str,
        change_type: str = "update",
        change_reason: Optional[str] = None
    ):
        """Save version snapshot to database."""
        query = """
            INSERT INTO rag_versions (
                doc_id, tenant_id, version, content_snapshot,
                change_type, change_reason
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """

        await conn.execute(
            query,
            doc_id, tenant_id, version, content_snapshot,
            change_type, change_reason
        )

    async def _get_document_history(
        self,
        conn: asyncpg.Connection,
        doc_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get document version history."""
        query = """
            SELECT v.*, d.title, d.doc_type
            FROM rag_versions v
            JOIN rag_documents d ON v.doc_id = d.id
            WHERE v.doc_id = $1
        """
        params = [doc_id]

        if tenant_id:
            query += " AND v.tenant_id = $2"
            params.append(tenant_id)

        query += " ORDER BY v.version DESC"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

    async def _soft_delete_chunks(
        self,
        conn: asyncpg.Connection,
        doc_id: str
    ):
        """Soft delete all chunks for a document."""
        query = """
            UPDATE rag_chunks
            SET deleted_at = NOW()
            WHERE doc_id = $1 AND deleted_at IS NULL
        """
        await conn.execute(query, doc_id)

    async def _restore_chunks(
        self,
        conn: asyncpg.Connection,
        doc_id: str
    ):
        """Restore soft deleted chunks for a document."""
        query = """
            UPDATE rag_chunks
            SET deleted_at = NULL
            WHERE doc_id = $1 AND deleted_at IS NOT NULL
        """
        await conn.execute(query, doc_id)

    async def _add_index_task(
        self,
        conn: asyncpg.Connection,
        doc_id: str,
        tenant_id: str,
        operation: str,
        priority: int = 5
    ):
        """Add document to index queue."""
        query = """
            INSERT INTO rag_index_queue (
                doc_id, tenant_id, operation, priority, status
            ) VALUES ($1, $2, $3, $4, 'pending')
        """

        await conn.execute(query, doc_id, tenant_id, operation, priority)

    def _row_to_document_response(self, row: Dict[str, Any]) -> DocumentResponse:
        """Convert database row to DocumentResponse."""
        # Handle metadata - could be None, dict, or JSON string
        metadata = row.get('metadata')
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        elif metadata is None:
            metadata = {}
        else:
            metadata = dict(metadata)

        # Handle tags - could be None, list
        tags = row.get('tags')
        if tags is None:
            tags = []
        elif not isinstance(tags, list):
            tags = list(tags)

        return DocumentResponse(
            id=str(row['id']),
            tenant_id=row['tenant_id'],
            title=row['title'],
            description=row.get('description'),
            doc_type=row['doc_type'],
            source_type=row.get('source_type'),
            version=row['version'],
            is_latest=row['is_latest'],
            status=row['status'],
            metadata=metadata,
            tags=tags,
            language=row['language'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

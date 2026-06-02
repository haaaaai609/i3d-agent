"""IndexWorker - processes document indexing tasks from the queue."""

import asyncio
import uuid
from typing import Optional, List, Dict, Any
import asyncpg

from i3d_agent.rag.processor import DocumentProcessor
from i3d_agent.rag.embedding import EmbeddingService
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class IndexWorker:
    """
    IndexWorker processes document indexing tasks from the queue.

    This worker continuously polls the index queue for pending tasks and processes them:
    - CREATE: Split document, generate embeddings, save chunks
    - UPDATE: Soft delete old chunks, process new version
    - DELETE: Remove chunks from database

    The worker integrates DocumentProcessor for content splitting and
    EmbeddingService for vector generation.
    """

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        """
        Initialize IndexWorker.

        Args:
            pool: Optional database connection pool
        """
        self.pool = pool
        self.processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
        self.is_running = False
        self._stop_event = asyncio.Event()
        self._conn: Optional[asyncpg.Connection] = None

    async def process_task(
        self,
        task_id: str,
        operation: str = "create"
    ) -> bool:
        """
        Process a single indexing task.

        Args:
            task_id: Task ID from the index queue
            operation: Operation type (create/update/delete)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Processing task {task_id} with operation: {operation}")

            # Get task details
            task = await self._get_task(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                await self._mark_completed(task_id, status="failed", error_message="Task not found")
                return False

            doc_id = task['doc_id']
            tenant_id = task['tenant_id']

            # Get document
            doc = await self._get_document(doc_id, tenant_id)
            if not doc:
                logger.warning(f"Document {doc_id} not found for task {task_id}")
                await self._mark_completed(task_id, status="failed", error_message="Document not found")
                return False

            # Process based on operation
            if operation == "create":
                await self._process_create(doc, task_id)
            elif operation == "update":
                await self._process_update(doc, task_id)
            elif operation == "delete":
                await self._process_delete(doc, task_id)
            else:
                logger.warning(f"Unknown operation: {operation}")
                await self._mark_completed(task_id, status="failed", error_message=f"Unknown operation: {operation}")
                return False

            logger.info(f"Successfully processed task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            await self._mark_completed(task_id, status="failed", error_message=str(e))
            return False

    async def _process_create(self, doc: Dict[str, Any], task_id: str):
        """Process document creation - split, embed, and save chunks."""
        chunks = await self._split_and_embed(doc)
        await self._save_chunks(chunks, doc)
        await self._mark_completed(task_id, status="completed")

    async def _process_update(self, doc: Dict[str, Any], task_id: str):
        """Process document update - delete old chunks, process new version."""
        # Soft delete old chunks if parent_doc_id exists
        if doc.get('parent_doc_id'):
            await self._soft_delete_old_chunks(doc['parent_doc_id'])

        chunks = await self._split_and_embed(doc)
        await self._save_chunks(chunks, doc)
        await self._mark_completed(task_id, status="completed")

    async def _process_delete(self, doc: Dict[str, Any], task_id: str):
        """Process document deletion - remove chunks."""
        await self._delete_chunks(doc['id'])
        await self._mark_completed(task_id, status="completed")

    async def _split_and_embed(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split document content and generate embeddings.

        Args:
            doc: Document dictionary

        Returns:
            List of chunks with embeddings
        """
        # Split content into chunks
        chunks = self.processor.split_content(
            content=doc['raw_content'],
            doc_type=doc['doc_type'],
            doc_id=doc['id'],
            title=doc.get('title'),
            language=doc.get('language', 'zh')
        )

        if not chunks:
            logger.warning(f"No chunks generated for document {doc['id']}")
            return []

        # Generate embeddings for all chunks
        chunks_with_embeddings = await self.embedding_service.embed_chunks(chunks)

        logger.debug(f"Generated {len(chunks_with_embeddings)} chunks with embeddings for doc {doc['id']}")
        return chunks_with_embeddings

    async def _save_chunks(self, chunks: List[Dict[str, Any]], doc: Dict[str, Any]):
        """
        Save chunks to database.

        Args:
            chunks: List of chunks with embeddings
            doc: Document metadata
        """
        if not chunks:
            return

        conn = await self._get_connection()
        try:
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())

                query = """
                    INSERT INTO rag_chunks (
                        id, doc_id, tenant_id, content, embedding,
                        chunk_index, token_count, metadata, doc_version
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """

                await conn.execute(
                    query,
                    chunk_id,
                    doc['id'],
                    doc['tenant_id'],
                    chunk['content'],
                    chunk['embedding'],
                    chunk['metadata'].get('chunk_index', 0),
                    chunk['metadata'].get('token_count'),
                    chunk['metadata'],
                    doc.get('version', 1)
                )

            logger.info(f"Saved {len(chunks)} chunks for document {doc['id']}")

        finally:
            self._release_connection(conn)

    async def _soft_delete_old_chunks(self, old_doc_id: str):
        """
        Soft delete old chunks for a document.

        Args:
            old_doc_id: Old document ID
        """
        conn = await self._get_connection()
        try:
            query = """
                UPDATE rag_chunks
                SET deleted_at = NOW()
                WHERE doc_id = $1 AND deleted_at IS NULL
            """
            await conn.execute(query, old_doc_id)
            logger.info(f"Soft deleted chunks for old document {old_doc_id}")

        finally:
            self._release_connection(conn)

    async def _delete_chunks(self, doc_id: str):
        """
        Delete chunks for a document (hard delete).

        Args:
            doc_id: Document ID
        """
        conn = await self._get_connection()
        try:
            query = "DELETE FROM rag_chunks WHERE doc_id = $1"
            await conn.execute(query, doc_id)
            logger.info(f"Deleted chunks for document {doc_id}")

        finally:
            self._release_connection(conn)

    async def _get_document(
        self,
        doc_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get document from database.

        Args:
            doc_id: Document ID
            tenant_id: Tenant ID (optional)

        Returns:
            Document dict or None
        """
        conn = await self._get_connection()
        try:
            query = "SELECT * FROM rag_documents WHERE id = $1"
            params = [doc_id]

            if tenant_id:
                query += " AND tenant_id = $2"
                params.append(tenant_id)

            row = await conn.fetchrow(query, *params)

            if not row:
                return None

            return dict(row)

        finally:
            self._release_connection(conn)

    async def _get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task from index queue.

        Args:
            task_id: Task ID

        Returns:
            Task dict or None
        """
        conn = await self._get_connection()
        try:
            query = "SELECT * FROM rag_index_queue WHERE id = $1"
            row = await conn.fetchrow(query, task_id)

            if not row:
                return None

            return dict(row)

        finally:
            self._release_connection(conn)

    async def _mark_completed(
        self,
        task_id: str,
        status: str = "completed",
        error_message: Optional[str] = None
    ):
        """
        Mark task as completed in the queue.

        Args:
            task_id: Task ID
            status: Task status (completed/failed)
            error_message: Error message if failed
        """
        conn = await self._get_connection()
        try:
            query = """
                UPDATE rag_index_queue
                SET status = $1, error_message = $2, updated_at = NOW()
                WHERE id = $3
            """
            await conn.execute(query, status, error_message, task_id)
            logger.debug(f"Marked task {task_id} as {status}")

        finally:
            self._release_connection(conn)

    async def run_worker(
        self,
        poll_interval: float = 5.0,
        max_concurrent: int = 5
    ):
        """
        Continuously process tasks from the queue.

        Args:
            poll_interval: Seconds between queue polls (default: 5.0)
            max_concurrent: Maximum concurrent tasks (default: 5)
        """
        if not self.pool:
            raise RuntimeError("Database pool not configured")

        self.is_running = True
        self._stop_event.clear()

        logger.info(f"Starting IndexWorker with poll_interval={poll_interval}, max_concurrent={max_concurrent}")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        try:
            while self.is_running:
                # Check for stop event
                if self._stop_event.is_set():
                    logger.info("Stop event received, finishing current tasks...")
                    break

                # Get pending tasks
                tasks = await self._get_pending_tasks(limit=max_concurrent)

                if not tasks:
                    # No tasks, wait for poll_interval
                    await asyncio.sleep(poll_interval)
                    continue

                logger.info(f"Found {len(tasks)} pending tasks")

                # Process tasks concurrently
                async def process_with_semaphore(task):
                    async with semaphore:
                        return await self.process_task(task['id'], task['operation'])

                # Run all tasks
                results = await asyncio.gather(
                    *[process_with_semaphore(task) for task in tasks],
                    return_exceptions=True
                )

                # Log results
                success_count = sum(1 for r in results if r is True)
                failure_count = len(results) - success_count

                if failure_count > 0:
                    logger.warning(f"Processed {len(tasks)} tasks: {success_count} success, {failure_count} failed")
                else:
                    logger.info(f"Successfully processed {success_count} tasks")

                # Small delay before next poll
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("Worker cancelled")
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            self.is_running = False
            logger.info("IndexWorker stopped")

    async def stop_worker(self):
        """Stop the worker gracefully."""
        logger.info("Stopping IndexWorker...")
        self.is_running = False
        self._stop_event.set()

        # Close embedding service client
        await self.embedding_service.close()

    async def _get_pending_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending tasks from the queue.

        Args:
            limit: Maximum number of tasks to retrieve

        Returns:
            List of pending tasks
        """
        conn = await self._get_connection()
        try:
            query = """
                SELECT id, doc_id, tenant_id, operation, priority
                FROM rag_index_queue
                WHERE status = 'pending'
                ORDER BY priority ASC, created_at ASC
                LIMIT $1
                FOR UPDATE SKIP LOCKED
            """

            rows = await conn.fetch(query, limit)
            return [dict(row) for row in rows]

        finally:
            self._release_connection(conn)

    async def _get_connection(self) -> asyncpg.Connection:
        """Get database connection."""
        if not self.pool:
            raise RuntimeError("Database pool not configured")

        if self._conn:
            return self._conn

        return await self.pool.acquire()

    def _release_connection(self, conn: asyncpg.Connection):
        """Release connection back to pool."""
        if self.pool and conn != self._conn:
            self.pool.release(conn)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_worker()

#!/usr/bin/env python3
"""RAG Index Worker startup script.

This script runs the RAG index worker which processes document indexing tasks
from the rag_index_queue table asynchronously.
"""

import asyncio
import sys
import asyncpg
from i3d_agent.rag.index_worker import IndexWorker
from i3d_agent.config.settings import get_settings
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


async def create_pool(dsn: str) -> asyncpg.Pool:
    """Create database connection pool."""
    return await asyncpg.create_pool(dsn, min_size=2, max_size=10)


async def main():
    """Main function to run the RAG index worker."""
    settings = get_settings()

    logger.info("Starting RAG Index Worker...")
    logger.info(f"Poll interval: 5s")
    logger.info(f"Max concurrent: {settings.INDEX_WORKER_CONCURRENCY}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'localhost'}")

    # Create database pool
    pool = await create_pool(settings.DATABASE_URL)

    try:
        worker = IndexWorker(pool=pool)

        logger.info("Worker ready, waiting for indexing tasks...")
        await worker.run_worker(
            poll_interval=5.0,
            max_concurrent=settings.INDEX_WORKER_CONCURRENCY
        )
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await worker.stop_worker()
        await pool.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())

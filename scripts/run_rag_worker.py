#!/usr/bin/env python3
"""RAG Index Worker startup script.

This script runs the RAG index worker which processes document indexing tasks
from the rag_index_queue table asynchronously.
"""

import asyncio
import sys
from i3d_agent.rag.index_worker import IndexWorker
from i3d_agent.config.settings import get_settings
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function to run the RAG index worker."""
    settings = get_settings()

    logger.info("Starting RAG Index Worker...")
    logger.info(f"Concurrency: {settings.INDEX_WORKER_CONCURRENCY}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'localhost'}")

    worker = IndexWorker()

    try:
        logger.info("Worker ready, waiting for indexing tasks...")
        await worker.run_worker(concurrency=settings.INDEX_WORKER_CONCURRENCY)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        sys.exit(1)
    finally:
        worker.stop_worker()
        await worker.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())

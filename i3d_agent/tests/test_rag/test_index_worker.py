"""Tests for IndexWorker - document indexing queue processor."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from i3d_agent.rag.index_worker import IndexWorker


@pytest.mark.asyncio
async def test_process_document_create():
    """测试处理文档创建"""
    worker = IndexWorker()

    with patch.object(worker, '_get_task') as mock_get_task, \
         patch.object(worker, '_get_document') as mock_get, \
         patch.object(worker, '_split_and_embed') as mock_embed, \
         patch.object(worker, '_save_chunks') as mock_save, \
         patch.object(worker, '_mark_completed') as mock_complete:

        mock_get_task.return_value = {
            'doc_id': 'doc-1',
            'tenant_id': 'default',
            'operation': 'create'
        }
        mock_get.return_value = {
            'id': 'doc-1',
            'raw_content': 'Test content',
            'doc_type': 'technical',
            'tenant_id': 'default',
            'version': 1
        }
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

    with patch.object(worker, '_get_task') as mock_get_task, \
         patch.object(worker, '_get_document') as mock_get, \
         patch.object(worker, '_soft_delete_old_chunks') as mock_delete, \
         patch.object(worker, '_split_and_embed') as mock_embed, \
         patch.object(worker, '_save_chunks') as mock_save, \
         patch.object(worker, '_mark_completed') as mock_complete:

        mock_get_task.return_value = {
            'doc_id': 'doc-1',
            'tenant_id': 'default',
            'operation': 'update'
        }
        mock_get.return_value = {
            'id': 'doc-1',
            'raw_content': 'New content',
            'doc_type': 'technical',
            'tenant_id': 'default',
            'version': 2,
            'parent_doc_id': 'old-doc-1'
        }

        await worker.process_task("task-1", operation="update")

        mock_delete.assert_called_once_with("old-doc-1")
        mock_embed.assert_called_once()
        mock_save.assert_called_once()
        mock_complete.assert_called_once()


@pytest.mark.asyncio
async def test_process_document_delete():
    """测试处理文档删除"""
    worker = IndexWorker()

    with patch.object(worker, '_get_task') as mock_get_task, \
         patch.object(worker, '_get_document') as mock_get, \
         patch.object(worker, '_delete_chunks') as mock_delete, \
         patch.object(worker, '_mark_completed') as mock_complete:

        mock_get_task.return_value = {
            'doc_id': 'doc-1',
            'tenant_id': 'default',
            'operation': 'delete'
        }
        mock_get.return_value = {
            'id': 'doc-1',
            'tenant_id': 'default'
        }

        await worker.process_task("task-1", operation="delete")

        mock_delete.assert_called_once_with("doc-1")
        mock_complete.assert_called_once()
        # No embedding or save should happen for delete
        assert mock_delete.call_count == 1


@pytest.mark.asyncio
async def test_split_and_embed():
    """测试切分和嵌入生成"""
    worker = IndexWorker()

    mock_processor = AsyncMock()
    mock_processor.split_content.return_value = [
        {"content": "Chunk 1", "metadata": {}},
        {"content": "Chunk 2", "metadata": {}}
    ]

    mock_embedding = AsyncMock()
    mock_embedding.embed_chunks.return_value = [
        {"content": "Chunk 1", "embedding": [0.1] * 1536, "metadata": {}},
        {"content": "Chunk 2", "embedding": [0.2] * 1536, "metadata": {}}
    ]

    worker.processor = mock_processor
    worker.embedding_service = mock_embedding

    doc = {
        'raw_content': 'Test content',
        'doc_type': 'technical',
        'tenant_id': 'default',
        'id': 'doc-1',
        'version': 1,
        'title': 'Test Doc'
    }

    chunks = await worker._split_and_embed(doc)

    assert len(chunks) == 2
    assert chunks[0]["embedding"] == [0.1] * 1536
    assert chunks[1]["embedding"] == [0.2] * 1536
    mock_processor.split_content.assert_called_once()
    mock_embedding.embed_chunks.assert_called_once()


@pytest.mark.asyncio
async def test_save_chunks():
    """测试保存chunks到数据库"""
    worker = IndexWorker()
    worker.pool = AsyncMock()

    chunks = [
        {
            "content": "Chunk 1",
            "embedding": [0.1] * 1536,
            "metadata": {"chunk_index": 0}
        },
        {
            "content": "Chunk 2",
            "embedding": [0.2] * 1536,
            "metadata": {"chunk_index": 1}
        }
    ]

    doc = {
        'id': 'doc-1',
        'tenant_id': 'default',
        'version': 1
    }

    # Mock connection
    mock_conn = AsyncMock()
    worker.pool.acquire = AsyncMock(return_value=mock_conn)
    worker.pool.release = AsyncMock()

    await worker._save_chunks(chunks, doc)

    # Verify chunks were inserted
    assert mock_conn.execute.call_count == 2
    worker.pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_soft_delete_old_chunks():
    """测试软删除旧chunks"""
    worker = IndexWorker()
    worker.pool = AsyncMock()

    mock_conn = AsyncMock()
    worker.pool.acquire = AsyncMock(return_value=mock_conn)
    worker.pool.release = AsyncMock()

    await worker._soft_delete_old_chunks("old-doc-1")

    mock_conn.execute.assert_called_once()
    # Verify SQL includes soft delete
    call_args = mock_conn.execute.call_args
    assert "deleted_at" in str(call_args)


@pytest.mark.asyncio
async def test_mark_completed():
    """测试标记任务完成"""
    worker = IndexWorker()
    worker.pool = AsyncMock()

    mock_conn = AsyncMock()
    worker.pool.acquire = AsyncMock(return_value=mock_conn)
    worker.pool.release = AsyncMock()

    await worker._mark_completed("task-1", status="completed")

    mock_conn.execute.assert_called_once()
    worker.pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_mark_failed():
    """测试标记任务失败"""
    worker = IndexWorker()
    worker.pool = AsyncMock()

    mock_conn = AsyncMock()
    worker.pool.acquire = AsyncMock(return_value=mock_conn)
    worker.pool.release = AsyncMock()

    await worker._mark_completed("task-1", status="failed", error_message="Processing failed")

    mock_conn.execute.assert_called_once()
    call_args = mock_conn.execute.call_args
    assert "failed" in str(call_args)
    worker.pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_get_document():
    """测试获取文档"""
    worker = IndexWorker()
    worker.pool = AsyncMock()

    mock_doc = {
        'id': 'doc-1',
        'raw_content': 'Test content',
        'doc_type': 'technical',
        'tenant_id': 'default',
        'version': 1,
        'title': 'Test Doc',
        'parent_doc_id': None
    }

    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = mock_doc
    worker.pool.acquire = AsyncMock(return_value=mock_conn)
    worker.pool.release = AsyncMock()

    doc = await worker._get_document("doc-1")

    assert doc is not None
    assert doc['id'] == "doc-1"
    assert doc['raw_content'] == "Test content"
    mock_conn.fetchrow.assert_called_once()
    worker.pool.release.assert_called_once_with(mock_conn)


@pytest.mark.asyncio
async def test_process_task_with_error():
    """测试处理任务时发生错误"""
    worker = IndexWorker()

    with patch.object(worker, '_get_task', side_effect=Exception("DB error")), \
         patch.object(worker, '_mark_completed') as mock_complete:

        await worker.process_task("task-1")

        # Should mark as failed
        mock_complete.assert_called_once_with("task-1", status="failed", error_message="DB error")


@pytest.mark.asyncio
async def test_process_task_missing_document():
    """测试处理不存在的文档"""
    worker = IndexWorker()

    with patch.object(worker, '_get_task', return_value={'doc_id': 'doc-1', 'tenant_id': 'default', 'operation': 'create'}), \
         patch.object(worker, '_get_document', return_value=None), \
         patch.object(worker, '_mark_completed') as mock_complete:

        await worker.process_task("task-1")

        # Should mark as failed
        mock_complete.assert_called_once()
        call_args = mock_complete.call_args
        assert "failed" in str(call_args)


@pytest.mark.asyncio
async def test_delete_chunks():
    """测试删除chunks"""
    worker = IndexWorker()
    worker.pool = AsyncMock()

    mock_conn = AsyncMock()
    worker.pool.acquire = AsyncMock(return_value=mock_conn)
    worker.pool.release = AsyncMock()

    await worker._delete_chunks("doc-1")

    mock_conn.execute.assert_called_once()
    worker.pool.release.assert_called_once_with(mock_conn)


def test_worker_initialization():
    """测试worker初始化"""
    worker = IndexWorker()

    assert worker.processor is not None
    assert worker.embedding_service is not None
    assert worker.is_running is False
    assert worker.pool is None


@pytest.mark.asyncio
async def test_stop_worker():
    """测试停止worker"""
    worker = IndexWorker()
    worker.is_running = True

    await worker.stop_worker()

    assert worker.is_running is False

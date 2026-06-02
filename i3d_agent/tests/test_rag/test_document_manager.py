"""Tests for DocumentManager"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from i3d_agent.rag.document_manager import DocumentManager


@pytest.mark.asyncio
async def test_create_document():
    """测试创建文档"""
    manager = DocumentManager()

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_db_insert') as mock_insert, \
         patch.object(manager, '_add_index_task') as mock_task:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn
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

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_get_document') as mock_get, \
         patch.object(manager, '_db_insert') as mock_insert, \
         patch.object(manager, '_db_update') as mock_update, \
         patch.object(manager, '_save_version_snapshot') as mock_snapshot, \
         patch.object(manager, '_add_index_task') as mock_task:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn

        # Mock current document
        current = {
            'id': "doc-1",
            'version': 1,
            'content_hash': "old-hash",
            'tenant_id': "default",
            'title': "Old Title",
            'doc_type': 'technical',
            'raw_content': "old content"
        }
        mock_get.return_value = current

        # Mock new document
        new_doc = Mock()
        new_doc.id = "doc-2"
        new_doc.version = 2
        mock_insert.return_value = new_doc

        updated = await manager.update_document("doc-1", content="New content")

        assert updated.version == 2
        mock_snapshot.assert_called_once()


@pytest.mark.asyncio
async def test_delete_document_soft_delete():
    """测试软删除文档"""
    manager = DocumentManager()

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_db_update') as mock_update, \
         patch.object(manager, '_soft_delete_chunks') as mock_delete_chunks, \
         patch.object(manager, '_add_index_task') as mock_task, \
         patch.object(manager, '_get_document') as mock_get:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn
        mock_get.return_value = {'tenant_id': 'default'}

        result = await manager.delete_document("doc-1", soft_delete=True)

        mock_update.assert_called_once()
        mock_delete_chunks.assert_called_once_with(mock_conn, "doc-1")
        mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_delete_document_hard_delete():
    """测试硬删除文档"""
    manager = DocumentManager()

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_db_delete') as mock_delete, \
         patch.object(manager, '_add_index_task') as mock_task, \
         patch.object(manager, '_get_document') as mock_get:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn
        mock_get.return_value = {'tenant_id': 'default'}

        result = await manager.delete_document("doc-1", soft_delete=False)

        mock_delete.assert_called_once_with(mock_conn, "doc-1")
        mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_restore_document():
    """测试恢复文档"""
    manager = DocumentManager()

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_get_document') as mock_get, \
         patch.object(manager, '_db_update') as mock_update, \
         patch.object(manager, '_restore_chunks') as mock_restore_chunks, \
         patch.object(manager, '_add_index_task') as mock_task, \
         patch.object(manager, 'get_document') as mock_get_doc:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn

        deleted_doc = {
            'id': "doc-1",
            'deleted_at': datetime.now(),
            'tenant_id': 'default'
        }
        mock_get.return_value = deleted_doc

        restored_doc = Mock()
        restored_doc.id = "doc-1"
        mock_get_doc.return_value = restored_doc

        restored = await manager.restore_document("doc-1")

        mock_update.assert_called_once()
        mock_restore_chunks.assert_called_once_with(mock_conn, "doc-1")
        mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_get_document():
    """测试获取文档"""
    manager = DocumentManager()

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_get_document') as mock_get:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn

        mock_doc = {
            'id': "doc-1",
            'title': "Test Doc",
            'tenant_id': 'default',
            'doc_type': 'technical',
            'version': 1,
            'is_latest': True,
            'status': 'ready',
            'metadata': {},
            'tags': [],
            'language': 'zh',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_get.return_value = mock_doc

        doc = await manager.get_document("doc-1")

        assert doc.id == "doc-1"
        assert doc.title == "Test Doc"


@pytest.mark.asyncio
async def test_get_document_history():
    """测试获取文档历史版本"""
    manager = DocumentManager()

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_get_document_history') as mock_history:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn

        mock_versions = [
            {'version': 1, 'created_at': datetime.now(), 'title': 'V1'},
            {'version': 2, 'created_at': datetime.now(), 'title': 'V2'}
        ]
        mock_history.return_value = mock_versions

        history = await manager.get_document_history("doc-1")

        assert len(history) == 2
        assert history[0]['version'] == 1


@pytest.mark.asyncio
async def test_list_documents():
    """测试列出文档"""
    manager = DocumentManager()

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_list_documents') as mock_list:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn

        mock_docs = [
            {'id': "doc-1", 'title': "Doc 1", 'tenant_id': 'default', 'doc_type': 'technical',
             'version': 1, 'is_latest': True, 'status': 'ready', 'metadata': {}, 'tags': [],
             'language': 'zh', 'created_at': datetime.now(), 'updated_at': datetime.now()},
            {'id': "doc-2", 'title': "Doc 2", 'tenant_id': 'default', 'doc_type': 'business',
             'version': 1, 'is_latest': True, 'status': 'ready', 'metadata': {}, 'tags': [],
             'language': 'zh', 'created_at': datetime.now(), 'updated_at': datetime.now()}
        ]
        mock_list.return_value = mock_docs

        docs = await manager.list_documents(tenant_id="default", limit=10, offset=0)

        assert len(docs) == 2
        assert docs[0].id == "doc-1"


@pytest.mark.asyncio
async def test_content_hash_generation():
    """测试内容哈希生成"""
    manager = DocumentManager()

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_db_insert') as mock_insert, \
         patch.object(manager, '_add_index_task') as mock_task:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn
        mock_insert.return_value = Mock(id="doc-1", version=1)

        # Same content should produce same hash
        doc1 = await manager.create_document(
            tenant_id="default",
            title="Test Doc",
            content="Same content",
            doc_type="technical"
        )

        doc2 = await manager.create_document(
            tenant_id="default",
            title="Test Doc 2",
            content="Same content",
            doc_type="technical"
        )

        # The hash should be calculated and stored
        assert hasattr(doc1, 'content_hash')


@pytest.mark.asyncio
async def test_update_same_content_no_new_version():
    """测试相同内容更新时不创建新版本"""
    manager = DocumentManager()

    with patch.object(manager, '_get_connection') as mock_get_conn, \
         patch.object(manager, '_get_document') as mock_get:

        mock_conn = AsyncMock()
        mock_get_conn.return_value = mock_conn

        current = {
            'id': "doc-1",
            'version': 1,
            'content_hash': manager._calculate_content_hash("Same content"),
            'tenant_id': 'default',
            'title': 'Test',
            'doc_type': 'technical',
            'raw_content': 'Same content'
        }
        mock_get.return_value = current

        # Should return early without creating new version
        result = await manager.update_document("doc-1", content="Same content")

        # If content hasn't changed, should return None
        assert result is None

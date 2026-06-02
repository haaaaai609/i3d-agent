import pytest
from i3d_agent.rag.models import (
    DocumentCreate, DocumentUpdate, DocumentResponse,
    Chunk, SearchRequest, AskRequest, FeedbackRequest
)

def test_document_create_validation():
    """测试文档创建请求验证"""
    request = DocumentCreate(
        tenant_id="default",
        title="Test Document",
        content="This is a test document content.",
        doc_type="technical",
        source_type="md"
    )
    assert request.tenant_id == "default"
    assert request.title == "Test Document"
    assert request.doc_type == "technical"

def test_document_create_missing_required_fields():
    """测试缺少必填字段"""
    with pytest.raises(ValueError):
        DocumentCreate(
            tenant_id="default",
            title="",  # Empty title should fail
            content="Content",
            doc_type="technical"
        )

def test_chunk_model():
    """测试 Chunk 模型"""
    chunk = Chunk(
        id="uuid-1",
        doc_id="uuid-doc-1",
        tenant_id="default",
        content="Chunk content",
        embedding=[0.1] * 1536,
        chunk_index=0,
        token_count=100,
        metadata={"title": "Test", "chunk_index": 0},
        doc_version=1
    )
    assert chunk.doc_id == "uuid-doc-1"
    assert len(chunk.embedding) == 1536

def test_search_request():
    """测试搜索请求模型"""
    request = SearchRequest(
        query="如何配置 API？",
        tenant_id="default",
        top_k=10,
        enable_expansion=True,
        enable_hyde=True,
        enable_rerank=True
    )
    assert request.enable_expansion is True
    assert request.top_k == 10

def test_ask_request():
    """测试问答请求模型"""
    request = AskRequest(
        question="如何部署系统？",
        tenant_id="default",
        top_k=5,
        enable_multi_step=True
    )
    assert request.enable_multi_step is True

def test_feedback_request():
    """测试反馈请求模型"""
    request = FeedbackRequest(
        session_id="session-1",
        query="测试查询",
        rating=5,
        is_helpful=True,
        feedback_text="非常有帮助"
    )
    assert request.rating == 5
    assert request.is_helpful is True
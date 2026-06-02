"""Tests for document processor"""

import pytest
from i3d_agent.rag.processor import DocumentProcessor, ChunkSizeConfig


def test_chunk_size_config_defaults():
    """测试默认分块配置"""
    config = ChunkSizeConfig()
    assert config.default_size == 800
    assert config.default_overlap == 150
    assert config.technical_size == 1000
    assert config.business_size == 600


def test_processor_markdown_splitting():
    """测试 Markdown 文档切分"""
    processor = DocumentProcessor()

    markdown_content = """
# 第一章

这是第一章的内容，包含一些文字描述。

## 1.1 小节

这是小节的内容。

# 第二章

这是第二章的内容。
    """

    chunks = processor.split_markdown(markdown_content)

    assert len(chunks) > 0
    assert all('content' in c for c in chunks)
    assert all('metadata' in c for c in chunks)
    # 检查章节信息被保留
    assert any('第一章' in c.get('metadata', {}).get('section', '') for c in chunks)


def test_processor_code_block_preservation():
    """测试代码块保留"""
    processor = DocumentProcessor()

    content = """
# API 文档

## 示例代码

```python
def hello_world():
    print("Hello, World!")
    return True
```

这段代码实现了问候功能。
    """

    chunks = processor.split_content(content, doc_type="technical")

    # 代码块应该完整保留在单个 chunk 中
    code_chunks = [c for c in chunks if '```' in c['content']]
    assert len(code_chunks) == 1
    assert 'def hello_world' in code_chunks[0]['content']


def test_processor_api_endpoint_splitting():
    """测试 API 文档按端点切分"""
    processor = DocumentProcessor()

    api_doc = """
# API Reference

## GET /api/v1/models

获取模型列表。

## POST /api/v1/models

创建新模型。
    """

    chunks = processor.split_api_document(api_doc)

    # 每个 API 端点应该是独立的 chunk
    assert len(chunks) == 2
    assert any('/api/v1/models' in c['content'] for c in chunks)


def test_metadata_extraction():
    """测试元数据提取"""
    processor = DocumentProcessor()

    chunks = processor.split_content(
        "Test content here",
        doc_type="technical",
        doc_id="test-doc-1",
        title="Test Document"
    )

    for i, chunk in enumerate(chunks):
        assert chunk['metadata']['doc_type'] == 'technical'
        assert chunk['metadata']['doc_id'] == 'test-doc-1'
        assert chunk['metadata']['title'] == 'Test Document'
        assert chunk['metadata']['chunk_index'] == i


def test_token_count_estimation():
    """测试 token 数量估算"""
    processor = DocumentProcessor()

    text = "This is a test sentence. " * 20
    count = processor.estimate_tokens(text)

    assert count > 0
    assert count < len(text)  # token 数应该少于字符数


def test_content_hash_calculation():
    """测试内容哈希计算"""
    processor = DocumentProcessor()

    content = "Test content for hashing"
    hash1 = processor.calculate_content_hash(content)
    hash2 = processor.calculate_content_hash(content)

    assert hash1 == hash2  # 相同内容应该产生相同哈希
    assert len(hash1) == 64  # SHA256 produces 64 hex characters


def test_paragraph_splitting():
    """测试段落切分"""
    processor = DocumentProcessor()

    content = """
    这是第一段内容。它包含多个句子。

    这是第二段内容。也有多个句子。

    这是第三段内容。
    """

    chunks = processor.split_paragraph(content)

    assert len(chunks) > 0
    assert all('content' in c for c in chunks)
    assert all('metadata' in c for c in chunks)


def test_empty_content():
    """测试空内容处理"""
    processor = DocumentProcessor()

    chunks = processor.split_content("")
    assert chunks == []


def test_split_content_routing():
    """测试 split_content 正确路由到不同的切分方法"""
    processor = DocumentProcessor()
    content = "# Test\n\nContent here"

    # Test API routing
    api_chunks = processor.split_content(content, doc_type="api")
    assert len(api_chunks) > 0

    # Test business routing
    business_chunks = processor.split_content(content, doc_type="business")
    assert len(business_chunks) > 0

    # Test technical routing (default)
    tech_chunks = processor.split_content(content, doc_type="technical")
    assert len(tech_chunks) > 0

"""Tests for HyDE (Hypothetical Document Embeddings) module"""
import pytest
from unittest.mock import patch, MagicMock
from i3d_agent.rag.hyde import HyDEService


@pytest.mark.asyncio
async def test_hyde_generation():
    """测试 HyDE 假设文档生成"""
    service = HyDEService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = """RAG 检索质量差的原因包括：
1. 文档切分策略不当
2. 缺少混合检索
3. 未使用重排序

改进方法：
1. 调整 chunk size
2. 结合向量检索和 BM25
3. 使用 Cohere Rerank API"""

        result = await service.generate_hypothetical("如何提高 RAG 检索质量？")

        assert result is not None
        assert "原因" in result or "改进" in result


@pytest.mark.asyncio
async def test_hyde_for_non_question():
    """测试非疑问句不生成 HyDE"""
    service = HyDEService()

    result = await service.generate_hypothetical("API 文档")

    assert result is None


@pytest.mark.asyncio
async def test_detect_question():
    """测试疑问句检测"""
    service = HyDEService()

    assert service._is_question("如何配置 API？")
    assert service._is_question("怎样使用这个功能")
    assert not service._is_question("API 文档")
    assert not service._is_question("系统配置")


@pytest.mark.asyncio
async def test_detect_question_english():
    """测试英文疑问句检测"""
    service = HyDEService()

    assert service._is_question("How to configure API?")
    assert service._is_question("What is RAG?")
    assert service._is_question("Why does this fail")
    assert not service._is_question("API documentation")
    assert not service._is_question("System configuration")


@pytest.mark.asyncio
async def test_llm_generate():
    """测试 LLM 生成假设文档"""
    service = HyDEService()

    with patch('i3d_agent.rag.hyde.simple_generate') as mock_generate:
        mock_generate.return_value = "Generated hypothetical document"

        result = await service._llm_generate("Test query")

        assert result == "Generated hypothetical document"
        mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_generate_hypothetical_full_flow():
    """测试完整的假设文档生成流程"""
    service = HyDEService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = "Generated answer document"

        result = await service.generate_hypothetical("如何使用这个系统？")

        assert result == "Generated answer document"


@pytest.mark.asyncio
async def test_question_variations():
    """测试各种疑问句式"""
    service = HyDEService()

    # 中文疑问词
    assert service._is_question("什么是 RAG？")
    assert service._is_question("为什么失败")
    assert service._is_question("哪里可以查看")
    assert service._is_question("哪个方法更好")
    assert service._is_question("何时使用")

    # 英文疑问词
    assert service._is_question("What is this?")
    assert service._is_question("How does it work")
    assert service._is_question("Where to find")
    assert service._is_question("Which method")

    # 非疑问句
    assert not service._is_question("用户手册")
    assert not service._is_question("Implementation guide")
    assert not service._is_question("系统架构文档")

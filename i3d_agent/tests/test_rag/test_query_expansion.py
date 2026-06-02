"""Tests for QueryExpansionService."""

import pytest
from unittest.mock import patch, AsyncMock
from i3d_agent.rag.query_expansion import QueryExpansionService


@pytest.mark.asyncio
async def test_query_expansion():
    """测试查询扩展"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = """
        1. 3D 搜索 API 配置方法
        2. 设置 3D 搜索 API 的步骤
        3. 怎样配置三维搜索接口
        """

        variations = await service.expand_query("如何配置 3D 搜索 API？")

        assert len(variations) >= 3
        assert "如何配置 3D 搜索 API？" in variations


@pytest.mark.asyncio
async def test_query_expansion_with_custom_count():
    """测试自定义扩展数量"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = "Variation 1\nVariation 2"

        variations = await service.expand_query("test", num_variations=2)

        assert len(variations) >= 2


@pytest.mark.asyncio
async def test_query_expansion_empty_response():
    """测试 LLM 返回空响应时的回退"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = ""

        variations = await service.expand_query("test query")

        # 应该只返回原始查询
        assert len(variations) == 1
        assert variations[0] == "test query"


@pytest.mark.asyncio
async def test_query_expansion_llm_error():
    """测试 LLM 调用失败时的回退"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.side_effect = Exception("LLM API error")

        variations = await service.expand_query("test query")

        # 应该只返回原始查询
        assert len(variations) == 1
        assert variations[0] == "test query"


@pytest.mark.asyncio
async def test_query_expansion_parsing_numbered_list():
    """测试解析带编号的列表"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = "1. First variation\n2. Second variation\n3. Third variation"

        variations = await service.expand_query("test")

        # 应该移除编号
        assert "First variation" in variations
        assert "Second variation" in variations
        assert "Third variation" in variations
        assert not any(v.startswith("1.") or v.startswith("2.") or v.startswith("3.") for v in variations)


@pytest.mark.asyncio
async def test_query_expansion_parsing_bullet_points():
    """测试解析项目符号列表"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = "- First variation\n- Second variation\n• Third variation"

        variations = await service.expand_query("test")

        # 应该移除项目符号
        assert "First variation" in variations
        assert "Second variation" in variations
        assert "Third variation" in variations


@pytest.mark.asyncio
async def test_query_expansion_removes_duplicates():
    """测试去重功能"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = "Same query\nSame query\nDifferent query"

        variations = await service.expand_query("Same query")

        # 原始查询 + 去重后的变体
        assert "Same query" in variations
        assert "Different query" in variations
        # 验证没有重复
        assert len(variations) == len(set(variations))


@pytest.mark.asyncio
async def test_query_expansion_includes_original():
    """测试始终包含原始查询"""
    service = QueryExpansionService()

    with patch.object(service, '_llm_generate') as mock_llm:
        mock_llm.return_value = "Variation 1\nVariation 2"

        original = "original query"
        variations = await service.expand_query(original)

        # 原始查询应该在结果中
        assert original in variations

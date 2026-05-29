"""Tests for SupervisorAgent class."""

import pytest

from i3d_agent.agents.base import AgentConfig
from i3d_agent.agents.supervisor import SupervisorAgent


class TestSupervisorAgent:
    """Tests for SupervisorAgent class."""

    def test_supervisor_init_default(self):
        """Test SupervisorAgent initialization with default config."""
        agent = SupervisorAgent()

        assert agent.config.name == "supervisor"
        assert agent.config.role == "task_coordinator"
        assert agent.tools == []

    def test_supervisor_init_custom_config(self):
        """Test SupervisorAgent initialization with custom config."""
        config = AgentConfig(
            name="custom_supervisor",
            role="coordinator",
            instructions="Custom instructions.",
        )
        agent = SupervisorAgent(config=config)

        assert agent.config.name == "custom_supervisor"
        assert agent.config.role == "coordinator"
        assert agent.config.instructions == "Custom instructions."

    def test_supervisor_analyze_intent_search(self):
        """Test intent analysis for search queries."""
        agent = SupervisorAgent()

        # Test various search keywords
        search_queries = [
            "搜索相关文档",
            "查找这个信息",
            "找到相似的项目",
            "匹配这个模式",
            "推荐一些资源",
        ]

        for query in search_queries:
            result = agent.analyze_intent(query)
            assert result["task_type"] == "search"
            assert result["agent"] == "search_agent"
            assert result["confidence"] in ["medium", "high"]
            assert len(result["matched_keywords"]) > 0

    def test_supervisor_analyze_intent_rag(self):
        """Test intent analysis for RAG queries."""
        agent = SupervisorAgent()

        rag_queries = [
            "查看这个文档",
            "参考操作手册",
            "有没有教程",
            "如何使用API",
            "怎么配置",
            "使用方法",
        ]

        for query in rag_queries:
            result = agent.analyze_intent(query)
            assert result["task_type"] == "rag"
            assert result["agent"] == "rag_agent"
            assert result["confidence"] in ["medium", "high"]
            assert len(result["matched_keywords"]) > 0

    def test_supervisor_analyze_intent_process(self):
        """Test intent analysis for process queries."""
        agent = SupervisorAgent()

        process_queries = [
            "处理这个任务",
            "查看当前状态",
            "进度到哪里了",
            "任务完成了吗",
        ]

        for query in process_queries:
            result = agent.analyze_intent(query)
            assert result["task_type"] == "process"
            assert result["agent"] == "process_agent"
            assert result["confidence"] in ["medium", "high"]
            assert len(result["matched_keywords"]) > 0

    def test_supervisor_analyze_intent_general(self):
        """Test intent analysis for general queries (no keywords)."""
        agent = SupervisorAgent()

        general_queries = [
            "你好",
            "帮我分析一下",
            "什么意思",
            "介绍你自己",
            "未知类型的请求",
        ]

        for query in general_queries:
            result = agent.analyze_intent(query)
            assert result["task_type"] == "general"
            assert result["agent"] == "general_agent"
            assert result["confidence"] == "low"
            assert len(result["matched_keywords"]) == 0

    def test_supervisor_analyze_intent_multiple_keywords(self):
        """Test intent analysis with multiple matching keywords."""
        agent = SupervisorAgent()

        # Query with multiple search keywords
        result = agent.analyze_intent("搜索并查找相关信息")
        assert result["task_type"] == "search"
        assert result["confidence"] == "high"
        assert len(result["matched_keywords"]) == 2

    def test_supervisor_analyze_intent_case_insensitive(self):
        """Test intent analysis is case-insensitive."""
        agent = SupervisorAgent()

        result_lower = agent.analyze_intent("搜索信息")
        result_upper = agent.analyze_intent("搜索信息")

        assert result_lower["task_type"] == result_upper["task_type"]
        assert result_lower["agent"] == result_upper["agent"]

    def test_format_search_response(self):
        """Test formatting search response."""
        agent = SupervisorAgent()
        results = [
            {"title": "Result 1", "url": "http://example.com/1"},
            {"title": "Result 2", "url": "http://example.com/2"},
        ]
        query = "test query"

        response = agent.format_search_response(results, query)

        assert response["task_type"] == "search"
        assert response["query"] == query
        assert response["count"] == 2
        assert response["status"] == "success"
        assert len(response["results"]) == 2

    def test_format_search_response_empty(self):
        """Test formatting search response with no results."""
        agent = SupervisorAgent()

        response = agent.format_search_response([], "test")

        assert response["task_type"] == "search"
        assert response["count"] == 0
        assert response["status"] == "no_results"
        assert response["results"] == []

    def test_format_rag_response(self):
        """Test formatting RAG response."""
        agent = SupervisorAgent()
        answer = "This is the generated answer."
        sources = [
            {"doc_id": "1", "content": "Source 1"},
            {"doc_id": "2", "content": "Source 2"},
        ]

        response = agent.format_rag_response(answer, sources)

        assert response["task_type"] == "rag"
        assert response["answer"] == answer
        assert response["source_count"] == 2
        assert response["status"] == "success"
        assert len(response["sources"]) == 2

    def test_format_rag_response_empty_sources(self):
        """Test formatting RAG response with no sources."""
        agent = SupervisorAgent()

        response = agent.format_rag_response("Answer", [])

        assert response["task_type"] == "rag"
        assert response["answer"] == "Answer"
        assert response["source_count"] == 0

    def test_format_process_response(self):
        """Test formatting process response."""
        agent = SupervisorAgent()
        status = {
            "status": "running",
            "progress": 50,
            "message": "Processing task",
            "details": {"step": "2/4"},
        }

        response = agent.format_process_response(status)

        assert response["task_type"] == "process"
        assert response["status"] == "running"
        assert response["progress"] == 50
        assert response["message"] == "Processing task"
        assert response["details"] == {"step": "2/4"}

    def test_format_process_response_minimal(self):
        """Test formatting process response with minimal data."""
        agent = SupervisorAgent()
        status = {}

        response = agent.format_process_response(status)

        assert response["task_type"] == "process"
        assert response["status"] == "unknown"
        assert response["progress"] == 0
        assert response["message"] == ""
        assert response["details"] == {}

    def test_format_general_response(self):
        """Test formatting general response."""
        agent = SupervisorAgent()
        messages = ["Hello", "How can I help?", "I'm ready"]

        response = agent.format_general_response(messages)

        assert response["task_type"] == "general"
        assert response["message_count"] == 3
        assert response["status"] == "success"
        assert len(response["messages"]) == 3

    def test_format_general_response_empty(self):
        """Test formatting general response with no messages."""
        agent = SupervisorAgent()

        response = agent.format_general_response([])

        assert response["task_type"] == "general"
        assert response["message_count"] == 0
        assert response["messages"] == []

    def test_supervisor_inherits_base_agent(self):
        """Test SupervisorAgent properly inherits BaseAgent."""
        agent = SupervisorAgent()

        # Should have BaseAgent methods
        assert hasattr(agent, "get_system_prompt")
        assert hasattr(agent, "add_tool")
        assert hasattr(agent, "_format_tools")

        # System prompt should include role
        prompt = agent.get_system_prompt()
        assert "task_coordinator" in prompt

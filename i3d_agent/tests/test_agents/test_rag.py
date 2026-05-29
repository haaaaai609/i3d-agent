"""Tests for RAGAgent class."""

import pytest
from unittest.mock import patch, MagicMock

from i3d_agent.agents.base import AgentConfig
from i3d_agent.agents.rag import RAGAgent


class TestRAGAgent:
    """Tests for RAGAgent class."""

    def test_rag_agent_creation_default(self):
        """Test RAGAgent creation with default configuration."""
        agent = RAGAgent()

        assert agent.config.name == "rag"
        assert agent.config.role == "technical_assistant"
        assert len(agent.tools) == 4

        # Check tool names
        tool_names = {tool["name"] for tool in agent.tools}
        expected_tools = {
            "retrieve_documents",
            "search_api_reference",
            "get_deployment_guide",
            "find_troubleshooting_steps",
        }
        assert tool_names == expected_tools

    def test_rag_agent_creation_custom_config(self):
        """Test RAGAgent creation with custom configuration."""
        config = AgentConfig(
            name="custom_rag",
            role="helper",
            instructions="Custom instructions for RAG.",
        )
        agent = RAGAgent(config=config)

        assert agent.config.name == "custom_rag"
        assert agent.config.role == "helper"
        assert agent.config.instructions == "Custom instructions for RAG."

    def test_rag_agent_tools(self):
        """Test RAGAgent has correct tools configured."""
        agent = RAGAgent()

        # Verify each tool has required fields
        for tool in agent.tools:
            assert "name" in tool
            assert "description" in tool
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)

    def test_rag_agent_answer_basic(self):
        """Test RAGAgent answer method with basic question."""
        agent = RAGAgent()

        # Mock retrieve_documents to return stub data
        mock_docs = [
            {
                "doc_id": "doc-1",
                "title": "Test Document",
                "content": "Test content",
                "score": 0.9,
                "metadata": {},
            }
        ]

        with patch("i3d_agent.agents.rag.retrieve_documents") as mock_retrieve:
            mock_retrieve.return_value = mock_docs

            result = agent.answer("What is the API endpoint for search?")

            assert result["status"] == "success"
            assert result["question"] == "What is the API endpoint for search?"
            assert "stub response" in result["answer"].lower()
            assert len(result["sources"]) == 1
            assert result["sources"][0]["doc_id"] == "doc-1"

    def test_rag_agent_answer_empty_question(self):
        """Test RAGAgent answer with empty question returns error."""
        agent = RAGAgent()

        result = agent.answer("")

        assert result["status"] == "error"
        assert result["question"] == ""
        assert result["answer"] == ""
        assert "cannot be empty" in result["error"].lower()

    def test_rag_agent_answer_whitespace_question(self):
        """Test RAGAgent answer with whitespace-only question returns error."""
        agent = RAGAgent()

        result = agent.answer("   ")

        assert result["status"] == "error"
        assert "cannot be empty" in result["error"].lower()

    def test_rag_agent_answer_no_results(self):
        """Test RAGAgent answer when no documents are found."""
        agent = RAGAgent()

        with patch("i3d_agent.agents.rag.retrieve_documents") as mock_retrieve:
            mock_retrieve.return_value = []

            result = agent.answer("Some obscure question")

            assert result["status"] == "no_results"
            assert "no relevant documents" in result["answer"].lower()
            assert result["sources"] == []

    def test_rag_agent_answer_with_tenant_id(self):
        """Test RAGAgent answer with tenant_id parameter."""
        agent = RAGAgent()

        mock_docs = [
            {
                "doc_id": "doc-1",
                "title": "Test",
                "content": "Content",
                "score": 0.8,
                "metadata": {},
            }
        ]

        with patch("i3d_agent.agents.rag.retrieve_documents") as mock_retrieve:
            mock_retrieve.return_value = mock_docs

            result = agent.answer(
                "Test question",
                tenant_id="tenant-123",
            )

            assert result["status"] == "success"
            mock_retrieve.assert_called_once_with(
                query="Test question",
                knowledge_base="default",
                top_k=5,
                tenant_id="tenant-123",
            )

    def test_rag_agent_answer_handles_exception(self):
        """Test RAGAgent answer handles exceptions gracefully."""
        agent = RAGAgent()

        with patch("i3d_agent.agents.rag.retrieve_documents") as mock_retrieve:
            mock_retrieve.side_effect = Exception("RAG service unavailable")

            result = agent.answer("Test question")

            assert result["status"] == "error"
            assert result["answer"] == ""
            assert "unavailable" in result["error"].lower()

    def test_rag_agent_get_api_info(self):
        """Test RAGAgent get_api_info method."""
        agent = RAGAgent()

        mock_api_info = {
            "endpoint": "/api/v1/search/3d",
            "method": "POST",
            "description": "Search for 3D models",
        }

        with patch("i3d_agent.agents.rag.search_api_reference") as mock_search:
            mock_search.return_value = mock_api_info

            result = agent.get_api_info("/api/v1/search/3d", method="POST")

            assert result["status"] == "success"
            assert result["data"]["endpoint"] == "/api/v1/search/3d"
            assert result["data"]["method"] == "POST"

    def test_rag_agent_get_api_info_error(self):
        """Test RAGAgent get_api_info handles errors."""
        agent = RAGAgent()

        with patch("i3d_agent.agents.rag.search_api_reference") as mock_search:
            mock_search.side_effect = ValueError("Invalid endpoint")

            result = agent.get_api_info("invalid")

            assert result["status"] == "error"
            assert "invalid endpoint" in result["error"].lower()

    def test_rag_agent_get_deployment_info(self):
        """Test RAGAgent get_deployment_info method."""
        agent = RAGAgent()

        mock_guide = {
            "component": "infer-engineer",
            "overview": "Component description",
            "installation": ["Step 1", "Step 2"],
        }

        with patch("i3d_agent.agents.rag.get_deployment_guide") as mock_get:
            mock_get.return_value = mock_guide

            result = agent.get_deployment_info("infer-engineer")

            assert result["status"] == "success"
            assert result["data"]["component"] == "infer-engineer"

    def test_rag_agent_get_deployment_info_with_tenant(self):
        """Test RAGAgent get_deployment_info with tenant_id."""
        agent = RAGAgent()

        mock_guide = {"component": "rag-service", "overview": "Overview"}

        with patch("i3d_agent.agents.rag.get_deployment_guide") as mock_get:
            mock_get.return_value = mock_guide

            agent.get_deployment_info("rag-service", tenant_id="tenant-456")

            mock_get.assert_called_once_with(
                component="rag-service",
                tenant_id="tenant-456",
            )

    def test_rag_agent_get_troubleshooting_info(self):
        """Test RAGAgent get_troubleshooting_info method."""
        agent = RAGAgent()

        mock_steps = [
            {
                "error_code": "ERR-5001",
                "diagnosis": "Connection timeout",
                "solutions": ["Check network", "Increase timeout"],
            }
        ]

        with patch("i3d_agent.agents.rag.find_troubleshooting_steps") as mock_find:
            mock_find.return_value = mock_steps

            result = agent.get_troubleshooting_info(
                error_code="ERR-5001",
                component="api-gateway",
            )

            assert result["status"] == "success"
            assert len(result["data"]) == 1
            assert result["data"][0]["error_code"] == "ERR-5001"

    def test_rag_agent_get_troubleshooting_info_all_params(self):
        """Test RAGAgent get_troubleshooting_info with all parameters."""
        agent = RAGAgent()

        mock_steps = [
            {
                "error_code": "E001",
                "error_pattern": "Database connection failed",
                "component": "database",
                "solutions": ["Check credentials"],
            }
        ]

        with patch("i3d_agent.agents.rag.find_troubleshooting_steps") as mock_find:
            mock_find.return_value = mock_steps

            agent.get_troubleshooting_info(
                error_code="E001",
                error_message="Database connection failed",
                component="database",
                tenant_id="tenant-789",
            )

            mock_find.assert_called_once_with(
                error_code="E001",
                error_message="Database connection failed",
                component="database",
                tenant_id="tenant-789",
            )

    def test_rag_agent_inherits_base_agent(self):
        """Test RAGAgent properly inherits BaseAgent."""
        agent = RAGAgent()

        # Should have BaseAgent methods
        assert hasattr(agent, "get_system_prompt")
        assert hasattr(agent, "add_tool")
        assert hasattr(agent, "_format_tools")

        # System prompt should include role
        prompt = agent.get_system_prompt()
        assert "technical_assistant" in prompt
        assert "retrieve_documents" in prompt

    @pytest.mark.integration
    def test_rag_agent_answer_integration(self):
        """Integration test for RAGAgent answer (requires actual RAG service)."""
        # This test requires actual RAG service access
        agent = RAGAgent()

        # Test would look like this with real RAG service:
        # result = agent.answer(
        #     question="How do I configure the 3D search API?",
        #     tenant_id="test-tenant",
        # )
        # assert result["status"] in ["success", "no_results", "error"]

        # Skip if no RAG service
        pytest.skip("Integration test - requires RAG service")

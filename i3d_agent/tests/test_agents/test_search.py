"""Tests for SearchAgent class."""

import pytest
from unittest.mock import patch, MagicMock

from i3d_agent.agents.base import AgentConfig
from i3d_agent.agents.search import SearchAgent


class TestSearchAgent:
    """Tests for SearchAgent class."""

    def test_search_agent_init_default(self):
        """Test SearchAgent initialization with default config."""
        agent = SearchAgent()

        assert agent.config.name == "search"
        assert agent.config.role == "model_searcher"
        assert len(agent.tools) == 4

        # Check tool names
        tool_names = {tool["name"] for tool in agent.tools}
        expected_tools = {"search_3d_model", "search_2d_image", "filter_by_attributes", "get_model_details"}
        assert tool_names == expected_tools

    def test_search_agent_init_custom_config(self):
        """Test SearchAgent initialization with custom config."""
        config = AgentConfig(
            name="custom_search",
            role="finder",
            instructions="Custom instructions.",
        )
        agent = SearchAgent(config=config)

        assert agent.config.name == "custom_search"
        assert agent.config.role == "finder"
        assert agent.config.instructions == "Custom instructions."

    def test_search_3d_type(self):
        """Test search with 3D type."""
        agent = SearchAgent()

        # Mock the search_3d_model function
        mock_results = [
            {"item_code": "BOLT-001", "similarity": 0.95, "file_type": "step"},
            {"item_code": "BOLT-002", "similarity": 0.87, "file_type": "step"},
        ]

        with patch("i3d_agent.agents.search.search_3d_model") as mock_search:
            mock_search.return_value = mock_results

            result = agent.search(
                query="BOLT-TEST",
                search_type="3d",
                params={"file_type": "step", "top_k": 10},
            )

            assert result["search_type"] == "3d"
            assert result["status"] == "success"
            assert result["count"] == 2
            assert len(result["results"]) == 2
            assert result["item_code"] == "BOLT-TEST"
            assert result["file_type"] == "step"

            # Verify the mock was called correctly
            mock_search.assert_called_once_with(
                item_code="BOLT-TEST",
                file_type="step",
                top_k=10,
                tenant_id=None,
            )

    def test_search_3d_with_filters(self):
        """Test 3D search with attribute filters."""
        agent = SearchAgent()

        # Mock results before filtering
        all_results = [
            {
                "item_code": "BOLT-001",
                "similarity": 0.95,
                "metadata": {"material": "steel", "weight": 1.5},
            },
            {
                "item_code": "BOLT-002",
                "similarity": 0.87,
                "metadata": {"material": "aluminum", "weight": 0.5},
            },
            {
                "item_code": "BOLT-003",
                "similarity": 0.80,
                "metadata": {"material": "steel", "weight": 2.5},
            },
        ]

        # Mock both search_3d_model and filter_by_attributes
        with patch("i3d_agent.agents.search.search_3d_model") as mock_search, \
             patch("i3d_agent.agents.search.filter_by_attributes") as mock_filter:
            mock_search.return_value = all_results
            mock_filter.return_value = [all_results[0], all_results[2]]  # Filter to steel only

            result = agent.search(
                query="BOLT-TEST",
                search_type="3d",
                params={
                    "file_type": "step",
                    "top_k": 10,
                    "filters": {"material": "steel", "weight_min": 1.0, "weight_max": 3.0},
                },
            )

            assert result["count"] == 2
            mock_filter.assert_called_once()

    def test_search_2d_type(self):
        """Test search with 2D type."""
        agent = SearchAgent()

        # Mock the search_2d_image function
        mock_results = [
            {"image_id": "IMG-001", "similarity": 0.92, "url": "http://example.com/img1.png"},
            {"image_id": "IMG-002", "similarity": 0.85, "url": "http://example.com/img2.png"},
        ]

        with patch("i3d_agent.agents.search.search_2d_image") as mock_search:
            mock_search.return_value = mock_results

            result = agent.search(
                query="iVBORw0KGgoAAAANSUhEUg...",  # Mock base64 data
                search_type="2d",
                params={"file_type": "png", "top_k": 5},
            )

            assert result["search_type"] == "2d"
            assert result["status"] == "success"
            assert result["count"] == 2
            assert len(result["results"]) == 2
            assert result["file_type"] == "png"

            # Verify the mock was called correctly
            mock_search.assert_called_once_with(
                image_base64="iVBORw0KGgoAAAANSUhEUg...",
                file_type="png",
                top_k=5,
                tenant_id=None,
            )

    def test_search_text_type(self):
        """Test search with text type (not yet implemented)."""
        agent = SearchAgent()

        result = agent.search(
            query="search query",
            search_type="text",
            params={},
        )

        assert result["search_type"] == "text"
        assert result["status"] == "not_implemented"
        assert result["count"] == 0
        assert result["results"] == []
        assert "not yet implemented" in result["message"].lower()

    def test_search_invalid_type(self):
        """Test search with invalid type raises ValueError."""
        agent = SearchAgent()

        result = agent.search(
            query="test",
            search_type="invalid",
            params={},
        )

        assert result["status"] == "error"
        assert "error" in result
        assert "Invalid search_type" in result["error"]

    def test_search_no_results(self):
        """Test search returns no results."""
        agent = SearchAgent()

        with patch("i3d_agent.agents.search.search_3d_model") as mock_search:
            mock_search.return_value = []

            result = agent.search(
                query="UNKNOWN-CODE",
                search_type="3d",
                params={},
            )

            assert result["search_type"] == "3d"
            assert result["status"] == "no_results"
            assert result["count"] == 0
            assert result["results"] == []

    def test_search_with_default_params(self):
        """Test search with default parameters."""
        agent = SearchAgent()

        with patch("i3d_agent.agents.search.search_3d_model") as mock_search:
            mock_search.return_value = []

            agent.search(query="TEST", search_type="3d")

            # Should use defaults
            mock_search.assert_called_once_with(
                item_code="TEST",
                file_type="step",
                top_k=10,
                tenant_id=None,
            )

    def test_search_with_tenant_id(self):
        """Test search with tenant_id parameter."""
        agent = SearchAgent()

        with patch("i3d_agent.agents.search.search_3d_model") as mock_search:
            mock_search.return_value = []

            agent.search(
                query="TEST",
                search_type="3d",
                tenant_id="tenant-123",
            )

            mock_search.assert_called_once_with(
                item_code="TEST",
                file_type="step",
                top_k=10,
                tenant_id="tenant-123",
            )

    def test_search_handles_exception(self):
        """Test search handles exceptions gracefully."""
        agent = SearchAgent()

        with patch("i3d_agent.agents.search.search_3d_model") as mock_search:
            mock_search.side_effect = Exception("API error")

            result = agent.search(
                query="TEST",
                search_type="3d",
                params={},
            )

            assert result["status"] == "error"
            assert result["count"] == 0
            assert result["results"] == []
            assert "API error" in result["error"]

    def test_get_details_success(self):
        """Test get_details returns model details."""
        agent = SearchAgent()

        mock_details = {
            "item_code": "BOLT-123",
            "name": "Steel Bolt M8",
            "material": "steel",
            "weight": 0.05,
        }

        with patch("i3d_agent.agents.search.get_model_details") as mock_get:
            mock_get.return_value = mock_details

            result = agent.get_details("BOLT-123")

            assert result["status"] == "success"
            assert result["details"] == mock_details

    def test_get_details_error(self):
        """Test get_details handles errors."""
        agent = SearchAgent()

        with patch("i3d_agent.agents.search.get_model_details") as mock_get:
            mock_get.side_effect = Exception("Not found")

            result = agent.get_details("UNKNOWN")

            assert result["status"] == "error"
            assert result["error"] == "Not found"
            assert result["item_code"] == "UNKNOWN"

    def test_search_agent_inherits_base_agent(self):
        """Test SearchAgent properly inherits BaseAgent."""
        agent = SearchAgent()

        # Should have BaseAgent methods
        assert hasattr(agent, "get_system_prompt")
        assert hasattr(agent, "add_tool")
        assert hasattr(agent, "_format_tools")

        # System prompt should include role
        prompt = agent.get_system_prompt()
        assert "model_searcher" in prompt

    @pytest.mark.integration
    def test_search_agent_execute_integration(self):
        """Integration test for SearchAgent execute (requires actual API)."""
        # This test requires actual API access and should be run manually
        # or with proper test infrastructure
        agent = SearchAgent()

        # Test would look like this with real API:
        # result = agent.search(
        #     query="BOLT-TEST",
        #     search_type="3d",
        #     params={"file_type": "step", "top_k": 5},
        #     tenant_id="test-tenant",
        # )
        # assert result["search_type"] == "3d"
        # assert result["status"] in ["success", "no_results", "error"]

        # Skip if no API access
        pytest.skip("Integration test - requires API access")

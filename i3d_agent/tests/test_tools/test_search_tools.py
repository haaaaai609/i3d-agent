"""
Tests for search tools module.

This module contains both unit and integration tests for the I3D search tools.
Integration tests require the search API services to be running.
"""

import base64
from unittest.mock import Mock, patch

import pytest
import httpx

from i3d_agent.tools.search_tools import (
    search_3d_model,
    search_2d_image,
    filter_by_attributes,
    get_model_details,
)


class TestSearch3DModel:
    """Tests for search_3d_model tool."""

    @pytest.mark.integration
    def test_search_3d_model_success(self):
        """Integration test: successful 3D model search."""
        with patch("i3d_agent.tools.search_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "results": [
                    {
                        "item_code": "BOLT-1235",
                        "similarity": 0.95,
                        "file_type": "step",
                        "metadata": {"material": "steel", "weight": 0.5},
                    },
                    {
                        "item_code": "BOLT-1236",
                        "similarity": 0.87,
                        "file_type": "step",
                        "metadata": {"material": "steel", "weight": 0.6},
                    },
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            results = search_3d_model("BOLT-1234", file_type="step", top_k=5)

            assert len(results) == 2
            assert results[0]["item_code"] == "BOLT-1235"
            assert results[0]["similarity"] == 0.95

    @pytest.mark.integration
    def test_search_3d_model_api_error(self):
        """Integration test: API error handling."""
        with patch("i3d_agent.tools.search_tools.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.HTTPError("Connection refused")
            )

            with pytest.raises(httpx.HTTPError):
                search_3d_model("BOLT-1234")

    def test_search_3d_model_empty_item_code(self):
        """Unit test: validation of empty item_code."""
        with pytest.raises(ValueError, match="item_code cannot be empty"):
            search_3d_model("")

    def test_search_3d_model_invalid_top_k(self):
        """Unit test: validation of top_k range."""
        with pytest.raises(ValueError, match="top_k must be between 1 and 100"):
            search_3d_model("BOLT-1234", top_k=0)

        with pytest.raises(ValueError, match="top_k must be between 1 and 100"):
            search_3d_model("BOLT-1234", top_k=101)


class TestSearch2DImage:
    """Tests for search_2d_image tool."""

    @pytest.mark.integration
    def test_search_2d_image_success(self):
        """Integration test: successful 2D image search."""
        with patch("i3d_agent.tools.search_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "results": [
                    {
                        "image_id": "IMG-001",
                        "similarity": 0.92,
                        "url": "https://example.com/img1.png",
                        "metadata": {"category": "bolt", "angle": "top"},
                    }
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            # Create dummy base64 data
            img_data = base64.b64encode(b"fake_image_data").decode()

            results = search_2d_image(img_data, file_type="png", top_k=5)

            assert len(results) == 1
            assert results[0]["image_id"] == "IMG-001"

    @pytest.mark.integration
    def test_search_2d_image_api_error(self):
        """Integration test: API error handling."""
        with patch("i3d_agent.tools.search_tools.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.HTTPError("API timeout")
            )

            with pytest.raises(httpx.HTTPError):
                search_2d_image("invalid_base64_data")

    def test_search_2d_image_empty_base64(self):
        """Unit test: validation of empty base64 string."""
        with pytest.raises(ValueError, match="image_base64 cannot be empty"):
            search_2d_image("")


class TestFilterByAttributes:
    """Tests for filter_by_attributes tool."""

    def test_filter_by_material(self):
        """Unit test: filtering by material."""
        results = [
            {"item_code": "1", "metadata": {"material": "steel", "weight": 1.0}},
            {"item_code": "2", "metadata": {"material": "aluminum", "weight": 0.5}},
            {"item_code": "3", "metadata": {"material": "steel", "weight": 2.0}},
        ]

        filtered = filter_by_attributes(results, material="steel")

        assert len(filtered) == 2
        assert all(r["metadata"]["material"] == "steel" for r in filtered)

    def test_filter_by_weight_range(self):
        """Unit test: filtering by weight range."""
        results = [
            {"item_code": "1", "metadata": {"weight": 0.1}},
            {"item_code": "2", "metadata": {"weight": 0.5}},
            {"item_code": "3", "metadata": {"weight": 5.0}},
        ]

        filtered = filter_by_attributes(results, weight_min=0.2, weight_max=2.0)

        assert len(filtered) == 1
        assert filtered[0]["item_code"] == "2"

    def test_filter_by_all_attributes(self):
        """Unit test: filtering by all attributes."""
        results = [
            {
                "item_code": "1",
                "metadata": {"material": "steel", "weight": 1.5},
            },
            {
                "item_code": "2",
                "metadata": {"material": "steel", "weight": 0.3},
            },
            {
                "item_code": "3",
                "metadata": {"material": "aluminum", "weight": 1.5},
            },
        ]

        filtered = filter_by_attributes(
            results, material="steel", weight_min=1.0, weight_max=2.0
        )

        assert len(filtered) == 1
        assert filtered[0]["item_code"] == "1"

    def test_filter_no_filters(self):
        """Unit test: no filters applied returns all results."""
        results = [
            {"item_code": "1", "metadata": {"material": "steel"}},
            {"item_code": "2", "metadata": {"material": "aluminum"}},
        ]

        filtered = filter_by_attributes(results)

        assert len(filtered) == 2

    def test_filter_invalid_results_type(self):
        """Unit test: validation of results parameter."""
        with pytest.raises(ValueError, match="results must be a list"):
            filter_by_attributes("not_a_list")


class TestGetModelDetails:
    """Tests for get_model_details tool."""

    @pytest.mark.integration
    def test_get_model_details_success(self):
        """Integration test: successful model details retrieval."""
        with patch("i3d_agent.tools.search_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "item_code": "BOLT-1234",
                "name": "Hex Bolt M8",
                "description": "Standard hex bolt",
                "material": "steel",
                "weight": 0.05,
                "dimensions": {"length": 50, "width": 8, "height": 8},
                "files": ["step", "stl"],
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            details = get_model_details("BOLT-1234")

            assert details["item_code"] == "BOLT-1234"
            assert details["material"] == "steel"
            assert details["weight"] == 0.05

    @pytest.mark.integration
    def test_get_model_details_not_found(self):
        """Integration test: model not found error."""
        with patch("i3d_agent.tools.search_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not found", request=Mock(), response=mock_response
            )
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(httpx.HTTPError):
                get_model_details("NONEXISTENT")

    def test_get_model_details_empty_item_code(self):
        """Unit test: validation of empty item_code."""
        with pytest.raises(ValueError, match="item_code cannot be empty"):
            get_model_details("")

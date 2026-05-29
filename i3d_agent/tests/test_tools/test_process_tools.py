"""
Tests for process tools module.

This module contains both unit and integration tests for the I3D process tools.
Integration tests require the XXL-Job API services to be running.
"""

from unittest.mock import Mock, patch

import pytest
import httpx

from i3d_agent.tools.process_tools import (
    get_task_status,
    get_processing_history,
    retry_failed_task,
    diagnose_error,
)


class TestGetTaskStatus:
    """Tests for get_task_status tool."""

    @pytest.mark.integration
    def test_get_task_status_success(self):
        """Integration test: successful task status query."""
        with patch("i3d_agent.tools.process_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "task_id": "TASK-12345",
                "status": "running",
                "progress": 65,
                "stage": "parsing",
                "created_at": "2024-05-29T10:00:00Z",
                "updated_at": "2024-05-29T10:05:00Z",
                "error_message": None,
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            status = get_task_status("TASK-12345")

            assert status["task_id"] == "TASK-12345"
            assert status["status"] == "running"
            assert status["progress"] == 65

    @pytest.mark.integration
    def test_get_task_status_failed_task(self):
        """Integration test: querying failed task with error message."""
        with patch("i3d_agent.tools.process_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "task_id": "TASK-12346",
                "status": "failed",
                "progress": 45,
                "stage": "validation",
                "created_at": "2024-05-29T09:00:00Z",
                "updated_at": "2024-05-29T09:02:00Z",
                "error_message": "Validation failed: Invalid geometry data",
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            status = get_task_status("TASK-12346")

            assert status["status"] == "failed"
            assert status["error_message"] is not None
            assert "Validation failed" in status["error_message"]

    @pytest.mark.integration
    def test_get_task_status_api_error(self):
        """Integration test: API error handling."""
        with patch("i3d_agent.tools.process_tools.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.HTTPError("Connection refused")
            )

            with pytest.raises(httpx.HTTPError, match="Task status API request failed"):
                get_task_status("TASK-12345")

    def test_get_task_status_empty_task_id(self):
        """Unit test: validation of empty task_id."""
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            get_task_status("")

    def test_get_task_status_whitespace_task_id(self):
        """Unit test: validation of whitespace task_id."""
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            get_task_status("   ")


class TestGetProcessingHistory:
    """Tests for get_processing_history tool."""

    @pytest.mark.integration
    def test_get_processing_history_success(self):
        """Integration test: successful processing history retrieval."""
        with patch("i3d_agent.tools.process_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "history": [
                    {
                        "task_id": "TASK-10001",
                        "item_code": "BOLT-1234",
                        "status": "success",
                        "timestamp": "2024-05-28T10:00:00Z",
                        "duration_seconds": 45,
                        "file_type": "step",
                        "error_message": None,
                    },
                    {
                        "task_id": "TASK-10002",
                        "item_code": "BOLT-1234",
                        "status": "failed",
                        "timestamp": "2024-05-28T11:00:00Z",
                        "duration_seconds": 12,
                        "file_type": "step",
                        "error_message": "File corrupted",
                    },
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            history = get_processing_history("BOLT-1234")

            assert len(history) == 2
            assert history[0]["item_code"] == "BOLT-1234"
            assert history[0]["status"] == "success"
            assert history[1]["status"] == "failed"

    @pytest.mark.integration
    def test_get_processing_history_empty(self):
        """Integration test: no history for item."""
        with patch("i3d_agent.tools.process_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"history": []}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            history = get_processing_history("NEW-ITEM-999")

            assert len(history) == 0

    @pytest.mark.integration
    def test_get_processing_history_api_error(self):
        """Integration test: API error handling."""
        with patch("i3d_agent.tools.process_tools.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.HTTPError("API timeout")
            )

            with pytest.raises(httpx.HTTPError, match="Processing history API request failed"):
                get_processing_history("BOLT-1234")

    def test_get_processing_history_empty_item_code(self):
        """Unit test: validation of empty item_code."""
        with pytest.raises(ValueError, match="item_code cannot be empty"):
            get_processing_history("")


class TestRetryFailedTask:
    """Tests for retry_failed_task tool."""

    @pytest.mark.integration
    def test_retry_failed_task_success(self):
        """Integration test: successful task retry."""
        with patch("i3d_agent.tools.process_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "new_task_id": "TASK-99999",
                "original_task_id": "TASK-12345",
                "message": "Retry initiated successfully",
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            result = retry_failed_task("TASK-12345")

            assert result["success"] is True
            assert result["new_task_id"] == "TASK-99999"
            assert result["original_task_id"] == "TASK-12345"

    @pytest.mark.integration
    def test_retry_failed_task_not_found(self):
        """Integration test: retry on non-existent task."""
        with patch("i3d_agent.tools.process_tools.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Task not found", request=Mock(), response=mock_response
            )
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            with pytest.raises(httpx.HTTPError, match="Retry task API request failed"):
                retry_failed_task("NONEXISTENT-TASK")

    @pytest.mark.integration
    def test_retry_failed_task_api_error(self):
        """Integration test: API error handling."""
        with patch("i3d_agent.tools.process_tools.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.HTTPError("Service unavailable")
            )

            with pytest.raises(httpx.HTTPError, match="Retry task API request failed"):
                retry_failed_task("TASK-12345")

    def test_retry_failed_task_empty_task_id(self):
        """Unit test: validation of empty task_id."""
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            retry_failed_task("")


class TestDiagnoseError:
    """Tests for diagnose_error tool."""

    def test_diagnose_file_format_error(self):
        """Unit test: diagnosis of file format errors."""
        result = diagnose_error(
            "Invalid file format: unsupported STEP version",
            component="parser"
        )

        assert result["error_type"] == "file_format_error"
        assert result["severity"] == "high"
        assert len(result["suggested_solutions"]) > 0
        assert len(result["related_docs"]) > 0

    def test_diagnose_parsing_error(self):
        """Unit test: diagnosis of parsing errors."""
        result = diagnose_error(
            "Failed to parse geometry data: syntax error",
            component="parser"
        )

        assert result["error_type"] == "parsing_error"
        assert result["severity"] == "high"
        assert "parse" in result["likely_cause"].lower()

    def test_diagnose_network_error(self):
        """Unit test: diagnosis of network errors."""
        result = diagnose_error(
            "Connection timeout while uploading to storage",
            component="uploader"
        )

        assert result["error_type"] == "network_error"
        assert result["severity"] == "medium"
        assert any("network" in sol.lower() or "timeout" in sol.lower()
                   for sol in result["suggested_solutions"])

    def test_diagnose_storage_error(self):
        """Unit test: diagnosis of storage errors."""
        result = diagnose_error(
            "Insufficient disk space on storage server",
            component="storage"
        )

        assert result["error_type"] == "storage_error"
        assert result["severity"] == "high"
        assert any("space" in sol.lower() for sol in result["suggested_solutions"])

    def test_diagnose_validation_error(self):
        """Unit test: diagnosis of validation errors."""
        result = diagnose_error(
            "Validation constraint violation: invalid dimension value",
            component="validator"
        )

        assert result["error_type"] == "validation_error"
        assert result["severity"] == "medium"
        assert len(result["suggested_solutions"]) > 0

    def test_diagnose_unknown_error(self):
        """Unit test: diagnosis of unknown errors."""
        result = diagnose_error(
            "Something unexpected happened during processing",
            component="unknown"
        )

        assert result["error_type"] == "unknown_error"
        assert result["severity"] == "medium"
        assert any("support" in sol.lower() for sol in result["suggested_solutions"])

    def test_diagnose_error_empty_message(self):
        """Unit test: validation of empty error_message."""
        with pytest.raises(ValueError, match="error_message cannot be empty"):
            diagnose_error("")

    def test_diagnose_error_whitespace_message(self):
        """Unit test: validation of whitespace error_message."""
        with pytest.raises(ValueError, match="error_message cannot be empty"):
            diagnose_error("   ")

    def test_diagnose_error_case_insensitive(self):
        """Unit test: pattern matching is case-insensitive."""
        result = diagnose_error("INVALID FORMAT DETECTED")

        assert result["error_type"] == "file_format_error"

    def test_diagnose_error_with_tenant_id(self):
        """Unit test: tenant_id parameter is accepted."""
        # This should not raise any errors
        result = diagnose_error(
            "Connection timeout",
            component="network",
            tenant_id="tenant1"
        )

        assert result["error_type"] == "network_error"

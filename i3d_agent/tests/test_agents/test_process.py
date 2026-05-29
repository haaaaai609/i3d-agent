"""Tests for ProcessAgent class."""

import pytest
from unittest.mock import patch

from i3d_agent.agents.base import AgentConfig
from i3d_agent.agents.process import ProcessAgent


class TestProcessAgent:
    """Tests for ProcessAgent class."""

    def test_process_agent_creation(self):
        """Test ProcessAgent creation with default config."""
        agent = ProcessAgent()

        assert agent.config.name == "process"
        assert agent.config.role == "task_processor"
        assert len(agent.tools) == 4

        # Check tool names
        tool_names = {tool["name"] for tool in agent.tools}
        expected_tools = {
            "get_task_status",
            "get_processing_history",
            "retry_failed_task",
            "diagnose_error",
        }
        assert tool_names == expected_tools

    def test_process_agent_init_custom_config(self):
        """Test ProcessAgent initialization with custom config."""
        config = AgentConfig(
            name="custom_process",
            role="processor",
            instructions="Custom instructions.",
        )
        agent = ProcessAgent(config=config)

        assert agent.config.name == "custom_process"
        assert agent.config.role == "processor"
        assert agent.config.instructions == "Custom instructions."

    def test_get_status_success(self):
        """Test get_status returns task status."""
        agent = ProcessAgent()

        mock_task_data = {
            "task_id": "TASK-12345",
            "status": "running",
            "progress": 65,
            "stage": "validation",
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-01T10:05:00Z",
        }

        with patch("i3d_agent.agents.process.get_task_status") as mock_get:
            mock_get.return_value = mock_task_data

            result = agent.get_status("TASK-12345")

            assert result["status"] == "success"
            assert result["task_id"] == "TASK-12345"
            assert result["task_status"] == "running"
            assert result["progress"] == 65

            # Verify the mock was called correctly
            mock_get.assert_called_once_with(task_id="TASK-12345", tenant_id=None)

    def test_get_status_with_tenant_id(self):
        """Test get_status with tenant_id parameter."""
        agent = ProcessAgent()

        mock_task_data = {
            "task_id": "TASK-12345",
            "status": "success",
            "progress": 100,
            "stage": "completed",
        }

        with patch("i3d_agent.agents.process.get_task_status") as mock_get:
            mock_get.return_value = mock_task_data

            result = agent.get_status("TASK-12345", tenant_id="tenant-123")

            assert result["status"] == "success"
            mock_get.assert_called_once_with(task_id="TASK-12345", tenant_id="tenant-123")

    def test_get_status_error(self):
        """Test get_status handles errors."""
        agent = ProcessAgent()

        with patch("i3d_agent.agents.process.get_task_status") as mock_get:
            mock_get.side_effect = Exception("Task not found")

            result = agent.get_status("UNKNOWN-TASK")

            assert result["status"] == "error"
            assert result["error"] == "Task not found"
            assert result["task_id"] == "UNKNOWN-TASK"

    def test_get_history_success(self):
        """Test get_history returns processing history."""
        agent = ProcessAgent()

        mock_history = [
            {
                "task_id": "TASK-001",
                "item_code": "BOLT-1234",
                "status": "success",
                "timestamp": "2025-01-01T10:00:00Z",
                "duration_seconds": 45,
                "file_type": "step",
            },
            {
                "task_id": "TASK-002",
                "item_code": "BOLT-1234",
                "status": "failed",
                "timestamp": "2025-01-02T10:00:00Z",
                "duration_seconds": 10,
                "file_type": "step",
                "error_message": "Validation failed",
            },
        ]

        with patch("i3d_agent.agents.process.get_processing_history") as mock_get:
            mock_get.return_value = mock_history

            result = agent.get_history("BOLT-1234")

            assert result["status"] == "success"
            assert result["item_code"] == "BOLT-1234"
            assert result["count"] == 2
            assert len(result["history"]) == 2

            # Verify the mock was called correctly
            mock_get.assert_called_once_with(item_code="BOLT-1234", tenant_id=None)

    def test_get_history_no_results(self):
        """Test get_history with no results."""
        agent = ProcessAgent()

        with patch("i3d_agent.agents.process.get_processing_history") as mock_get:
            mock_get.return_value = []

            result = agent.get_history("UNKNOWN-CODE")

            assert result["status"] == "no_results"
            assert result["count"] == 0
            assert result["history"] == []

    def test_get_history_with_tenant_id(self):
        """Test get_history with tenant_id parameter."""
        agent = ProcessAgent()

        with patch("i3d_agent.agents.process.get_processing_history") as mock_get:
            mock_get.return_value = []

            result = agent.get_history("BOLT-1234", tenant_id="tenant-456")

            mock_get.assert_called_once_with(item_code="BOLT-1234", tenant_id="tenant-456")

    def test_get_history_error(self):
        """Test get_history handles errors."""
        agent = ProcessAgent()

        with patch("i3d_agent.agents.process.get_processing_history") as mock_get:
            mock_get.side_effect = Exception("API error")

            result = agent.get_history("BOLT-1234")

            assert result["status"] == "error"
            assert result["error"] == "API error"
            assert result["item_code"] == "BOLT-1234"
            assert result["count"] == 0

    def test_retry_success(self):
        """Test retry returns new task ID."""
        agent = ProcessAgent()

        mock_retry_response = {
            "success": True,
            "new_task_id": "TASK-NEW-123",
            "original_task_id": "TASK-12345",
            "message": "Retry initiated successfully",
        }

        with patch("i3d_agent.agents.process.retry_failed_task") as mock_retry:
            mock_retry.return_value = mock_retry_response

            result = agent.retry("TASK-12345")

            assert result["status"] == "success"
            assert result["task_id"] == "TASK-12345"
            assert result["new_task_id"] == "TASK-NEW-123"
            assert "initiated" in result["message"].lower()

            # Verify the mock was called correctly
            mock_retry.assert_called_once_with(task_id="TASK-12345", tenant_id=None)

    def test_retry_with_tenant_id(self):
        """Test retry with tenant_id parameter."""
        agent = ProcessAgent()

        mock_retry_response = {
            "success": True,
            "new_task_id": "TASK-NEW-456",
            "original_task_id": "TASK-FAILED",
            "message": "Retry started",
        }

        with patch("i3d_agent.agents.process.retry_failed_task") as mock_retry:
            mock_retry.return_value = mock_retry_response

            result = agent.retry("TASK-FAILED", tenant_id="tenant-789")

            assert result["status"] == "success"
            mock_retry.assert_called_once_with(task_id="TASK-FAILED", tenant_id="tenant-789")

    def test_retry_error(self):
        """Test retry handles errors."""
        agent = ProcessAgent()

        with patch("i3d_agent.agents.process.retry_failed_task") as mock_retry:
            mock_retry.side_effect = Exception("Task not found")

            result = agent.retry("UNKNOWN-TASK")

            assert result["status"] == "error"
            assert result["error"] == "Task not found"
            assert result["task_id"] == "UNKNOWN-TASK"

    def test_diagnose_file_format_error(self):
        """Test diagnose with file format error."""
        agent = ProcessAgent()

        error_msg = "Invalid file format for STEP file"

        result = agent.diagnose(error_msg, component="parser")

        assert result["status"] == "success"
        assert result["error_type"] == "file_format_error"
        assert result["severity"] == "high"
        assert "suggested_solutions" in result
        assert len(result["suggested_solutions"]) > 0
        assert "related_docs" in result

    def test_diagnose_parsing_error(self):
        """Test diagnose with parsing error."""
        agent = ProcessAgent()

        error_msg = "Failed to parse STEP file structure"

        result = agent.diagnose(error_msg, component="validator")

        assert result["status"] == "success"
        assert result["error_type"] == "parsing_error"
        assert result["severity"] == "high"
        assert result["component"] == "validator"

    def test_diagnose_network_error(self):
        """Test diagnose with network error."""
        agent = ProcessAgent()

        error_msg = "Connection timeout to storage service"

        result = agent.diagnose(error_msg, component="storage")

        assert result["status"] == "success"
        assert result["error_type"] == "network_error"
        assert result["severity"] == "medium"

    def test_diagnose_storage_error(self):
        """Test diagnose with storage error."""
        agent = ProcessAgent()

        error_msg = "Insufficient disk space on storage server"

        result = agent.diagnose(error_msg)

        assert result["status"] == "success"
        assert result["error_type"] == "storage_error"
        assert result["severity"] == "high"

    def test_diagnose_validation_error(self):
        """Test diagnose with validation error."""
        agent = ProcessAgent()

        error_msg = "Validation constraint violation for weight field"

        result = agent.diagnose(error_msg, component="validator")

        assert result["status"] == "success"
        assert result["error_type"] == "validation_error"
        assert result["severity"] == "medium"

    def test_diagnose_unknown_error(self):
        """Test diagnose with unknown error."""
        agent = ProcessAgent()

        error_msg = "Something unexpected happened"

        result = agent.diagnose(error_msg)

        assert result["status"] == "success"
        assert result["error_type"] == "unknown_error"
        assert result["severity"] == "medium"

    def test_diagnose_with_tenant_id(self):
        """Test diagnose with tenant_id parameter (passed but unused)."""
        agent = ProcessAgent()

        error_msg = "Failed to parse file"

        result = agent.diagnose(error_msg, component="parser", tenant_id="tenant-999")

        # Should still work, tenant_id is passed but unused in diagnosis
        assert result["status"] == "success"

    def test_diagnose_empty_error_raises_error(self):
        """Test diagnose with empty error message raises ValueError."""
        agent = ProcessAgent()

        # Empty error message should raise ValueError
        result = agent.diagnose("")

        assert result["status"] == "error"
        assert "error" in result

    def test_process_agent_inherits_base_agent(self):
        """Test ProcessAgent properly inherits BaseAgent."""
        agent = ProcessAgent()

        # Should have BaseAgent methods
        assert hasattr(agent, "get_system_prompt")
        assert hasattr(agent, "add_tool")
        assert hasattr(agent, "_format_tools")

        # System prompt should include role
        prompt = agent.get_system_prompt()
        assert "task_processor" in prompt

    @pytest.mark.integration
    def test_process_agent_integration(self):
        """Integration test for ProcessAgent (requires actual API)."""
        # This test requires actual API access and should be run manually
        # or with proper test infrastructure
        agent = ProcessAgent()

        # Test would look like this with real API:
        # result = agent.get_status("TASK-12345", tenant_id="test-tenant")
        # assert result["status"] in ["success", "error"]

        # Skip if no API access
        pytest.skip("Integration test - requires API access")

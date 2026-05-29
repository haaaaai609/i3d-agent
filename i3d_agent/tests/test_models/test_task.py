"""
Tests for task models.

Following TDD approach - tests are written before the implementation.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError


class TestTaskType:
    """Test TaskType enum values."""

    def test_task_type_values(self):
        """Test TaskType has required values: SEARCH, RAG, PROCESS."""
        from i3d_agent.models.task import TaskType

        # Check all required values exist
        assert hasattr(TaskType, 'SEARCH')
        assert hasattr(TaskType, 'RAG')
        assert hasattr(TaskType, 'PROCESS')

        # Check values are correct
        assert TaskType.SEARCH.value == 'SEARCH'
        assert TaskType.RAG.value == 'RAG'
        assert TaskType.PROCESS.value == 'PROCESS'

        # Check it's an enum
        assert TaskType.SEARCH in TaskType
        assert TaskType.RAG in TaskType
        assert TaskType.PROCESS in TaskType


class TestTaskStatus:
    """Test TaskStatus enum values."""

    def test_task_status_values(self):
        """Test TaskStatus has required values: PENDING, RUNNING, COMPLETED, FAILED."""
        from i3d_agent.models.task import TaskStatus

        # Check all required values exist
        assert hasattr(TaskStatus, 'PENDING')
        assert hasattr(TaskStatus, 'RUNNING')
        assert hasattr(TaskStatus, 'COMPLETED')
        assert hasattr(TaskStatus, 'FAILED')

        # Check values are correct
        assert TaskStatus.PENDING.value == 'PENDING'
        assert TaskStatus.RUNNING.value == 'RUNNING'
        assert TaskStatus.COMPLETED.value == 'COMPLETED'
        assert TaskStatus.FAILED.value == 'FAILED'

        # Check it's an enum
        assert TaskStatus.PENDING in TaskStatus
        assert TaskStatus.RUNNING in TaskStatus
        assert TaskStatus.COMPLETED in TaskStatus
        assert TaskStatus.FAILED in TaskStatus


class TestAgentTask:
    """Test AgentTask model."""

    def test_task_create(self):
        """Test creating an AgentTask with minimal fields."""
        from i3d_agent.models.task import AgentTask, TaskType, TaskStatus

        task = AgentTask(
            id="task-123",
            tenant_id="huabei",
            user_id="user-456",
            task_type=TaskType.SEARCH,
            task_data={"query": "test query"}
        )

        assert task.id == "task-123"
        assert task.tenant_id == "huabei"
        assert task.user_id == "user-456"
        assert task.task_type == TaskType.SEARCH
        assert task.task_data == {"query": "test query"}

    def test_task_default_status(self):
        """Test AgentTask has default status of PENDING."""
        from i3d_agent.models.task import AgentTask, TaskType, TaskStatus

        task = AgentTask(
            id="task-123",
            tenant_id="huabei",
            user_id="user-456",
            task_type=TaskType.SEARCH,
            task_data={"query": "test query"}
        )

        assert task.status == TaskStatus.PENDING

    def test_task_with_all_fields(self):
        """Test creating AgentTask with all fields."""
        from i3d_agent.models.task import AgentTask, TaskType, TaskStatus

        now = datetime.now()
        task = AgentTask(
            id="task-123",
            tenant_id="huabei",
            user_id="user-456",
            task_type=TaskType.RAG,
            task_data={"query": "test query"},
            status=TaskStatus.COMPLETED,
            result={"answer": "test answer"},
            error_message=None,
            created_at=now,
            updated_at=now,
            completed_at=now
        )

        assert task.id == "task-123"
        assert task.tenant_id == "huabei"
        assert task.user_id == "user-456"
        assert task.task_type == TaskType.RAG
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"answer": "test answer"}
        assert task.error_message is None

    def test_task_with_error(self):
        """Test AgentTask with error message."""
        from i3d_agent.models.task import AgentTask, TaskType, TaskStatus

        task = AgentTask(
            id="task-123",
            tenant_id="huabei",
            user_id="user-456",
            task_type=TaskType.PROCESS,
            task_data={"data": "test"},
            status=TaskStatus.FAILED,
            error_message="Task failed due to error"
        )

        assert task.status == TaskStatus.FAILED
        assert task.error_message == "Task failed due to error"


class TestTaskCreate:
    """Test TaskCreate schema."""

    def test_task_create_schema(self):
        """Test TaskCreate schema with required fields."""
        from i3d_agent.models.task import TaskCreate, TaskType

        task_create = TaskCreate(
            task_type=TaskType.SEARCH,
            task_data={"query": "test query"}
        )

        assert task_create.task_type == TaskType.SEARCH
        assert task_create.task_data == {"query": "test query"}

    def test_task_create_all_task_types(self):
        """Test TaskCreate with all task types."""
        from i3d_agent.models.task import TaskCreate, TaskType

        TaskCreate(task_type=TaskType.SEARCH, task_data={})
        TaskCreate(task_type=TaskType.RAG, task_data={})
        TaskCreate(task_type=TaskType.PROCESS, task_data={})

    def test_task_create_missing_task_type(self):
        """Test TaskCreate requires task_type."""
        from i3d_agent.models.task import TaskCreate

        with pytest.raises(ValidationError):
            TaskCreate(task_data={"query": "test"})

    def test_task_create_missing_task_data(self):
        """Test TaskCreate requires task_data."""
        from i3d_agent.models.task import TaskCreate, TaskType

        with pytest.raises(ValidationError):
            TaskCreate(task_type=TaskType.SEARCH)


class TestTaskUpdate:
    """Test TaskUpdate schema."""

    def test_task_update_status(self):
        """Test TaskUpdate with status field."""
        from i3d_agent.models.task import TaskUpdate, TaskStatus

        task_update = TaskUpdate(status=TaskStatus.RUNNING)

        assert task_update.status == TaskStatus.RUNNING

    def test_task_update_with_result(self):
        """Test TaskUpdate with result field."""
        from i3d_agent.models.task import TaskUpdate

        task_update = TaskUpdate(result={"answer": "test"})

        assert task_update.result == {"answer": "test"}

    def test_task_update_with_error_message(self):
        """Test TaskUpdate with error_message field."""
        from i3d_agent.models.task import TaskUpdate

        task_update = TaskUpdate(error_message="Task failed")

        assert task_update.error_message == "Task failed"

    def test_task_update_all_fields(self):
        """Test TaskUpdate with all fields."""
        from i3d_agent.models.task import TaskUpdate, TaskStatus

        task_update = TaskUpdate(
            status=TaskStatus.COMPLETED,
            result={"answer": "test"},
            error_message=None
        )

        assert task_update.status == TaskStatus.COMPLETED
        assert task_update.result == {"answer": "test"}
        assert task_update.error_message is None

    def test_task_update_empty(self):
        """Test TaskUpdate can be empty (all fields optional)."""
        from i3d_agent.models.task import TaskUpdate

        task_update = TaskUpdate()

        assert task_update.status is None
        assert task_update.result is None
        assert task_update.error_message is None


class TestTaskStatusTransitions:
    """Test task status transitions."""

    def test_task_status_transitions(self):
        """Test valid task status transitions."""
        from i3d_agent.models.task import AgentTask, TaskType, TaskStatus

        task = AgentTask(
            id="task-123",
            tenant_id="huabei",
            user_id="user-456",
            task_type=TaskType.SEARCH,
            task_data={"query": "test"}
        )

        # Initial status
        assert task.status == TaskStatus.PENDING

        # Transition to RUNNING
        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING

        # Transition to COMPLETED
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

    def test_task_status_failed_transition(self):
        """Test transition to FAILED status."""
        from i3d_agent.models.task import AgentTask, TaskType, TaskStatus

        task = AgentTask(
            id="task-123",
            tenant_id="huabei",
            user_id="user-456",
            task_type=TaskType.PROCESS,
            task_data={"data": "test"}
        )

        # Start with RUNNING
        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING

        # Transition to FAILED
        task.status = TaskStatus.FAILED
        task.error_message = "Processing failed"
        assert task.status == TaskStatus.FAILED
        assert task.error_message == "Processing failed"

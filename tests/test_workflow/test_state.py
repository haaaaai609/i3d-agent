import pytest
from datetime import datetime
from pydantic import ValidationError

from i3d_agent.workflow.state import (
    SubTask,
    ClarificationRequest,
    ErrorInfo,
    WorkflowState,
)


class TestSubTask:
    """测试 SubTask 模型"""

    def test_create_subtask(self):
        """测试创建子任务"""
        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="pending",
            input_data={"query": "螺栓"},
        )

        assert task.task_id == "task_1"
        assert task.task_type == "search"
        assert task.status == "pending"
        assert task.output_data is None
        assert task.retry_count == 0

    def test_subtask_with_dependencies(self):
        """测试带依赖关系的子任务"""
        task = SubTask(
            task_id="task_2",
            task_type="rag",
            agent="rag_agent",
            status="pending",
            input_data={"question": "如何使用"},
            dependencies=["task_1"],
        )

        assert task.dependencies == ["task_1"]

    def test_subtask_status_validation(self):
        """测试子任务状态验证"""
        with pytest.raises(ValidationError):
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="invalid_status",  # 无效状态
                input_data={},
            )


class TestClarificationRequest:
    """测试 ClarificationRequest 模型"""

    def test_create_clarification_request(self):
        """测试创建澄清请求"""
        request = ClarificationRequest(
            task_id="task_1",
            question="请指定搜索类型",
            options=["3d", "2d", "text"],
        )

        assert request.task_id == "task_1"
        assert request.question == "请指定搜索类型"
        assert request.options == ["3d", "2d", "text"]

    def test_clarification_request_without_options(self):
        """测试不带选项的澄清请求"""
        request = ClarificationRequest(
            task_id="task_1",
            question="请提供更多细节",
        )

        assert request.options is None


class TestErrorInfo:
    """测试 ErrorInfo 模型"""

    def test_create_error_info(self):
        """测试创建错误信息"""
        error = ErrorInfo(
            task_id="task_1",
            error_type="retriable",
            message="网络超时",
            original_error="TimeoutError",
        )

        assert error.task_id == "task_1"
        assert error.error_type == "retriable"
        assert error.message == "网络超时"

    def test_error_type_validation(self):
        """测试错误类型验证"""
        with pytest.raises(ValidationError):
            ErrorInfo(
                task_id="task_1",
                error_type="invalid_type",  # 无效类型
                message="错误",
            )


class TestWorkflowState:
    """测试 WorkflowState"""

    def test_create_workflow_state(self):
        """测试创建工作流状态"""
        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        assert state["query"] == "搜索螺栓"
        assert state["should_continue"] is True

    def test_workflow_state_with_subtasks(self):
        """测试带子任务的工作流状态"""
        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="pending",
            input_data={"query": "螺栓"},
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        assert len(state["sub_tasks"]) == 1
        assert state["sub_tasks"][0].task_type == "search"

import pytest

from i3d_agent.workflow.state import SubTask, ErrorInfo
from i3d_agent.workflow.utils import (
    is_simple_query,
    get_task_by_id,
    get_next_pending_task,
    get_failed_task,
    is_retriable_error,
    is_degradable_error,
)


class TestQueryComplexity:
    """测试查询复杂度判断"""

    def test_simple_search_query(self):
        """测试简单搜索查询"""
        assert is_simple_query("搜索螺栓") is True
        assert is_simple_query("查找螺丝") is True
        assert is_simple_query("推荐零件") is True

    def test_simple_rag_query(self):
        """测试简单 RAG 查询"""
        assert is_simple_query("文档怎么用") is True
        assert is_simple_query("api 使用方法") is True

    def test_simple_process_query(self):
        """测试简单处理状态查询"""
        assert is_simple_query("处理状态") is True
        assert is_simple_query("任务进度") is True

    def test_complex_multi_intent_query(self):
        """测试多意图复杂查询"""
        assert is_simple_query("搜索螺栓并查看文档") is False
        assert is_simple_query("找零件然后看怎么处理") is False

    def test_complex_vague_query(self):
        """测试模糊复杂查询"""
        assert is_simple_query("我需要一些东西") is False
        assert is_simple_query("帮我看看") is False


class TestTaskHelpers:
    """测试任务辅助函数"""

    def test_get_task_by_id(self):
        """测试通过 ID 获取任务"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="pending",
                input_data={},
            ),
            SubTask(
                task_id="task_2",
                task_type="rag",
                agent="rag_agent",
                status="completed",
                input_data={},
            ),
        ]

        task = get_task_by_id(tasks, "task_1")
        assert task is not None
        assert task.task_id == "task_1"

    def test_get_task_by_id_not_found(self):
        """测试获取不存在的任务"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="pending",
                input_data={},
            )
        ]

        task = get_task_by_id(tasks, "task_999")
        assert task is None

    def test_get_next_pending_task(self):
        """测试获取下一个待处理任务"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="completed",
                input_data={},
            ),
            SubTask(
                task_id="task_2",
                task_type="rag",
                agent="rag_agent",
                status="pending",
                input_data={},
            ),
        ]

        task = get_next_pending_task(tasks)
        assert task is not None
        assert task.task_id == "task_2"

    def test_get_next_pending_task_none(self):
        """测试没有待处理任务时返回 None"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="completed",
                input_data={},
            )
        ]

        task = get_next_pending_task(tasks)
        assert task is None

    def test_get_failed_task(self):
        """测试获取失败任务"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="completed",
                input_data={},
            ),
            SubTask(
                task_id="task_2",
                task_type="rag",
                agent="rag_agent",
                status="failed",
                input_data={},
                error_message="网络错误",
            ),
        ]

        task = get_failed_task(tasks)
        assert task is not None
        assert task.task_id == "task_2"
        assert task.error_message == "网络错误"

    def test_get_failed_task_none(self):
        """测试没有失败任务时返回 None"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="completed",
                input_data={},
            )
        ]

        task = get_failed_task(tasks)
        assert task is None


class TestErrorClassification:
    """测试错误分类"""

    def test_is_retriable_error(self):
        """测试可重试错误判断"""
        error_timeout = ErrorInfo(
            task_id="task_1", error_type="retriable", message="超时"
        )
        assert is_retriable_error(error_timeout) is True

        error_critical = ErrorInfo(
            task_id="task_1", error_type="critical", message="严重错误"
        )
        assert is_retriable_error(error_critical) is False

    def test_is_degradable_error(self):
        """测试可降级错误判断"""
        error_degradable = ErrorInfo(
            task_id="task_1", error_type="degradable", message="服务降级"
        )
        assert is_degradable_error(error_degradable) is True

        error_critical = ErrorInfo(
            task_id="task_1", error_type="critical", message="严重错误"
        )
        assert is_degradable_error(error_critical) is False

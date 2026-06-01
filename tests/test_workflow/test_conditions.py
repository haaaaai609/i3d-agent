import pytest

from i3d_agent.workflow.state import SubTask, ErrorInfo, ClarificationRequest
from i3d_agent.workflow.conditions.routing import (
    should_route_to_memory,
    check_clarification_needed,
    check_all_tasks_completed,
    decide_next_agent,
    classify_error,
)


class TestShouldRouteToMemory:
    """测试记忆路由判断"""

    def test_no_conversation_history_routes_to_memory(self):
        """测试无对话历史时路由到 memory_agent"""
        state = {
            "conversation_history": [],
        }
        result = should_route_to_memory(state)
        assert result == "load_memory"

    def test_with_conversation_history_skips_memory(self):
        """测试有对话历史时跳过 memory_agent"""
        state = {
            "conversation_history": [{"role": "user", "content": "上次查询"}],
        }
        result = should_route_to_memory(state)
        assert result == "skip_memory"


class TestCheckClarificationNeeded:
    """测试澄清需求检查"""

    def test_no_pending_clarification_continues(self):
        """测试无待处理澄清时继续执行"""
        state = {
            "pending_clarification": None,
        }
        result = check_clarification_needed(state)
        assert result == "continue_execution"

    def test_pending_clarification_requests_user_input(self):
        """测试有待处理澄清时请求用户输入"""
        state = {
            "pending_clarification": ClarificationRequest(
                task_id="task_1",
                question="请指定搜索类型",
            ),
        }
        result = check_clarification_needed(state)
        assert result == "request_clarification"


class TestCheckAllTasksCompleted:
    """测试任务完成检查"""

    def test_all_pending_returns_continue(self):
        """测试有待处理任务时返回继续"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="pending",
                    input_data={},
                )
            ]
        }
        result = check_all_tasks_completed(state)
        assert result == "continue_tasks"

    def test_all_completed_returns_aggregate(self):
        """测试所有任务完成时返回聚合"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="completed",
                    input_data={},
                    output_data={"results": []},
                )
            ]
        }
        result = check_all_tasks_completed(state)
        assert result == "aggregate_results"

    def test_has_failed_returns_handle_error(self):
        """测试有失败任务时返回错误处理"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="failed",
                    input_data={},
                    error_message="网络错误",
                )
            ]
        }
        result = check_all_tasks_completed(state)
        assert result == "handle_error"


class TestDecideNextAgent:
    """测试下一个 Agent 决策"""

    def test_no_pending_task_returns_aggregator(self):
        """测试无待处理任务时返回 aggregator"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="completed",
                    input_data={},
                )
            ]
        }
        result = decide_next_agent(state)
        assert result == "aggregator"

    def test_pending_search_task_returns_search_agent(self):
        """测试待处理搜索任务返回 search_agent"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="pending",
                    input_data={"query": "螺栓"},
                )
            ]
        }
        result = decide_next_agent(state)
        assert result == "search_agent"

    def test_pending_rag_task_returns_rag_agent(self):
        """测试待处理 RAG 任务返回 rag_agent"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="rag",
                    agent="rag_agent",
                    status="pending",
                    input_data={"question": "如何使用"},
                )
            ]
        }
        result = decide_next_agent(state)
        assert result == "rag_agent"

    def test_pending_process_task_returns_process_agent(self):
        """测试待处理 Process 任务返回 process_agent"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="process",
                    agent="process_agent",
                    status="pending",
                    input_data={"task_id": "task_123"},
                )
            ]
        }
        result = decide_next_agent(state)
        assert result == "process_agent"


class TestClassifyError:
    """测试错误分类"""

    def test_retriable_error_returns_retry(self):
        """测试可重试错误返回 retry"""
        state = {
            "error": ErrorInfo(
                task_id="task_1",
                error_type="retriable",
                message="网络超时",
            )
        }
        result = classify_error(state)
        assert result == "retry"

    def test_degradable_error_returns_degrade(self):
        """测试可降级错误返回 degrade"""
        state = {
            "error": ErrorInfo(
                task_id="task_1",
                error_type="degradable",
                message="服务降级",
            )
        }
        result = classify_error(state)
        assert result == "degrade"

    def test_critical_error_returns_fail(self):
        """测试严重错误返回 fail"""
        state = {
            "error": ErrorInfo(
                task_id="task_1",
                error_type="critical",
                message="严重错误",
            )
        }
        result = classify_error(state)
        assert result == "fail"

    def test_no_error_returns_no_error(self):
        """测试无错误时返回 no_error"""
        state = {
            "error": None,
        }
        result = classify_error(state)
        assert result == "no_error"

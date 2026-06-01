import pytest
from unittest.mock import Mock, patch

from i3d_agent.workflow.state import WorkflowState, SubTask, ClarificationRequest, ErrorInfo
from i3d_agent.workflow.nodes.memory_agent import memory_agent_node
from i3d_agent.workflow.nodes.supervisor import supervisor_node
from i3d_agent.workflow.nodes.search_agent import search_agent_node
from i3d_agent.workflow.nodes.rag_agent import rag_agent_node
from i3d_agent.workflow.nodes.process_agent import process_agent_node
from i3d_agent.workflow.nodes.aggregator import aggregator_node
from i3d_agent.workflow.nodes.error_handler import error_handler_node
from i3d_agent.agents.base import NeedsClarificationError


class TestMemoryAgentNode:
    """测试 memory_agent 节点"""

    @pytest.mark.asyncio
    @patch("i3d_agent.workflow.nodes.memory_agent.MemoryManager")
    async def test_memory_agent_loads_history(self, mock_mgr_class):
        mock_mgr = Mock()
        mock_mgr.get_context.return_value = {"messages": [{"role": "user", "content": "test"}]}
        mock_mgr_class.return_value = mock_mgr

        with patch("i3d_agent.workflow.nodes.memory_agent._memory_manager", mock_mgr):
            state: WorkflowState = {
                "query": "test", "user_id": "u1", "tenant_id": "t1", "session_id": "s1",
                "stream": False, "messages": [], "conversation_history": [], "sub_tasks": [],
                "current_task_index": 0, "pending_clarification": None, "clarification_answer": None,
                "error": None, "response": None, "sources": None, "thought_process": None,
                "metadata": None, "next_action": None, "should_continue": True,
            }
            result = await memory_agent_node(state)
            assert len(result["conversation_history"]) == 1


class TestSupervisorNode:
    """测试 supervisor 节点"""

    @pytest.mark.asyncio
    async def test_supervisor_creates_task(self):
        state: WorkflowState = {
            "query": "搜索螺栓", "user_id": "u1", "tenant_id": "huabei", "session_id": "s1",
            "stream": False, "messages": [], "conversation_history": [], "sub_tasks": [],
            "current_task_index": 0, "pending_clarification": None, "clarification_answer": None,
            "error": None, "response": None, "sources": None, "thought_process": None,
            "metadata": None, "next_action": None, "should_continue": True,
        }
        result = await supervisor_node(state)
        assert len(result["sub_tasks"]) == 1


class TestAggregatorNode:
    """测试 aggregator 节点"""

    @pytest.mark.asyncio
    async def test_aggregator_collects_results(self):
        task = SubTask(
            task_id="t1", task_type="search", agent="search_agent", status="completed",
            input_data={}, output_data={"results": [{"name": "螺栓"}]}
        )
        state: WorkflowState = {
            "query": "搜索", "user_id": "u1", "tenant_id": "t1", "session_id": "s1",
            "stream": False, "messages": [], "conversation_history": [], "sub_tasks": [task],
            "current_task_index": 0, "pending_clarification": None, "clarification_answer": None,
            "error": None, "response": None, "sources": None, "thought_process": None,
            "metadata": None, "next_action": None, "should_continue": True,
        }
        result = await aggregator_node(state)
        assert result["response"] is not None
        assert result["should_continue"] is False


class TestErrorHandlerNode:
    """测试 error_handler 节点"""

    @pytest.mark.asyncio
    async def test_error_handler_retries(self):
        task = SubTask(
            task_id="t1", task_type="search", agent="search_agent", status="failed",
            input_data={}, error_message="timeout", retry_count=0
        )
        state: WorkflowState = {
            "query": "搜索", "user_id": "u1", "tenant_id": "t1", "session_id": "s1",
            "stream": False, "messages": [], "conversation_history": [], "sub_tasks": [task],
            "current_task_index": 0, "pending_clarification": None, "clarification_answer": None,
            "error": ErrorInfo(task_id="t1", error_type="retriable", message="timeout"),
            "response": None, "sources": None, "thought_process": None,
            "metadata": None, "next_action": None, "should_continue": True,
        }
        result = await error_handler_node(state)
        assert result["sub_tasks"][0].status == "pending"
        assert result["sub_tasks"][0].retry_count == 1

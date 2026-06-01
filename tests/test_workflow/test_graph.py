import pytest

from i3d_agent.workflow.graph import I3DWorkflow
from i3d_agent.workflow.nodes.memory_agent import get_memory_manager


class TestI3DWorkflow:
    """测试 I3DWorkflow 工作流"""

    def test_workflow_initialization(self):
        """测试工作流初始化"""
        memory_manager = get_memory_manager()
        workflow = I3DWorkflow(memory_manager)

        assert workflow.graph is not None
        assert workflow.memory_manager is not None

    def test_workflow_creates_state_graph(self):
        """测试工作流创建 StateGraph"""
        memory_manager = get_memory_manager()
        workflow = I3DWorkflow(memory_manager)

        assert workflow.graph is not None

    @pytest.mark.asyncio
    async def test_workflow_run_simple_search(self):
        """测试工作流执行简单搜索"""
        from unittest.mock import patch, Mock, MagicMock

        # Mock the memory manager to avoid Redis connection
        mock_memory_manager = Mock()
        mock_memory_manager.get_context.return_value = None
        mock_memory_manager.set_context.return_value = None

        # Set the global memory manager
        from i3d_agent.workflow.nodes.memory_agent import set_memory_manager
        set_memory_manager(mock_memory_manager)

        workflow = I3DWorkflow(mock_memory_manager)

        with patch("i3d_agent.workflow.nodes.search_agent.SearchAgent") as mock_search:
            mock_agent = Mock()
            mock_agent.search.return_value = {
                "results": [{"item_code": "BOLT001", "name": "螺栓"}],
            }
            mock_search.return_value = mock_agent

            response = await workflow.run(
                query="搜索螺栓",
                user_id="user123",
                tenant_id="huabei",
                session_id="session456",
            )

            assert response.response is not None

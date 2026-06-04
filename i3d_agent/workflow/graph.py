"""I3D Agent workflow graph."""

import os
import uuid
from typing import Optional, Dict, Any, AsyncIterator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from i3d_agent.memory.manager import MemoryManager
from i3d_agent.models.chat import ChatResponse, SourceDocument
from i3d_agent.workflow.state import WorkflowState
from i3d_agent.workflow.nodes.memory_agent import memory_agent_node
from i3d_agent.workflow.nodes.supervisor import supervisor_node
from i3d_agent.workflow.nodes.search_agent import search_agent_node
from i3d_agent.workflow.nodes.rag_agent import rag_agent_node
from i3d_agent.workflow.nodes.process_agent import process_agent_node
from i3d_agent.workflow.nodes.aggregator import aggregator_node
from i3d_agent.workflow.nodes.error_handler import error_handler_node
from i3d_agent.workflow.conditions.routing import (
    should_route_to_memory,
    check_all_tasks_completed,
    decide_next_agent,
    classify_error,
)
from i3d_agent.workflow.utils import (
    workflow_context,
    log_route_decision,
)
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class I3DWorkflow:
    """I3D Agent System 工作流。"""

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ):
        self.memory_manager = memory_manager or MemoryManager()
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(WorkflowState)

        # 为每个节点添加日志包装器
        async def logged_memory_agent(state: WorkflowState) -> WorkflowState:
            request_id = state.get("request_id", "unknown")
            from i3d_agent.workflow.utils import node_execution
            with node_execution("memory_agent", request_id):
                return await memory_agent_node(state)

        async def logged_supervisor(state: WorkflowState) -> WorkflowState:
            request_id = state.get("request_id", "unknown")
            from i3d_agent.workflow.utils import node_execution
            with node_execution("supervisor", request_id):
                return await supervisor_node(state)

        async def logged_search_agent(state: WorkflowState) -> WorkflowState:
            request_id = state.get("request_id", "unknown")
            from i3d_agent.workflow.utils import node_execution
            with node_execution("search_agent", request_id):
                return await search_agent_node(state)

        async def logged_rag_agent(state: WorkflowState) -> WorkflowState:
            request_id = state.get("request_id", "unknown")
            from i3d_agent.workflow.utils import node_execution
            with node_execution("rag_agent", request_id):
                return await rag_agent_node(state)

        async def logged_process_agent(state: WorkflowState) -> WorkflowState:
            request_id = state.get("request_id", "unknown")
            from i3d_agent.workflow.utils import node_execution
            with node_execution("process_agent", request_id):
                return await process_agent_node(state)

        async def logged_aggregator(state: WorkflowState) -> WorkflowState:
            request_id = state.get("request_id", "unknown")
            from i3d_agent.workflow.utils import node_execution
            with node_execution("aggregator", request_id):
                return await aggregator_node(state)

        async def logged_error_handler(state: WorkflowState) -> WorkflowState:
            request_id = state.get("request_id", "unknown")
            from i3d_agent.workflow.utils import node_execution
            with node_execution("error_handler", request_id):
                return await error_handler_node(state)

        # Add dispatcher node (simple passthrough)
        async def dispatcher_node(state: WorkflowState) -> WorkflowState:
            request_id = state.get("request_id", "unknown")
            from i3d_agent.workflow.utils import node_execution
            with node_execution("dispatcher", request_id):
                return state

        workflow.add_node("memory_agent", logged_memory_agent)
        workflow.add_node("supervisor", logged_supervisor)
        workflow.add_node("search_agent", logged_search_agent)
        workflow.add_node("rag_agent", logged_rag_agent)
        workflow.add_node("process_agent", logged_process_agent)
        workflow.add_node("aggregator", logged_aggregator)
        workflow.add_node("error_handler", logged_error_handler)
        workflow.add_node("dispatcher", dispatcher_node)

        # Entry point with conditional routing for memory
        workflow.set_entry_point("memory_agent")

        # 创建带日志的路由决策函数
        def logged_should_route_to_memory(state: WorkflowState) -> str:
            request_id = state.get("request_id", "unknown")
            result = should_route_to_memory(state)
            log_route_decision(request_id, "memory_agent", "supervisor", result)
            return result

        workflow.add_conditional_edges(
            "memory_agent",
            logged_should_route_to_memory,
            {
                "load_memory": "supervisor",
                "skip_memory": "supervisor",
            },
        )

        # supervisor 的路由决策
        def logged_supervisor_route(state: WorkflowState) -> str:
            request_id = state.get("request_id", "unknown")
            if state.get("response"):
                result = "complete"
            elif state.get("sub_tasks"):
                result = "has_tasks"
            else:
                result = "no_tasks"
            log_route_decision(request_id, "supervisor", result, "has_response_or_tasks",
                            has_response=bool(state.get("response")), has_tasks=bool(state.get("sub_tasks")))
            return result

        workflow.add_conditional_edges(
            "supervisor",
            logged_supervisor_route,
            {
                "complete": END,
                "has_tasks": "dispatcher",
                "no_tasks": "aggregator",
            },
        )

        # dispatcher 的路由决策
        def logged_decide_next_agent(state: WorkflowState) -> str:
            request_id = state.get("request_id", "unknown")
            result = decide_next_agent(state)
            log_route_decision(request_id, "dispatcher", result, "next_pending_task")
            return result

        workflow.add_conditional_edges(
            "dispatcher",
            logged_decide_next_agent,
            {
                "search_agent": "search_agent",
                "rag_agent": "rag_agent",
                "process_agent": "process_agent",
                "aggregator": "aggregator",
            },
        )

        # 各 agent 完成后的路由决策
        for agent_name in ["search_agent", "rag_agent", "process_agent"]:
            def logged_check_tasks(state: WorkflowState, name=agent_name) -> str:
                request_id = state.get("request_id", "unknown")
                result = check_all_tasks_completed(state)
                log_route_decision(request_id, name, result, f"{name}_completed")
                return result

            workflow.add_conditional_edges(
                agent_name,
                logged_check_tasks,
                {
                    "continue_tasks": "dispatcher",
                    "aggregate_results": "aggregator",
                    "handle_error": "error_handler",
                },
            )

        # error_handler 的路由决策
        def logged_classify_error(state: WorkflowState) -> str:
            request_id = state.get("request_id", "unknown")
            result = classify_error(state)
            error = state.get("error")
            error_type = error.error_type if error else "no_error"
            log_route_decision(request_id, "error_handler", result, f"error_type={error_type}")
            return result

        workflow.add_conditional_edges(
            "error_handler",
            logged_classify_error,
            {
                "retry": "dispatcher",
                "degrade": "aggregator",
                "fail": END,
                "no_error": "dispatcher",
            },
        )

        workflow.add_edge("aggregator", END)

        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)

        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    async def run(
        self,
        query: str,
        user_id: str,
        tenant_id: str,
        session_id: str,
        stream: bool = False,
        request_id: Optional[str] = None,
    ) -> ChatResponse:
        """运行工作流。

        Args:
            query: 用户查询
            user_id: 用户 ID
            tenant_id: 租户 ID
            session_id: 会话 ID
            stream: 是否流式返回
            request_id: 请求 ID（用于日志追踪）
        """
        if request_id is None:
            request_id = str(uuid.uuid4())[:8]

        initial_state: WorkflowState = {
            "query": query,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "stream": stream,
            "request_id": request_id,
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

        config = {"configurable": {"thread_id": session_id}}

        # 使用工作流上下文管理器
        with workflow_context(request_id):
            logger.info(
                f"[{request_id}] 🚀 WORKFLOW_INVOKING | query_preview={query[:50]}... | "
                f"user={user_id} | tenant={tenant_id} | session={session_id}"
            )
            final_state = await self.graph.ainvoke(initial_state, config)

        return ChatResponse(
            response=final_state.get("response", ""),
            sources=final_state.get("sources"),
            thought_process=final_state.get("thought_process"),
            session_id=session_id,
            metadata=final_state.get("metadata"),
        )

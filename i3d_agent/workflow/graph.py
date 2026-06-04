"""I3D Agent workflow graph."""

import os
import uuid
import json
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

    async def run_stream(
        self,
        query: str,
        user_id: str,
        tenant_id: str,
        session_id: str,
        request_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """运行工作流并流式返回状态更新。

        Args:
            query: 用户查询
            user_id: 用户 ID
            tenant_id: 租户 ID
            session_id: 会话 ID
            request_id: 请求 ID（用于日志追踪）

        Yields:
            状态更新字典，包含 type 和相关数据
        """
        if request_id is None:
            request_id = str(uuid.uuid4())[:8]

        initial_state: WorkflowState = {
            "query": query,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "stream": True,
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
                f"[{request_id}] 🚀 WORKFLOW_STREAM_INVOKING | query_preview={query[:50]}... | "
                f"user={user_id} | tenant={tenant_id} | session={session_id}"
            )

            final_response = None
            final_sources = None
            final_thought_process = None

            # 使用 astream 流式运行工作流
            async for event in self.graph.astream(
                initial_state,
                config,
                stream_mode="updates",
            ):
                # 调试：记录事件类型
                logger.debug(f"[{request_id}] 🔍 STREAM_EVENT | type={type(event)} | content={str(event)[:200]}")

                # event 格式检查
                if isinstance(event, tuple) and len(event) == 2:
                    node_name, state_update = event
                    logger.info(f"[{request_id}] 📦 NODE_UPDATE | node={node_name} | has_response={bool(state_update.get('response'))}")

                    # 如果 supervisor 生成了响应（general 查询），发送内容和完成事件
                    if node_name == "supervisor" and state_update.get("response"):
                        final_response = state_update["response"]
                        final_sources = state_update.get("sources")
                        final_thought_process = state_update.get("thought_process")

                        logger.info(f"[{request_id}] 📤 SENDING_CONTENT | from=supervisor | length={len(final_response)}")

                        # 发送内容
                        yield {
                            "type": "content",
                            "content": state_update["response"],
                            "request_id": request_id,
                            "session_id": session_id,
                            "done": False,
                        }

                    # 如果 aggregator 完成，保存结果
                    if node_name == "aggregator":
                        final_response = state_update.get("response", "")
                        final_sources = state_update.get("sources")
                        final_thought_process = state_update.get("thought_process")

                        logger.info(f"[{request_id}] 📤 SENDING_CONTENT | from=aggregator | length={len(final_response) if final_response else 0}")

                        # 发送内容
                        if final_response:
                            yield {
                                "type": "content",
                                "content": final_response,
                                "request_id": request_id,
                                "session_id": session_id,
                                "done": False,
                            }
                elif isinstance(event, dict):
                    # 处理字典格式的事件
                    logger.debug(f"[{request_id}] 🔍 DICT_EVENT | keys={list(event.keys())}")
                    for node_name, state_update in event.items():
                        logger.info(f"[{request_id}] 📦 NODE_UPDATE | node={node_name} | has_response={bool(state_update.get('response'))}")

                        if node_name == "supervisor" and state_update.get("response"):
                            final_response = state_update["response"]
                            final_sources = state_update.get("sources")
                            final_thought_process = state_update.get("thought_process")

                            logger.info(f"[{request_id}] 📤 SENDING_CONTENT | from=supervisor | length={len(final_response)}")

                            yield {
                                "type": "content",
                                "content": state_update["response"],
                                "request_id": request_id,
                                "session_id": session_id,
                                "done": False,
                            }

                        if node_name == "aggregator":
                            final_response = state_update.get("response", "")
                            final_sources = state_update.get("sources")
                            final_thought_process = state_update.get("thought_process")

                            logger.info(f"[{request_id}] 📤 SENDING_CONTENT | from=aggregator | length={len(final_response) if final_response else 0}")

                            if final_response:
                                yield {
                                    "type": "content",
                                    "content": final_response,
                                    "request_id": request_id,
                                    "session_id": session_id,
                                    "done": False,
                                }

            # 发送完成事件（前端期望的格式）
            logger.info(f"[{request_id}] 📤 SENDING_DONE | final_response_length={len(final_response) if final_response else 0}")
            yield {
                "type": "done",
                "done": True,
                "session_id": session_id,
                "sources": final_sources,
                "thought_process": final_thought_process,
            }

        logger.info(f"[{request_id}] ✅ WORKFLOW_STREAM_COMPLETE")

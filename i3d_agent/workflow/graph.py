"""I3D Agent workflow graph."""

import os
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

        workflow.add_node("memory_agent", memory_agent_node)
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("search_agent", search_agent_node)
        workflow.add_node("rag_agent", rag_agent_node)
        workflow.add_node("process_agent", process_agent_node)
        workflow.add_node("aggregator", aggregator_node)
        workflow.add_node("error_handler", error_handler_node)

        # Add dispatcher node (simple passthrough)
        async def dispatcher_node(state: WorkflowState) -> WorkflowState:
            return state

        workflow.add_node("dispatcher", dispatcher_node)

        # Entry point with conditional routing for memory
        workflow.set_entry_point("memory_agent")

        workflow.add_conditional_edges(
            "memory_agent",
            should_route_to_memory,
            {
                "load_memory": "supervisor",
                "skip_memory": "supervisor",
            },
        )

        workflow.add_conditional_edges(
            "supervisor",
            lambda state: "has_tasks" if state.get("sub_tasks") else "no_tasks",
            {
                "has_tasks": "dispatcher",
                "no_tasks": "aggregator",
            },
        )

        workflow.add_conditional_edges(
            "dispatcher",
            decide_next_agent,
            {
                "search_agent": "search_agent",
                "rag_agent": "rag_agent",
                "process_agent": "process_agent",
                "aggregator": "aggregator",
            },
        )

        for agent_name in ["search_agent", "rag_agent", "process_agent"]:
            workflow.add_conditional_edges(
                agent_name,
                check_all_tasks_completed,
                {
                    "continue_tasks": "dispatcher",
                    "aggregate_results": "aggregator",
                    "handle_error": "error_handler",
                },
            )

        workflow.add_conditional_edges(
            "error_handler",
            classify_error,
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
    ) -> ChatResponse:
        initial_state: WorkflowState = {
            "query": query,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "stream": stream,
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

        final_state = await self.graph.ainvoke(initial_state, config)

        return ChatResponse(
            response=final_state.get("response", ""),
            sources=final_state.get("sources"),
            thought_process=final_state.get("thought_process"),
            session_id=session_id,
            metadata=final_state.get("metadata"),
        )

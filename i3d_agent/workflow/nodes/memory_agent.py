"""Memory agent node for the I3D Agent workflow."""

import asyncio
from typing import Dict, Any

from i3d_agent.config.settings import get_settings
from i3d_agent.memory.manager import MemoryManager
from i3d_agent.workflow.state import WorkflowState


_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


async def memory_agent_node(state: WorkflowState) -> WorkflowState:
    memory_manager = get_memory_manager()
    user_id = state["user_id"]
    query = state["query"]
    session_id = state["session_id"]

    context = memory_manager.get_context(user_id)
    if context:
        conversation_history = context.get("messages", [])
        state["conversation_history"] = conversation_history
    else:
        state["conversation_history"] = []

    memory_manager.set_context(
        user_id,
        {
            "current_query": query,
            "session_id": session_id,
            "timestamp": None,
        }
    )

    return state

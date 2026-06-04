"""Memory agent node for the I3D Agent workflow."""

import asyncio
from typing import Dict, Any

from i3d_agent.config.settings import get_settings
from i3d_agent.memory.manager import MemoryManager
from i3d_agent.workflow.state import WorkflowState
from i3d_agent.workflow.utils import log_agent_execution
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)

_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def set_memory_manager(manager: MemoryManager) -> None:
    """Set the global memory manager (useful for testing)."""
    global _memory_manager
    _memory_manager = manager


async def memory_agent_node(state: WorkflowState) -> WorkflowState:
    request_id = state.get("request_id", "unknown")
    memory_manager = get_memory_manager()
    user_id = state["user_id"]
    query = state["query"]
    session_id = state["session_id"]

    log_agent_execution(request_id, "memory_agent", "loading_context",
                        user_id=user_id, session_id=session_id)

    context = memory_manager.get_context(user_id)
    if context:
        conversation_history = context.get("messages", [])
        state["conversation_history"] = conversation_history
        log_agent_execution(request_id, "memory_agent", "context_loaded",
                          history_count=len(conversation_history))
    else:
        state["conversation_history"] = []
        log_agent_execution(request_id, "memory_agent", "no_context_found")

    memory_manager.set_context(
        user_id,
        {
            "current_query": query,
            "session_id": session_id,
            "timestamp": None,
        }
    )

    return state

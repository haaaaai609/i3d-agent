"""RAG agent node for the I3D Agent workflow."""

from typing import Dict, Any, Optional
import asyncpg

from i3d_agent.agents.rag import RAGAgent
from i3d_agent.agents.base import NeedsClarificationError
from i3d_agent.workflow.state import WorkflowState, SubTask, ClarificationRequest, ErrorInfo
from i3d_agent.workflow.utils import log_agent_execution, log_task_status, log_error_handling
from i3d_agent.utils.logger import get_logger
from i3d_agent.config.settings import get_settings


# ========== 全局数据库池 ==========

_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """获取或创建数据库连接池"""
    global _db_pool
    if _db_pool is None:
        settings = get_settings()
        _db_pool = await asyncpg.create_pool(
            settings.get_database_url(async_driver=True),
            min_size=2,
            max_size=10
        )
    return _db_pool

logger = get_logger(__name__)


async def rag_agent_node(state: WorkflowState) -> WorkflowState:
    request_id = state.get("request_id", "unknown")
    sub_tasks = state.get("sub_tasks", [])
    tenant_id = state["tenant_id"]

    current_task: SubTask | None = None
    for task in sub_tasks:
        if task.task_type == "rag" and task.status in ["pending", "running"]:
            current_task = task
            break

    if not current_task:
        log_agent_execution(request_id, "rag_agent", "no_pending_task")
        return state

    current_task.status = "running"
    log_task_status(request_id, current_task, "started")

    try:
        pool = await get_db_pool()
        agent = RAGAgent(pool=pool)
        input_data = current_task.input_data

        log_agent_execution(
            request_id,
            "rag_agent",
            "executing",
            question=input_data.get("question", "")[:50]
        )

        result = await agent.answer(
            question=input_data.get("question", ""),
            tenant_id=tenant_id,
        )

        current_task.status = "completed"
        current_task.output_data = result

        sources_count = len(result.get("sources", [])) if result else 0
        log_agent_execution(request_id, "rag_agent", "completed",
                          sources_count=sources_count,
                          answer_length=len(result.get("answer", "")) if result else 0)
        log_task_status(request_id, current_task, "completed")

    except NeedsClarificationError as e:
        current_task.status = "needs_clarification"
        current_task.error_message = str(e)

        log_agent_execution(request_id, "rag_agent", "needs_clarification", question=str(e.question))
        log_task_status(request_id, current_task, "needs_clarification")

        state["pending_clarification"] = ClarificationRequest(
            task_id=current_task.task_id,
            question=e.question,
            options=e.options,
        )

    except Exception as e:
        error_message = str(e)

        if "timeout" in error_message.lower():
            error_type = "retriable"
        else:
            error_type = "degradable"

        current_task.status = "failed"
        current_task.error_message = error_message

        log_error_handling(request_id, current_task.task_id, error_type, error_message)
        log_task_status(request_id, current_task, "failed")

        state["error"] = ErrorInfo(
            task_id=current_task.task_id,
            error_type=error_type,
            message=error_message,
            original_error=type(e).__name__,
        )

    return state

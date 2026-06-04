"""Error handler node for the I3D Agent workflow."""

from typing import Dict, Any

from i3d_agent.workflow.state import WorkflowState, SubTask, ErrorInfo
from i3d_agent.workflow.utils import log_agent_execution, log_error_handling
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


async def error_handler_node(state: WorkflowState) -> WorkflowState:
    request_id = state.get("request_id", "unknown")
    error: ErrorInfo | None = state.get("error")
    if not error:
        log_agent_execution(request_id, "error_handler", "no_error")
        return state

    log_agent_execution(request_id, "error_handler", "processing",
                       error_type=error.error_type,
                       task_id=error.task_id[:8])

    sub_tasks: list[SubTask] = state.get("sub_tasks", [])
    failed_task: SubTask | None = None

    for task in sub_tasks:
        if task.task_id == error.task_id:
            failed_task = task
            break

    if not failed_task:
        log_agent_execution(request_id, "error_handler", "task_not_found",
                          task_id=error.task_id[:8])
        state["error"] = None
        return state

    if error.error_type == "retriable":
        if failed_task.retry_count < 3:
            failed_task.status = "pending"
            failed_task.retry_count += 1
            state["error"] = None
            log_agent_execution(request_id, "error_handler", "retrying",
                              retry_count=failed_task.retry_count)
        else:
            state["should_continue"] = False
            state["response"] = f"请求失败：{error.message}（已重试 {failed_task.retry_count} 次）"
            log_agent_execution(request_id, "error_handler", "max_retries_exceeded",
                              retry_count=failed_task.retry_count)

    elif error.error_type == "degradable":
        state["next_action"] = "aggregate"
        state["response"] = f"（部分服务不可用：{error.message}）"
        state["error"] = None
        log_agent_execution(request_id, "error_handler", "degraded")

    else:
        state["should_continue"] = False
        state["response"] = f"遇到问题：{error.message}"
        log_agent_execution(request_id, "error_handler", "critical_error")

    logger.info(
        f"[{request_id}] ⚠️ ERROR_HANDLER_COMPLETE | "
        f"error_type={error.error_type} | task_id={error.task_id[:8]}"
    )

    return state

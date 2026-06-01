"""Error handler node for the I3D Agent workflow."""

from typing import Dict, Any

from i3d_agent.workflow.state import WorkflowState, SubTask, ErrorInfo


async def error_handler_node(state: WorkflowState) -> WorkflowState:
    error: ErrorInfo | None = state.get("error")
    if not error:
        return state

    sub_tasks: list[SubTask] = state.get("sub_tasks", [])
    failed_task: SubTask | None = None

    for task in sub_tasks:
        if task.task_id == error.task_id:
            failed_task = task
            break

    if not failed_task:
        state["error"] = None
        return state

    if error.error_type == "retriable":
        if failed_task.retry_count < 3:
            failed_task.status = "pending"
            failed_task.retry_count += 1
            state["error"] = None
        else:
            state["should_continue"] = False
            state["response"] = f"请求失败：{error.message}（已重试 {failed_task.retry_count} 次）"

    elif error.error_type == "degradable":
        state["next_action"] = "aggregate"
        state["response"] = f"（部分服务不可用：{error.message}）"
        state["error"] = None

    else:
        state["should_continue"] = False
        state["response"] = f"遇到问题：{error.message}"

    return state

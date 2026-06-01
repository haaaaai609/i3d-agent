"""Search agent node for the I3D Agent workflow."""

from typing import Dict, Any

from i3d_agent.agents.search import SearchAgent
from i3d_agent.agents.base import NeedsClarificationError, AgentError
from i3d_agent.workflow.state import WorkflowState, SubTask, ClarificationRequest, ErrorInfo


async def search_agent_node(state: WorkflowState) -> WorkflowState:
    sub_tasks = state.get("sub_tasks", [])
    tenant_id = state["tenant_id"]

    current_task: SubTask | None = None
    for task in sub_tasks:
        if task.task_type == "search" and task.status in ["pending", "running"]:
            current_task = task
            break

    if not current_task:
        return state

    current_task.status = "running"

    try:
        agent = SearchAgent()
        input_data = current_task.input_data

        result = await agent.search(
            query=input_data.get("query", ""),
            search_type=input_data.get("search_type", "3d"),
            params=input_data.get("params", {}),
            tenant_id=tenant_id,
        )

        current_task.status = "completed"
        current_task.output_data = result

    except NeedsClarificationError as e:
        current_task.status = "needs_clarification"
        current_task.error_message = str(e)

        state["pending_clarification"] = ClarificationRequest(
            task_id=current_task.task_id,
            question=e.question,
            options=e.options,
        )

    except Exception as e:
        error_message = str(e)

        if "timeout" in error_message.lower() or "网络" in error_message:
            error_type = "retriable"
        elif "服务" in error_message or "降级" in error_message:
            error_type = "degradable"
        else:
            error_type = "critical"

        current_task.status = "failed"
        current_task.error_message = error_message

        state["error"] = ErrorInfo(
            task_id=current_task.task_id,
            error_type=error_type,
            message=error_message,
            original_error=type(e).__name__,
        )

    return state

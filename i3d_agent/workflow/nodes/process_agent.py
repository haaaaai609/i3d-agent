"""Process agent node for the I3D Agent workflow."""

from typing import Dict, Any

from i3d_agent.agents.process import ProcessAgent
from i3d_agent.agents.base import NeedsClarificationError
from i3d_agent.workflow.state import WorkflowState, SubTask, ClarificationRequest, ErrorInfo
from i3d_agent.workflow.utils import log_agent_execution, log_task_status, log_error_handling
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


async def process_agent_node(state: WorkflowState) -> WorkflowState:
    request_id = state.get("request_id", "unknown")
    sub_tasks = state.get("sub_tasks", [])
    tenant_id = state["tenant_id"]

    current_task: SubTask | None = None
    for task in sub_tasks:
        if task.task_type == "process" and task.status in ["pending", "running"]:
            current_task = task
            break

    if not current_task:
        log_agent_execution(request_id, "process_agent", "no_pending_task")
        return state

    current_task.status = "running"
    log_task_status(request_id, current_task, "started")

    try:
        agent = ProcessAgent()
        input_data = current_task.input_data

        log_agent_execution(request_id, "process_agent", "executing",
                          input_keys=list(input_data.keys()))

        if "task_id" in input_data:
            result = agent.get_status(
                task_id=input_data["task_id"],
                tenant_id=tenant_id,
            )
            log_agent_execution(request_id, "process_agent", "got_status",
                            task_id=input_data["task_id"][:8])
        elif "item_code" in input_data:
            result = agent.get_history(
                item_code=input_data["item_code"],
                tenant_id=tenant_id,
            )
            log_agent_execution(request_id, "process_agent", "got_history",
                            item_code=input_data["item_code"])
        else:
            raise ValueError("Invalid input data for process task")

        current_task.status = "completed"
        current_task.output_data = result

        log_agent_execution(request_id, "process_agent", "completed")
        log_task_status(request_id, current_task, "completed")

    except NeedsClarificationError as e:
        current_task.status = "needs_clarification"
        current_task.error_message = str(e)

        log_agent_execution(request_id, "process_agent", "needs_clarification", question=str(e.question))
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

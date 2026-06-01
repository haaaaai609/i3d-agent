"""Conditional routing functions for the I3D Agent workflow."""

from typing import Dict, Any, List

from i3d_agent.workflow.state import SubTask, WorkflowState
from i3d_agent.workflow.utils import get_next_pending_task, get_failed_task


def should_route_to_memory(state: WorkflowState) -> str:
    """判断是否需要加载记忆。"""
    if not state.get("conversation_history"):
        return "load_memory"
    return "skip_memory"


def check_clarification_needed(state: WorkflowState) -> str:
    """检查是否有 Agent 需要澄清。"""
    if state.get("pending_clarification"):
        return "request_clarification"
    return "continue_execution"


def check_all_tasks_completed(state: WorkflowState) -> str:
    """检查所有任务是否完成。"""
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])

    failed_task = get_failed_task(sub_tasks)
    if failed_task:
        return "handle_error"

    pending_task = get_next_pending_task(sub_tasks)
    if pending_task:
        return "continue_tasks"

    return "aggregate_results"


def decide_next_agent(state: WorkflowState) -> str:
    """决定下一个执行的 Agent。"""
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])

    next_task = get_next_pending_task(sub_tasks)

    if not next_task:
        return "aggregator"

    return f"{next_task.task_type}_agent"


def classify_error(state: WorkflowState) -> str:
    """分类错误并决定处理方式。"""
    error = state.get("error")

    if not error:
        return "no_error"

    if error.error_type == "retriable":
        return "retry"
    elif error.error_type == "degradable":
        return "degrade"
    else:
        return "fail"


def check_task_completion(state: WorkflowState, task_id: str) -> str:
    """检查单个任务的完成状态。"""
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])

    for task in sub_tasks:
        if task.task_id == task_id:
            if task.status == "completed":
                return "completed"
            elif task.status == "needs_clarification":
                return "needs_clarification"
            elif task.status == "failed":
                return "failed"

    return "completed"

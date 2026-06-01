"""Utility functions for the I3D Agent workflow."""

from typing import Dict, List, Optional, Any

from i3d_agent.agents.supervisor import SupervisorAgent
from i3d_agent.workflow.state import SubTask, ErrorInfo


def is_simple_query(query: str, max_length: int = 50) -> bool:
    """判断查询是否为简单查询。"""
    if len(query) > max_length:
        return False

    multi_intent_keywords = ["并", "然后", "之后", "接着", "再", "和", "同时"]
    query_lower = query.lower()
    for keyword in multi_intent_keywords:
        if keyword in query_lower:
            return False

    supervisor = SupervisorAgent()
    intent_result = supervisor.analyze_intent(query)

    if intent_result["confidence"] == "high" and intent_result["task_type"] != "general":
        return True

    if intent_result["confidence"] == "low" and not intent_result["matched_keywords"]:
        return False

    return True


def get_task_by_id(tasks: list[SubTask], task_id: str) -> Optional[SubTask]:
    """通过任务 ID 获取任务。"""
    for task in tasks:
        if task.task_id == task_id:
            return task
    return None


def get_next_pending_task(tasks: list[SubTask]) -> Optional[SubTask]:
    """获取下一个待处理的任务。"""
    for task in tasks:
        if task.status in ["pending", "running"]:
            return task
    return None


def get_failed_task(tasks: list[SubTask]) -> Optional[SubTask]:
    """获取失败的任务。"""
    for task in tasks:
        if task.status == "failed":
            return task
    return None


def update_task_status(
    tasks: list[SubTask],
    task_id: str,
    status: str,
    output_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> list[SubTask]:
    """更新任务状态。"""
    for task in tasks:
        if task.task_id == task_id:
            task.status = status
            if output_data is not None:
                task.output_data = output_data
            if error_message is not None:
                task.error_message = error_message
            break
    return tasks


def is_retriable_error(error: ErrorInfo) -> bool:
    """判断错误是否可重试。"""
    return error.error_type == "retriable"


def is_degradable_error(error: ErrorInfo) -> bool:
    """判断错误是否可降级处理。"""
    return error.error_type == "degradable"


def is_critical_error(error: ErrorInfo) -> bool:
    """判断是否为严重错误。"""
    return error.error_type == "critical"

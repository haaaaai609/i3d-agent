"""Utility functions for the I3D Agent workflow."""

import time
import uuid
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Generator, Callable

from i3d_agent.agents.supervisor import SupervisorAgent
from i3d_agent.workflow.state import SubTask, ErrorInfo
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)

# 工作流上下文存储
_workflow_context: Dict[str, Dict[str, Any]] = {}


def get_workflow_context(request_id: str) -> Dict[str, Any]:
    """获取工作流上下文。"""
    if request_id not in _workflow_context:
        _workflow_context[request_id] = {
            "request_id": request_id,
            "start_time": time.time(),
            "node_count": 0,
            "nodes_visited": [],
        }
    return _workflow_context[request_id]


def clear_workflow_context(request_id: str) -> None:
    """清理工作流上下文。"""
    _workflow_context.pop(request_id, None)


@contextmanager
def workflow_context(request_id: str) -> Generator[Dict[str, Any], None, None]:
    """工作流上下文管理器。"""
    ctx = get_workflow_context(request_id)
    logger.info(f"[{request_id}] 🧠 WORKFLOW_START | request_id={request_id}")
    try:
        yield ctx
    finally:
        duration = time.time() - ctx["start_time"]
        logger.info(
            f"[{request_id}] 🧠 WORKFLOW_END | request_id={request_id} | "
            f"total_duration={duration:.2f}s | nodes_visited={len(ctx['nodes_visited'])}"
        )
        clear_workflow_context(request_id)


@contextmanager
def node_execution(
    node_name: str,
    request_id: str,
    **extra_info
) -> Generator[None, None, None]:
    """节点执行上下文管理器，记录节点开始和结束。"""
    start_time = time.time()
    ctx = get_workflow_context(request_id)
    ctx["node_count"] += 1
    ctx["nodes_visited"].append(node_name)

    # 构建额外的日志信息
    extra_str = " | ".join([f"{k}={v}" for k, v in extra_info.items()])
    if extra_str:
        logger.info(f"[{request_id}] 🔄 NODE_START | node={node_name} | {extra_str}")
    else:
        logger.info(f"[{request_id}] 🔄 NODE_START | node={node_name}")

    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"[{request_id}] 🔄 NODE_END | node={node_name} | duration={duration:.2f}s")


def log_route_decision(
    request_id: str,
    from_node: str,
    to_node: str,
    reason: str,
    **extra_info
) -> None:
    """记录路由决策。"""
    extra_str = " | ".join([f"{k}={v}" for k, v in extra_info.items()])
    if extra_str:
        logger.info(
            f"[{request_id}] 🔀 ROUTE | from={from_node} | to={to_node} | reason={reason} | {extra_str}"
        )
    else:
        logger.info(f"[{request_id}] 🔀 ROUTE | from={from_node} | to={to_node} | reason={reason}")


def log_intent_detected(
    request_id: str,
    task_type: str,
    agent: str,
    confidence: str,
    query_preview: str
) -> None:
    """记录意图检测结果。"""
    logger.info(
        f"[{request_id}] 🎯 INTENT_DETECTED | task_type={task_type} | agent={agent} | "
        f"confidence={confidence} | query_preview={query_preview[:50]}..."
    )


def log_agent_execution(
    request_id: str,
    agent_name: str,
    action: str,
    **extra_info
) -> None:
    """记录 Agent 执行状态。"""
    extra_str = " | ".join([f"{k}={v}" for k, v in extra_info.items()])
    if extra_str:
        logger.info(f"[{request_id}] 🔍 AGENT_{action.upper()} | agent={agent_name} | {extra_str}")
    else:
        logger.info(f"[{request_id}] 🔍 AGENT_{action.upper()} | agent={agent_name}")


def log_task_status(
    request_id: str,
    task: SubTask,
    status_change: str = ""
) -> None:
    """记录任务状态变化。"""
    if status_change:
        logger.info(
            f"[{request_id}] 📋 TASK_STATUS | task_id={task.task_id[:8]} | "
            f"type={task.task_type} | status={task.status} | change={status_change}"
        )
    else:
        logger.info(
            f"[{request_id}] 📋 TASK_STATUS | task_id={task.task_id[:8]} | "
            f"type={task.task_type} | status={task.status}"
        )


def log_aggregation(request_id: str, completed_count: int, total_count: int) -> None:
    """记录聚合操作。"""
    logger.info(
        f"[{request_id}] 📊 AGGREGATING | completed_tasks={completed_count} | total_tasks={total_count}"
    )


def log_error_handling(
    request_id: str,
    task_id: str,
    error_type: str,
    message: str
) -> None:
    """记录错误处理。"""
    logger.warning(
        f"[{request_id}] ⚠️ ERROR_HANDLING | task_id={task_id[:8]} | "
        f"error_type={error_type} | message={message[:100]}"
    )


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

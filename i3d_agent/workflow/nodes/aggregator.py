"""Aggregator node for the I3D Agent workflow."""

from typing import List, Dict, Any, Optional

from i3d_agent.workflow.state import WorkflowState, SubTask
from i3d_agent.workflow.utils import log_aggregation, log_agent_execution
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


async def aggregator_node(state: WorkflowState) -> WorkflowState:
    request_id = state.get("request_id", "unknown")
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])
    completed_tasks = [task for task in sub_tasks if task.status == "completed"]

    log_aggregation(request_id, len(completed_tasks), len(sub_tasks))

    if not completed_tasks:
        state["response"] = "抱歉，无法完成您的请求。"
        state["should_continue"] = False
        log_agent_execution(request_id, "aggregator", "no_completed_tasks")
        return state

    response_parts = []
    sources = []
    thought_process_parts = []

    for task in completed_tasks:
        output = task.output_data
        if not output:
            continue

        if task.task_type == "search":
            results = output.get("results", [])
            if results:
                response_parts.append(f"找到 {len(results)} 个结果：")
                for i, result in enumerate(results[:5], 1):
                    name = result.get("name", result.get("item_code", ""))
                    response_parts.append(f"{i}. {name}")
                thought_process_parts.append(f"执行搜索任务，找到 {len(results)} 个结果")
                log_agent_execution(request_id, "aggregator", "aggregated_search",
                                results_count=len(results))

        elif task.task_type == "rag":
            answer = output.get("answer", "")
            if answer:
                response_parts.append(answer)
            task_sources = output.get("sources", [])
            sources.extend(task_sources)
            thought_process_parts.append("执行文档检索任务")
            log_agent_execution(request_id, "aggregator", "aggregated_rag",
                            sources_count=len(task_sources),
                            answer_length=len(answer))

        elif task.task_type == "process":
            status = output.get("status", "unknown")
            progress = output.get("progress", 0)
            response_parts.append(f"任务状态：{status}，进度：{progress}%")
            thought_process_parts.append("查询处理状态")
            log_agent_execution(request_id, "aggregator", "aggregated_process",
                            status=status, progress=progress)

        elif task.task_type == "general":
            answer = output.get("answer", "")
            if answer:
                response_parts.append(answer)
            thought_process_parts.append("执行通用对话")
            log_agent_execution(request_id, "aggregator", "aggregated_general")

    if response_parts:
        state["response"] = "\n\n".join(response_parts)
    else:
        state["response"] = "已完成任务，但没有返回结果。"

    if sources:
        state["sources"] = sources

    if thought_process_parts:
        state["thought_process"] = "；".join(thought_process_parts)

    state["metadata"] = {
        "completed_tasks": len(completed_tasks),
        "total_tasks": len(sub_tasks),
    }

    state["should_continue"] = False

    logger.info(
        f"[{request_id}] ✅ AGGREGATOR_COMPLETE | "
        f"response_length={len(state['response'])} | sources={len(sources) if sources else 0}"
    )

    return state

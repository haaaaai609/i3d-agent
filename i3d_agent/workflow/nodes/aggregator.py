"""Aggregator node for the I3D Agent workflow."""

from typing import List, Dict, Any, Optional

from i3d_agent.workflow.state import WorkflowState, SubTask


async def aggregator_node(state: WorkflowState) -> WorkflowState:
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])
    completed_tasks = [task for task in sub_tasks if task.status == "completed"]

    if not completed_tasks:
        state["response"] = "抱歉，无法完成您的请求。"
        state["should_continue"] = False
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

        elif task.task_type == "rag":
            answer = output.get("answer", "")
            if answer:
                response_parts.append(answer)
            task_sources = output.get("sources", [])
            sources.extend(task_sources)
            thought_process_parts.append("执行文档检索任务")

        elif task.task_type == "process":
            status = output.get("status", "unknown")
            progress = output.get("progress", 0)
            response_parts.append(f"任务状态：{status}，进度：{progress}%")
            thought_process_parts.append("查询处理状态")

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

    return state

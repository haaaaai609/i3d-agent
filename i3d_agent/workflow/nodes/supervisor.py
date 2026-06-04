"""Supervisor node for the I3D Agent workflow."""

import uuid
from typing import Dict, Any, List

from i3d_agent.agents.supervisor import SupervisorAgent
from i3d_agent.workflow.state import WorkflowState, SubTask
from i3d_agent.workflow.utils import (
    log_intent_detected,
    log_task_status,
    log_agent_execution,
)
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


async def supervisor_node(state: WorkflowState) -> WorkflowState:
    request_id = state.get("request_id", "unknown")
    query = state["query"]
    tenant_id = state["tenant_id"]
    clarification_answer = state.get("clarification_answer")
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])
    conversation_history = state.get("conversation_history", [])

    # 处理澄清答案
    if clarification_answer and sub_tasks:
        log_agent_execution(request_id, "supervisor", "processing_clarification",
                          clarification_answer=clarification_answer[:50])
        for task in sub_tasks:
            if task.status == "needs_clarification":
                task.status = "pending"
                task.input_data["clarification"] = clarification_answer
                log_task_status(request_id, task, "clarification_received")
                break
        state["clarification_answer"] = None
        return state

    # 如果已有子任务，直接返回
    if sub_tasks:
        log_agent_execution(request_id, "supervisor", "has_existing_tasks",
                          task_count=len(sub_tasks))
        return state

    supervisor = SupervisorAgent()
    intent_result = supervisor.analyze_intent(query)

    # 记录意图检测结果
    log_intent_detected(
        request_id,
        intent_result["task_type"],
        intent_result.get("agent", "unknown"),
        intent_result["confidence"],
        query[:100]
    )

    # Handle general queries directly with LLM
    if intent_result["task_type"] == "general":
        log_agent_execution(request_id, "supervisor", "handling_general_query")

        response = await supervisor.chat(
            message=query,
            conversation_history=conversation_history,
            tenant_id=tenant_id,
        )

        state["response"] = response.get("answer", "抱歉，无法生成回复。")
        state["metadata"] = {"agent": "supervisor", "task_type": "general"}
        state["should_continue"] = False

        logger.info(
            f"[{request_id}] ✅ SUPERVISOR_GENERAL_COMPLETE | "
            f"response_length={len(state['response'])}"
        )
        return state

    # Create task for specialized agents
    task = SubTask(
        task_id=str(uuid.uuid4()),
        task_type=intent_result["task_type"],
        agent=intent_result["agent"],
        status="pending",
        input_data={"query": query, "tenant_id": tenant_id},
    )

    state["sub_tasks"] = [task]
    log_task_status(request_id, task, "created")
    log_agent_execution(request_id, "supervisor", "task_created",
                        task_type=task.task_type, agent=task.agent)

    return state

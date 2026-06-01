"""Supervisor node for the I3D Agent workflow."""

import uuid
from typing import Dict, Any, List

from i3d_agent.agents.supervisor import SupervisorAgent
from i3d_agent.workflow.state import WorkflowState, SubTask
from i3d_agent.workflow.utils import is_simple_query


async def supervisor_node(state: WorkflowState) -> WorkflowState:
    query = state["query"]
    tenant_id = state["tenant_id"]
    clarification_answer = state.get("clarification_answer")
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])

    if clarification_answer and sub_tasks:
        for task in sub_tasks:
            if task.status == "needs_clarification":
                task.status = "pending"
                task.input_data["clarification"] = clarification_answer
                break
        state["clarification_answer"] = None
        return state

    if sub_tasks:
        return state

    if is_simple_query(query):
        supervisor = SupervisorAgent()
        intent_result = supervisor.analyze_intent(query)

        task = SubTask(
            task_id=str(uuid.uuid4()),
            task_type=intent_result["task_type"],
            agent=intent_result["agent"],
            status="pending",
            input_data={"query": query, "tenant_id": tenant_id},
        )

        state["sub_tasks"] = [task]
    else:
        task = SubTask(
            task_id=str(uuid.uuid4()),
            task_type="search",
            agent="search_agent",
            status="pending",
            input_data={"query": query, "tenant_id": tenant_id},
        )

        state["sub_tasks"] = [task]

    return state

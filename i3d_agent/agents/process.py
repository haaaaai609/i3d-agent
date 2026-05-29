"""Process agent for file processing task status queries."""

from typing import Any, Dict, List, Optional

from i3d_agent.agents.base import AgentConfig, BaseAgent
from i3d_agent.tools.process_tools import (
    get_task_status,
    get_processing_history,
    retry_failed_task,
    diagnose_error,
)


class ProcessAgent(BaseAgent):
    """Process agent for file processing task management.

    This agent provides capabilities for:
    - Querying task status by task ID
    - Retrieving processing history for items
    - Retrying failed tasks
    - Diagnosing errors with suggested solutions
    """

    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the process agent.

        Args:
            config: Optional agent configuration. Uses default if not provided.
        """
        if config is None:
            config = AgentConfig(
                name="process",
                role="task_processor",
                instructions="Query task status, retrieve processing history, retry failed tasks, and diagnose errors.",
            )

        # Initialize tools
        tools = [
            {
                "name": "get_task_status",
                "description": "Query file processing task status by task ID",
            },
            {
                "name": "get_processing_history",
                "description": "Get processing history for a specific item/part",
            },
            {
                "name": "retry_failed_task",
                "description": "Retry a failed file processing task",
            },
            {
                "name": "diagnose_error",
                "description": "Diagnose error causes and provide suggested solutions",
            },
        ]

        super().__init__(config=config, tools=tools)

    def get_status(self, task_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get task status by task ID.

        Args:
            task_id: The unique identifier for the processing task
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            Dictionary with keys:
                - status: "success" or "error"
                - task_id: Task identifier
                - task_status: Current status (pending, running, success, failed)
                - progress: Progress percentage (0-100)
                - stage: Current processing stage
                - created_at: Task creation timestamp
                - updated_at: Last update timestamp
                - error_message: Error details if status is failed
                - error: Error message if status is "error"

        Raises:
            ValueError: If task_id is empty
            httpx.HTTPError: If the API request fails
        """
        try:
            result = get_task_status(task_id=task_id, tenant_id=tenant_id)
            return {
                "status": "success",
                "task_id": task_id,
                **result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "task_id": task_id,
            }

    def get_history(
        self, item_code: str, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get processing history for a specific item/part.

        Args:
            item_code: The item code to retrieve processing history for
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            Dictionary with keys:
                - status: "success", "no_results", or "error"
                - item_code: Item code
                - history: List of processing records
                - count: Number of records
                - error: Error message if status is "error"

        Raises:
            ValueError: If item_code is empty
            httpx.HTTPError: If the API request fails
        """
        try:
            history = get_processing_history(item_code=item_code, tenant_id=tenant_id)
            return {
                "status": "success" if history else "no_results",
                "item_code": item_code,
                "history": history,
                "count": len(history),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "item_code": item_code,
                "history": [],
                "count": 0,
            }

    def retry(self, task_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Retry a failed file processing task.

        Args:
            task_id: The failed task identifier to retry
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            Dictionary with keys:
                - status: "success" or "error"
                - task_id: Original task identifier
                - new_task_id: New task identifier for the retry attempt (on success)
                - message: Status message
                - error: Error message if status is "error"

        Raises:
            ValueError: If task_id is empty
            httpx.HTTPError: If the API request fails
        """
        try:
            result = retry_failed_task(task_id=task_id, tenant_id=tenant_id)
            return {
                "status": "success",
                "task_id": task_id,
                "new_task_id": result.get("new_task_id"),
                "message": result.get("message", "Retry initiated"),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "task_id": task_id,
            }

    def diagnose(
        self,
        error_message: str,
        component: str = "unknown",
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Diagnose error causes and provide suggested solutions.

        Args:
            error_message: The error message to diagnose
            component: The component that generated the error
            tenant_id: Optional tenant ID for context (unused in diagnosis)

        Returns:
            Dictionary with keys:
                - status: "success" or "error"
                - error_type: Categorized error type
                - severity: Error severity level (low, medium, high)
                - likely_cause: Most likely cause of the error
                - suggested_solutions: List of suggested solutions
                - related_docs: Links to relevant documentation
                - error: Error message if status is "error"

        Raises:
            ValueError: If error_message is empty
        """
        try:
            result = diagnose_error(
                error_message=error_message, component=component, tenant_id=tenant_id
            )
            return {
                "status": "success",
                "error_message": error_message,
                "component": component,
                **result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_message": error_message,
                "component": component,
            }


__all__ = ["ProcessAgent"]

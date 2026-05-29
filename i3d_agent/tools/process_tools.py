"""
Process tools for file processing task management.

This module provides LangChain-compatible tools for interacting with
the XXL-Job based file processing system, including task status queries,
processing history retrieval, failed task retry, and error diagnosis.
"""

import re
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from i3d_agent.config.settings import settings
import httpx


@tool
def get_task_status(task_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Query file processing task status by task ID.

    Retrieves current status information for a specific file processing task
    including progress, stage, and any error messages if failed.

    Args:
        task_id: The unique identifier for the processing task
        tenant_id: Optional tenant ID for multi-tenancy. Uses default if not provided

    Returns:
        Dict[str, Any]: Task status information with keys:
            - task_id: Task identifier
            - status: Current status (pending, running, success, failed)
            - progress: Progress percentage (0-100)
            - stage: Current processing stage
            - created_at: Task creation timestamp
            - updated_at: Last update timestamp
            - error_message: Error details if status is failed

    Raises:
        ValueError: If task_id is empty
        httpx.HTTPError: If the API request fails

    Example:
        >>> status = get_task_status("TASK-12345")
        >>> print(f"Task status: {status['status']}, Progress: {status['progress']}%")
    """
    if not task_id or not task_id.strip():
        raise ValueError("task_id cannot be empty")

    tenant_id = tenant_id or settings.DEFAULT_TENANT

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{settings.XXL_JOB_URL}/api/tasks/{task_id}",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"Task status API request failed: {str(e)}")


@tool
def get_processing_history(item_code: str, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get processing history for a specific part/item.

    Retrieves historical processing records for a given item code, including
    previous successful and failed processing attempts with timestamps.

    Args:
        item_code: The item code to retrieve processing history for
        tenant_id: Optional tenant ID for multi-tenancy. Uses default if not provided

    Returns:
        List[Dict[str, Any]]: List of processing records with keys:
            - task_id: Task identifier
            - item_code: Processed item code
            - status: Processing result status
            - timestamp: Processing timestamp
            - duration_seconds: Processing duration
            - file_type: Processed file type
            - error_message: Error details if failed

    Raises:
        ValueError: If item_code is empty
        httpx.HTTPError: If the API request fails

    Example:
        >>> history = get_processing_history("BOLT-1234")
        >>> for record in history:
        ...     print(f"{record['timestamp']}: {record['status']}")
    """
    if not item_code or not item_code.strip():
        raise ValueError("item_code cannot be empty")

    tenant_id = tenant_id or settings.DEFAULT_TENANT

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{settings.XXL_JOB_URL}/api/history/{item_code}",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json().get("history", [])
    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"Processing history API request failed: {str(e)}")


@tool
def retry_failed_task(task_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retry a failed file processing task.

    Re-submits a previously failed task for reprocessing with the same
    parameters. Useful for handling transient failures.

    Args:
        task_id: The failed task identifier to retry
        tenant_id: Optional tenant ID for multi-tenancy. Uses default if not provided

    Returns:
        Dict[str, Any]: Retry response with keys:
            - success: Whether retry was initiated successfully
            - new_task_id: New task identifier for the retry attempt
            - original_task_id: Original failed task identifier
            - message: Status message

    Raises:
        ValueError: If task_id is empty
        httpx.HTTPError: If the API request fails

    Example:
        >>> result = retry_failed_task("TASK-12345")
        >>> if result['success']:
        ...     print(f"Retry started with new task ID: {result['new_task_id']}")
    """
    if not task_id or not task_id.strip():
        raise ValueError("task_id cannot be empty")

    tenant_id = tenant_id or settings.DEFAULT_TENANT

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.XXL_JOB_URL}/api/tasks/{task_id}/retry",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"Retry task API request failed: {str(e)}")


@tool
def diagnose_error(
    error_message: str,
    component: str = "unknown",
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Diagnose error causes and provide suggested solutions.

    Analyzes error messages using pattern matching to identify common issues
    and provides actionable solutions for file processing errors.

    Args:
        error_message: The error message to diagnose
        component: The component that generated the error (e.g., "parser", "validator", "storage")
        tenant_id: Optional tenant ID for multi-tenancy context

    Returns:
        Dict[str, Any]: Diagnosis result with keys:
            - error_type: Categorized error type
            - severity: Error severity level (low, medium, high)
            - likely_cause: Most likely cause of the error
            - suggested_solutions: List of suggested solutions
            - related_docs: Links to relevant documentation

    Raises:
        ValueError: If error_message is empty

    Example:
        >>> diagnosis = diagnose_error("Failed to parse STEP file", component="parser")
        >>> print(f"Error type: {diagnosis['error_type']}")
        >>> print(f"Suggested solutions: {diagnosis['suggested_solutions']}")
    """
    if not error_message or not error_message.strip():
        raise ValueError("error_message cannot be empty")

    # Simple pattern-based diagnosis logic
    error_msg_lower = error_message.lower()

    # File format errors
    if any(pattern in error_msg_lower for pattern in ["invalid format", "unsupported format", "file format"]):
        return {
            "error_type": "file_format_error",
            "severity": "high",
            "likely_cause": "The file format is not supported or corrupted",
            "suggested_solutions": [
                "Verify the file format matches the expected type (STEP, STL, OBJ)",
                "Check if the file is corrupted by opening it in a CAD viewer",
                "Re-export the file from the source CAD system",
                "Ensure file headers are intact and not modified",
            ],
            "related_docs": [
                "Supported file formats: STEP (.stp, .step), STL (.stl), OBJ (.obj)",
                "File validation requirements and specifications",
            ],
        }

    # Parsing errors
    if any(pattern in error_msg_lower for pattern in ["parse", "syntax", "invalid structure"]):
        return {
            "error_type": "parsing_error",
            "severity": "high",
            "likely_cause": f"File structure parsing failed in {component} component",
            "suggested_solutions": [
                "Validate the file against the format specification",
                "Check for incomplete geometry or mesh data",
                "Ensure all required metadata is present",
                "Try repairing the file using CAD repair tools",
            ],
            "related_docs": [
                "File format specification and validation guidelines",
                "Common parsing errors and their fixes",
            ],
        }

    # Network/connection errors
    if any(pattern in error_msg_lower for pattern in ["connection", "timeout", "network", "unreachable"]):
        return {
            "error_type": "network_error",
            "severity": "medium",
            "likely_cause": "Network connectivity or timeout issue",
            "suggested_solutions": [
                "Check network connectivity to the service endpoint",
                "Verify the service is running and accessible",
                "Increase timeout values if processing large files",
                "Check firewall rules and proxy settings",
            ],
            "related_docs": [
                "Network configuration and firewall settings",
                "Service endpoint URLs and ports",
            ],
        }

    # Storage errors
    if any(pattern in error_msg_lower for pattern in ["storage", "disk", "space", "upload"]):
        return {
            "error_type": "storage_error",
            "severity": "high",
            "likely_cause": "Storage system error or insufficient space",
            "suggested_solutions": [
                "Check available disk space on the storage server",
                "Verify storage service is running (MinIO/S3)",
                "Check file size limits and quotas",
                "Verify write permissions for the storage path",
            ],
            "related_docs": [
                "Storage system configuration and limits",
                "MinIO/S3 connection troubleshooting",
            ],
        }

    # Validation errors
    if any(pattern in error_msg_lower for pattern in ["validation", "invalid", "constraint", "violation"]):
        return {
            "error_type": "validation_error",
            "severity": "medium",
            "likely_cause": f"Data validation failed in {component} component",
            "suggested_solutions": [
                "Review validation rules and requirements",
                "Check all required fields are populated",
                "Verify data types match expected formats",
                "Ensure business logic constraints are satisfied",
            ],
            "related_docs": [
                "Data validation rules and constraints",
                "Business logic requirements guide",
            ],
        }

    # Default: unknown error
    return {
        "error_type": "unknown_error",
        "severity": "medium",
        "likely_cause": "Unable to categorize the error automatically",
        "suggested_solutions": [
            "Check the full error logs for more details",
            "Contact support with the error message and task ID",
            "Review recent changes that might have affected the system",
            "Check if similar errors have occurred before",
        ],
        "related_docs": [
            "General troubleshooting guide",
            "Error log analysis procedures",
        ],
    }


__all__ = [
    "get_task_status",
    "get_processing_history",
    "retry_failed_task",
    "diagnose_error",
]

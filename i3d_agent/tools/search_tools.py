"""
Search tools for I3D model and image search APIs.

This module provides LangChain-compatible tools for interacting with
the I3D search services, including 3D model search, 2D image search,
and result filtering capabilities.
"""

import base64
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from i3d_agent.config.settings import settings
import httpx


@tool
def search_3d_model(
    item_code: str,
    file_type: str = "step",
    top_k: int = 10,
    tenant_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search for 3D models using the I3D 3D search API.

    Performs semantic search on 3D model database to find similar models
    based on the provided item code. Supports multiple file formats and
    configurable result counts.

    Args:
        item_code: The item code to search for (e.g., "BOLT-1234")
        file_type: File type filter (e.g., "step", "stl", "obj"). Defaults to "step"
        top_k: Maximum number of results to return (default: 10, max: 100)
        tenant_id: Optional tenant ID for multi-tenancy. Uses default if not provided

    Returns:
        List[Dict[str, Any]]: List of search results with keys:
            - item_code: Model identifier
            - similarity: Float score (0-1)
            - file_type: Model file format
            - metadata: Additional model information

    Raises:
        ValueError: If item_code is empty or top_k is invalid
        httpx.HTTPError: If the API request fails

    Example:
        >>> results = search_3d_model("BOLT-1234", file_type="step", top_k=5)
        >>> print(f"Found {len(results)} similar models")
    """
    if not item_code or not item_code.strip():
        raise ValueError("item_code cannot be empty")

    if top_k < 1 or top_k > 100:
        raise ValueError("top_k must be between 1 and 100")

    tenant_id = tenant_id or settings.DEFAULT_TENANT

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.INFER_ENGINEER_URL}/api/v1/search/3d",
                json={
                    "item_code": item_code,
                    "file_type": file_type,
                    "top_k": top_k,
                },
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json().get("results", [])
    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"3D search API request failed: {str(e)}")


@tool
def search_2d_image(
    image_base64: str,
    file_type: str = "png",
    top_k: int = 10,
    tenant_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search for 2D images using the I3D 2D search API.

    Performs visual similarity search on 2D image database using
    the provided base64-encoded image as query.

    Args:
        image_base64: Base64-encoded image data (without data URL prefix)
        file_type: Image format type (e.g., "png", "jpg", "jpeg"). Defaults to "png"
        top_k: Maximum number of results to return (default: 10, max: 100)
        tenant_id: Optional tenant ID for multi-tenancy. Uses default if not provided

    Returns:
        List[Dict[str, Any]]: List of search results with keys:
            - image_id: Image identifier
            - similarity: Float score (0-1)
            - url: Image URL
            - metadata: Additional image information

    Raises:
        ValueError: If image_base64 is empty or invalid
        httpx.HTTPError: If the API request fails

    Example:
        >>> with open("query.png", "rb") as f:
        ...     img_data = base64.b64encode(f.read()).decode()
        >>> results = search_2d_image(img_data, file_type="png", top_k=5)
    """
    if not image_base64 or not image_base64.strip():
        raise ValueError("image_base64 cannot be empty")

    if top_k < 1 or top_k > 100:
        raise ValueError("top_k must be between 1 and 100")

    tenant_id = tenant_id or settings.DEFAULT_TENANT

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.INFER_ENGINEER_URL}/api/v1/search/2d",
                json={
                    "image_data": image_base64,
                    "file_type": file_type,
                    "top_k": top_k,
                },
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json().get("results", [])
    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"2D search API request failed: {str(e)}")


@tool
def filter_by_attributes(
    results: List[Dict[str, Any]],
    material: Optional[str] = None,
    weight_min: Optional[float] = None,
    weight_max: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Filter search results by material and weight attributes.

    Performs local filtering on search results to narrow down based on
    material type and weight range. This is useful for post-processing
    search API results.

    Args:
        results: List of search result dictionaries to filter
        material: Optional material filter (e.g., "steel", "aluminum", "plastic")
        weight_min: Optional minimum weight (in kg)
        weight_max: Optional maximum weight (in kg)

    Returns:
        List[Dict[str, Any]]: Filtered list of results matching all criteria

    Raises:
        ValueError: If results is not a list

    Example:
        >>> filtered = filter_by_attributes(
        ...     results,
        ...     material="steel",
        ...     weight_min=0.1,
        ...     weight_max=5.0
        ... )
    """
    if not isinstance(results, list):
        raise ValueError("results must be a list")

    filtered = results

    if material:
        filtered = [
            r
            for r in filtered
            if r.get("metadata", {}).get("material", "").lower() == material.lower()
        ]

    if weight_min is not None:
        filtered = [
            r
            for r in filtered
            if r.get("metadata", {}).get("weight", float("inf")) >= weight_min
        ]

    if weight_max is not None:
        filtered = [
            r
            for r in filtered
            if r.get("metadata", {}).get("weight", 0) <= weight_max
        ]

    return filtered


@tool
def get_model_details(
    item_code: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get detailed information about a specific 3D model.

    Retrieves comprehensive metadata for a model including specifications,
    materials, dimensions, and file availability.

    Args:
        item_code: The item code to retrieve details for
        tenant_id: Optional tenant ID for multi-tenancy. Uses default if not provided

    Returns:
        Dict[str, Any]: Model details with keys:
            - item_code: Model identifier
            - name: Model name
            - description: Model description
            - material: Material specification
            - weight: Weight in kg
            - dimensions: Object dimensions (L x W x H)
            - files: List of available file formats
            - metadata: Additional properties

    Raises:
        ValueError: If item_code is empty
        httpx.HTTPError: If the API request fails

    Example:
        >>> details = get_model_details("BOLT-1234")
        >>> print(f"Material: {details['material']}, Weight: {details['weight']}kg")
    """
    if not item_code or not item_code.strip():
        raise ValueError("item_code cannot be empty")

    tenant_id = tenant_id or settings.DEFAULT_TENANT

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{settings.INFER_ENGINEER_URL}/api/v1/models/{item_code}",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"Model details API request failed: {str(e)}")


__all__ = [
    "search_3d_model",
    "search_2d_image",
    "filter_by_attributes",
    "get_model_details",
]

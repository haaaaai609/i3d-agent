"""Search agent for 3D model and 2D image search."""

from typing import Any, Dict, List, Optional

from i3d_agent.agents.base import AgentConfig, BaseAgent
from i3d_agent.tools.search_tools import (
    search_3d_model,
    search_2d_image,
    filter_by_attributes,
    get_model_details,
)


class SearchAgent(BaseAgent):
    """Search agent for 3D/2D model and image search.

    This agent provides search capabilities for:
    - 3D models using item codes
    - 2D images using base64-encoded image data
    - Text-based search queries
    - Result filtering by attributes
    - Model detail retrieval
    """

    # Search types
    SEARCH_TYPE_3D = "3d"
    SEARCH_TYPE_2D = "2d"
    SEARCH_TYPE_TEXT = "text"

    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the search agent.

        Args:
            config: Optional agent configuration. Uses default if not provided.
        """
        if config is None:
            config = AgentConfig(
                name="search",
                role="model_searcher",
                instructions="Search for 3D models, 2D images, and related resources.",
            )

        # Initialize tools
        tools = [
            {
                "name": "search_3d_model",
                "description": "Search for 3D models using item code",
            },
            {
                "name": "search_2d_image",
                "description": "Search for 2D images using base64 image data",
            },
            {
                "name": "filter_by_attributes",
                "description": "Filter results by material and weight",
            },
            {
                "name": "get_model_details",
                "description": "Get detailed information about a model",
            },
        ]

        super().__init__(config=config, tools=tools)

    def search(
        self,
        query: str,
        search_type: str = SEARCH_TYPE_3D,
        params: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute search based on type and parameters.

        Args:
            query: Search query (item code for 3D, base64 image for 2D, text query)
            search_type: Type of search - "3d", "2d", or "text"
            params: Optional additional parameters (file_type, top_k, filters, etc.)
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            Dictionary with keys:
                - search_type: Type of search performed
                - results: List of search results
                - count: Number of results
                - status: "success", "no_results", or "error"
                - error: Error message if status is "error"

        Raises:
            ValueError: If search_type is invalid
            httpx.HTTPError: If the API request fails
        """
        if params is None:
            params = {}

        search_type = search_type.lower()

        try:
            if search_type == self.SEARCH_TYPE_3D:
                return self._search_3d(query, params, tenant_id)
            elif search_type == self.SEARCH_TYPE_2D:
                return self._search_2d(query, params, tenant_id)
            elif search_type == self.SEARCH_TYPE_TEXT:
                return self._search_text(query, params)
            else:
                valid_types = [self.SEARCH_TYPE_3D, self.SEARCH_TYPE_2D, self.SEARCH_TYPE_TEXT]
                raise ValueError(
                    f"Invalid search_type '{search_type}'. Must be one of: {valid_types}"
                )
        except Exception as e:
            return {
                "search_type": search_type,
                "results": [],
                "count": 0,
                "status": "error",
                "error": str(e),
            }

    def _search_3d(
        self,
        item_code: str,
        params: Dict[str, Any],
        tenant_id: Optional[str],
    ) -> Dict[str, Any]:
        """Execute 3D model search.

        Args:
            item_code: Item code to search for
            params: Additional parameters (file_type, top_k, filters)
            tenant_id: Optional tenant ID

        Returns:
            Search results dictionary
        """
        file_type = params.get("file_type", "step")
        top_k = params.get("top_k", 10)

        # Perform search
        results = search_3d_model(
            item_code=item_code,
            file_type=file_type,
            top_k=top_k,
            tenant_id=tenant_id,
        )

        # Apply filters if provided
        if "filters" in params:
            filters = params["filters"]
            results = filter_by_attributes(
                results=results,
                material=filters.get("material"),
                weight_min=filters.get("weight_min"),
                weight_max=filters.get("weight_max"),
            )

        return {
            "search_type": self.SEARCH_TYPE_3D,
            "results": results,
            "count": len(results),
            "status": "success" if results else "no_results",
            "item_code": item_code,
            "file_type": file_type,
        }

    def _search_2d(
        self,
        image_base64: str,
        params: Dict[str, Any],
        tenant_id: Optional[str],
    ) -> Dict[str, Any]:
        """Execute 2D image search.

        Args:
            image_base64: Base64-encoded image data
            params: Additional parameters (file_type, top_k)
            tenant_id: Optional tenant ID

        Returns:
            Search results dictionary
        """
        file_type = params.get("file_type", "png")
        top_k = params.get("top_k", 10)

        results = search_2d_image(
            image_base64=image_base64,
            file_type=file_type,
            top_k=top_k,
            tenant_id=tenant_id,
        )

        return {
            "search_type": self.SEARCH_TYPE_2D,
            "results": results,
            "count": len(results),
            "status": "success" if results else "no_results",
            "file_type": file_type,
        }

    def _search_text(
        self,
        query: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute text-based search (placeholder for future implementation).

        Args:
            query: Text search query
            params: Additional parameters

        Returns:
            Search results dictionary (placeholder)
        """
        # Text search would be implemented here in the future
        # For now, return empty results
        return {
            "search_type": self.SEARCH_TYPE_TEXT,
            "results": [],
            "count": 0,
            "status": "not_implemented",
            "message": "Text search not yet implemented",
            "query": query,
        }

    def get_details(
        self,
        item_code: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get detailed information about a specific model.

        Args:
            item_code: Item code to retrieve details for
            tenant_id: Optional tenant ID

        Returns:
            Model details dictionary

        Raises:
            ValueError: If item_code is empty
            httpx.HTTPError: If the API request fails
        """
        try:
            details = get_model_details(item_code=item_code, tenant_id=tenant_id)
            return {
                "status": "success",
                "details": details,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "item_code": item_code,
            }


__all__ = ["SearchAgent"]

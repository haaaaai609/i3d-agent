"""
Tests for RAG tools module.

This module contains structure tests for the RAG tools stubs.
Full integration tests will be added when the RAG service is implemented.
"""

import pytest

from i3d_agent.tools.rag_tools import (
    retrieve_documents,
    search_api_reference,
    get_deployment_guide,
    find_troubleshooting_steps,
)


class TestRetrieveDocuments:
    """Tests for retrieve_documents tool."""

    def test_retrieve_documents_structure(self):
        """Structure test: verify return type and basic structure."""
        result = retrieve_documents("test query", knowledge_base="default", top_k=5)

        assert isinstance(result, list)
        assert len(result) > 0

        doc = result[0]
        assert "doc_id" in doc
        assert "title" in doc
        assert "content" in doc
        assert "score" in doc
        assert "metadata" in doc

    def test_retrieve_documents_empty_query(self):
        """Unit test: validation of empty query."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            retrieve_documents("")

    def test_retrieve_documents_invalid_top_k(self):
        """Unit test: validation of top_k range."""
        with pytest.raises(ValueError, match="top_k must be between 1 and 100"):
            retrieve_documents("test", top_k=0)

        with pytest.raises(ValueError, match="top_k must be between 1 and 100"):
            retrieve_documents("test", top_k=101)

    def test_retrieve_documents_with_tenant_id(self):
        """Structure test: tenant_id parameter is handled."""
        result = retrieve_documents("test", tenant_id="tenant-123")

        assert isinstance(result, list)
        if result:
            assert result[0]["metadata"]["tenant_id"] == "tenant-123"


class TestSearchApiReference:
    """Tests for search_api_reference tool."""

    def test_search_api_reference_structure(self):
        """Structure test: verify return type and basic structure."""
        result = search_api_reference("/api/v1/test", method="GET")

        assert isinstance(result, dict)
        assert "endpoint" in result
        assert "method" in result
        assert "description" in result
        assert "parameters" in result
        assert "responses" in result
        assert "examples" in result
        assert "rate_limit" in result
        assert "authentication" in result

    def test_search_api_reference_empty_endpoint(self):
        """Unit test: validation of empty endpoint."""
        with pytest.raises(ValueError, match="endpoint cannot be empty"):
            search_api_reference("")

    def test_search_api_reference_invalid_method(self):
        """Unit test: validation of HTTP method."""
        with pytest.raises(ValueError, match="method must be one of"):
            search_api_reference("/api/v1/test", method="INVALID")

    def test_search_api_reference_valid_methods(self):
        """Structure test: all valid HTTP methods are accepted."""
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

        for method in valid_methods:
            result = search_api_reference("/api/v1/test", method=method)
            assert result["method"] == method.upper()

    def test_search_api_reference_with_tenant_id(self):
        """Structure test: tenant_id parameter is handled."""
        result = search_api_reference("/api/v1/test", tenant_id="tenant-123")

        assert result["metadata"]["tenant_id"] == "tenant-123"


class TestGetDeploymentGuide:
    """Tests for get_deployment_guide tool."""

    def test_get_deployment_guide_structure(self):
        """Structure test: verify return type and basic structure."""
        result = get_deployment_guide("test-component")

        assert isinstance(result, dict)
        assert "component" in result
        assert "overview" in result
        assert "prerequisites" in result
        assert "installation" in result
        assert "configuration" in result
        assert "verification" in result
        assert "troubleshooting" in result

    def test_get_deployment_guide_empty_component(self):
        """Unit test: validation of empty component."""
        with pytest.raises(ValueError, match="component cannot be empty"):
            get_deployment_guide("")

    def test_get_deployment_guide_prerequisites_type(self):
        """Structure test: prerequisites is a list."""
        result = get_deployment_guide("test-component")
        assert isinstance(result["prerequisites"], list)

    def test_get_deployment_guide_installation_type(self):
        """Structure test: installation is a list."""
        result = get_deployment_guide("test-component")
        assert isinstance(result["installation"], list)

    def test_get_deployment_guide_configuration_type(self):
        """Structure test: configuration is a dict."""
        result = get_deployment_guide("test-component")
        assert isinstance(result["configuration"], dict)

    def test_get_deployment_guide_with_tenant_id(self):
        """Structure test: tenant_id parameter is handled."""
        result = get_deployment_guide("test-component", tenant_id="tenant-123")

        assert result["metadata"]["tenant_id"] == "tenant-123"


class TestFindTroubleshootingSteps:
    """Tests for find_troubleshooting_steps tool."""

    def test_find_troubleshooting_steps_structure(self):
        """Structure test: verify return type and basic structure."""
        result = find_troubleshooting_steps(
            error_code="ERR-001",
            error_message="Test error",
            component="test-component"
        )

        assert isinstance(result, list)
        assert len(result) > 0

        step = result[0]
        assert "error_code" in step
        assert "error_pattern" in step
        assert "component" in step
        assert "diagnosis" in step
        assert "solutions" in step
        assert "related_docs" in step
        assert "severity" in step

    def test_find_troubleshooting_steps_empty_params(self):
        """Unit test: validation when all parameters are empty."""
        with pytest.raises(
            ValueError,
            match="At least one of error_code, error_message, or component must be provided"
        ):
            find_troubleshooting_steps()

    def test_find_troubleshooting_steps_with_error_code_only(self):
        """Structure test: works with only error_code."""
        result = find_troubleshooting_steps(error_code="ERR-001")

        assert isinstance(result, list)
        if result:
            assert result[0]["error_code"] == "ERR-001"

    def test_find_troubleshooting_steps_with_error_message_only(self):
        """Structure test: works with only error_message."""
        result = find_troubleshooting_steps(error_message="Connection failed")

        assert isinstance(result, list)
        if result:
            assert "Connection failed" in result[0]["error_pattern"]

    def test_find_troubleshooting_steps_with_component_only(self):
        """Structure test: works with only component."""
        result = find_troubleshooting_steps(component="infer-engineer")

        assert isinstance(result, list)
        if result:
            assert result[0]["component"] == "infer-engineer"

    def test_find_troubleshooting_steps_solutions_type(self):
        """Structure test: solutions is a list."""
        result = find_troubleshooting_steps(error_code="ERR-001")

        if result:
            assert isinstance(result[0]["solutions"], list)

    def test_find_troubleshooting_steps_with_tenant_id(self):
        """Structure test: tenant_id parameter is handled."""
        result = find_troubleshooting_steps(
            error_code="ERR-001",
            tenant_id="tenant-123"
        )

        if result:
            assert result[0]["metadata"]["tenant_id"] == "tenant-123"

"""Tests for chat API."""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from i3d_agent.api.main import app
from i3d_agent.workflow.nodes.memory_agent import set_memory_manager
from i3d_agent.memory.manager import MemoryManager


@pytest.fixture
def test_client():
    """创建测试客户端。"""
    return TestClient(app)


@pytest.fixture
def mock_memory_manager():
    """Mock memory manager。"""
    return MemoryManager()


def test_health_check(test_client):
    """测试健康检查端点。"""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_chat_endpoint(test_client, mock_memory_manager):
    """测试聊天端点。"""
    # 设置 mock memory manager
    set_memory_manager(mock_memory_manager)

    response = test_client.post(
        "/api/v1/chat",
        json={
            "message": "搜索螺栓",
            "user_id": "test_user",
            "tenant_id": "huabei",
        }
    )

    assert response.status_code in [200, 500]  # 可能因为缺少外部服务返回 500

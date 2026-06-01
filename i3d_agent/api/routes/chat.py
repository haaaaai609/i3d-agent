"""Chat API routes for I3D Agent System."""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import ValidationError

from i3d_agent.models.chat import ChatRequest, ChatResponse
from i3d_agent.workflow.graph import I3DWorkflow
from i3d_agent.workflow.nodes.memory_agent import get_memory_manager
from i3d_agent.utils.logger import get_logger, bind_context

logger = get_logger(__name__)
router = APIRouter()

# 全局 workflow 实例
_workflow: Optional[I3DWorkflow] = None


def get_workflow() -> I3DWorkflow:
    """获取 workflow 实例（依赖注入）。"""
    global _workflow
    if _workflow is None:
        memory_manager = get_memory_manager()
        _workflow = I3DWorkflow(memory_manager)
    return _workflow


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    聊天端点 - 处理用户查询并返回 AI 响应。

    Args:
        request: 聊天请求

    Returns:
        ChatResponse: AI 响应

    Raises:
        HTTPException: 请求验证失败或处理错误时
    """
    # 绑定上下文
    bind_context(
        logger,
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        session_id=request.session_id,
    )

    try:
        logger.info(f"Received chat request from user {request.user_id}")

        workflow = get_workflow()

        # 生成 session_id（如果未提供）
        session_id = request.session_id or str(uuid.uuid4())

        # 执行工作流
        response = await workflow.run(
            query=request.message,
            user_id=request.user_id,
            tenant_id=request.tenant_id,
            session_id=session_id,
            stream=request.stream,
        )

        logger.info(f"Chat request completed for user {request.user_id}")
        return response

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=ChatResponse)
async def get_session(session_id: str, user_id: str, tenant_id: str = "huabei") -> ChatResponse:
    """
    获取会话历史（预留端点）。

    Args:
        session_id: 会话 ID
        user_id: 用户 ID
        tenant_id: 租户 ID

    Returns:
        ChatResponse: 会话历史
    """
    # TODO: 实现会话历史获取
    return ChatResponse(
        response="会话历史功能待实现",
        session_id=session_id,
    )

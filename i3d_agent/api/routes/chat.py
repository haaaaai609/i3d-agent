"""Chat API routes for I3D Agent System."""

import uuid
import json
import time
from typing import Optional, AsyncIterator

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from i3d_agent.models.chat import ChatRequest, ChatResponse
from i3d_agent.workflow.graph import I3DWorkflow
from i3d_agent.workflow.nodes.memory_agent import get_memory_manager
from i3d_agent.llm.client import get_llm_client, Message
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


async def workflow_stream_with_memory(
    query: str,
    user_id: str,
    tenant_id: str,
    session_id: str,
) -> AsyncIterator[str]:
    """生成流式响应 - 使用工作流流式输出。

    Args:
        query: 用户查询
        user_id: 用户 ID
        tenant_id: 租户 ID
        session_id: 会话 ID

    Yields:
        Server-Sent Events 格式的数据块
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    try:
        workflow = get_workflow()

        # [LOG] 请求开始
        logger.info(f"[{request_id}] 📥 Request received | session={session_id} | query_preview={query[:50]}...")

        # 使用工作流的流式方法
        async for event in workflow.run_stream(
            query=query,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            request_id=request_id,
        ):
            # 转换为 SSE 格式
            data = json.dumps(event)
            yield f"data: {data}\n\n"

        # [LOG] 请求完成
        total_duration = time.time() - start_time
        logger.info(f"[{request_id}] ✅ Stream request completed | total_duration={total_duration:.2f}s")

    except Exception as e:
        logger.error(f"[{request_id}] ❌ Error in workflow stream: {e}", exc_info=True)
        error_data = json.dumps({
            "type": "error",
            "error": str(e),
            "done": True,
            "session_id": session_id,
        })
        yield f"data: {error_data}\n\n"


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

    # 生成请求 ID
    request_id = str(uuid.uuid4())[:8]

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
            request_id=request_id,
        )

        logger.info(f"Chat request completed for user {request.user_id}")
        return response

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天端点 - 实时返回 AI 响应。

    使用 Server-Sent Events (SSE) 格式返回流式响应。
    通过 workflow checkpoint 加载历史，支持会话记忆。

    Args:
        request: 聊天请求

    Returns:
        StreamingResponse: SSE 格式的流式响应
    """
    # 绑定上下文
    bind_context(
        logger,
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        session_id=request.session_id,
    )

    try:
        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"📨 Stream chat request | user={request.user_id} | tenant={request.tenant_id} | session={session_id} | query_preview={request.message[:50]}...")

        # 生成 session_id（如果未提供）
        # session_id = request.session_id or str(uuid.uuid4())  # 已经在上面生成

        return StreamingResponse(
            workflow_stream_with_memory(
                query=request.message,
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                session_id=session_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.error(f"Error processing stream chat request: {e}")
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

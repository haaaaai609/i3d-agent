"""Chat API routes for I3D Agent System."""

import uuid
import json
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
    """生成流式响应 - 使用 checkpoint 加载历史，然后流式输出。

    Args:
        query: 用户查询
        user_id: 用户 ID
        tenant_id: 租户 ID
        session_id: 会话 ID

    Yields:
        Server-Sent Events 格式的数据块
    """
    try:
        workflow = get_workflow()
        config = {"configurable": {"thread_id": session_id}}

        # 从 checkpoint 获取历史对话
        checkpoint = workflow.graph.get_state(config)
        conversation_history = []

        # 正确访问 checkpoint 的 values
        if checkpoint and hasattr(checkpoint, 'values') and checkpoint.values:
            state_values = checkpoint.values
            conversation_history = state_values.get("conversation_history", [])
            logger.info(f"Checkpoint values keys: {list(state_values.keys()) if isinstance(state_values, dict) else 'N/A'}")
            logger.info(f"Loaded conversation_history: {conversation_history}")

        # 如果还是没有历史，尝试 metadata
        if not conversation_history and checkpoint and hasattr(checkpoint, 'metadata'):
            metadata = checkpoint.metadata or {}
            conversation_history = metadata.get("messages", [])
            logger.info(f"Loaded from metadata.messages: {conversation_history}")

        logger.info(f"Total loaded {len(conversation_history)} messages from history for session {session_id}")

        # 准备消息列表
        messages = []
        for msg in conversation_history:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                messages.append(Message(role=role, content=content))
            elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                messages.append(Message(role=msg.role, content=msg.content))

        # 添加当前用户消息
        messages.append(Message(role="user", content=query))

        # LLM 流式生成
        llm_client = get_llm_client()
        system_prompt = """你是 I3D Agent System 的智能助手，专门帮助用户处理 3D CAD 模型搜索、技术文档查询和任务处理等相关问题。

你的职责：
1. 友好地回应用户的问候和一般性问题
2. 记住对话历史，保持上下文连贯
3. 解释 I3D 系统的功能和使用方法
4. 使用简洁、专业的中文回答

记住之前的对话内容，保持对话的连续性。"""

        full_response = ""
        async for chunk in llm_client.generate_stream(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.8,
        ):
            full_response += chunk
            data = json.dumps({
                "type": "content",
                "content": chunk,
                "done": False,
                "session_id": session_id,
            })
            yield f"data: {data}\n\n"

        # 保存对话到 checkpoint - 使用 as_named_updates 来正确更新状态
        try:
            # 准备新的对话历史
            new_history = conversation_history + [
                {"role": "user", "content": query},
                {"role": "assistant", "content": full_response}
            ]

            # 使用 update_state 更新，确保覆盖整个 state
            workflow.graph.update_state(
                config,
                {
                    "conversation_history": new_history,
                    "query": query,
                    "response": full_response,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "session_id": session_id,
                }
            )
            logger.info(f"Saved {len(new_history)} messages to checkpoint for session {session_id}")
        except Exception as save_error:
            logger.warning(f"Failed to save checkpoint: {save_error}", exc_info=True)

        # 发送完成信号
        final_data = json.dumps({
            "type": "done",
            "done": True,
            "session_id": session_id,
            "sources": None,
            "thought_process": None,
        })
        yield f"data: {final_data}\n\n"

    except Exception as e:
        logger.error(f"Error in workflow stream: {e}", exc_info=True)
        error_data = json.dumps({
            "type": "error",
            "error": str(e),
            "done": True,
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
        logger.info(f"Received stream chat request from user {request.user_id}")

        # 生成 session_id（如果未提供）
        session_id = request.session_id or str(uuid.uuid4())

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

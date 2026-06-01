"""Workflow state models for I3D Agent System."""

from typing import Dict, Any, Optional, List, TypedDict, Literal

from pydantic import BaseModel, Field


class SubTask(BaseModel):
    """子任务模型。"""
    task_id: str = Field(..., description="任务唯一标识符")
    task_type: Literal["search", "rag", "process", "memory"] = Field(
        ..., description="任务类型"
    )
    agent: str = Field(..., description="负责执行此任务的 Agent 名称")
    status: Literal["pending", "running", "completed", "failed", "needs_clarification"] = Field(
        default="pending", description="任务状态"
    )
    input_data: Dict[str, Any] = Field(default_factory=dict, description="任务输入数据")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="任务输出数据")
    error_message: Optional[str] = Field(default=None, description="错误消息")
    dependencies: List[str] = Field(default_factory=list, description="依赖的其他任务 ID")
    retry_count: int = Field(default=0, description="重试次数")


class ClarificationRequest(BaseModel):
    """澄清请求模型。"""
    task_id: str = Field(..., description="需要澄清的任务 ID")
    question: str = Field(..., description="向用户提出的问题")
    options: Optional[List[str]] = Field(default=None, description="可选的答案选项")
    context: Optional[Dict[str, Any]] = Field(default=None, description="额外的上下文信息")


class ErrorInfo(BaseModel):
    """错误信息模型。"""
    task_id: str = Field(..., description="失败的任务 ID")
    error_type: Literal["retriable", "degradable", "user_help_needed", "critical"] = Field(
        ..., description="错误类型分类"
    )
    message: str = Field(..., description="错误消息描述")
    original_error: Optional[str] = Field(default=None, description="原始错误信息")


class WorkflowState(TypedDict):
    """工作流状态类型定义。"""
    query: str
    user_id: str
    tenant_id: str
    session_id: str
    stream: bool
    messages: List[Any]
    conversation_history: List[Dict[str, Any]]
    sub_tasks: List[SubTask]
    current_task_index: int
    pending_clarification: Optional[ClarificationRequest]
    clarification_answer: Optional[str]
    error: Optional[ErrorInfo]
    response: Optional[str]
    sources: Optional[List[Any]]
    thought_process: Optional[str]
    metadata: Optional[Dict[str, Any]]
    next_action: Optional[str]
    should_continue: bool

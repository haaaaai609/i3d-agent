# LangGraph 工作流实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 I3D Agent System 的 LangGraph 工作流，支持任务分解、迭代细化、并行执行和智能错误恢复。

**Architecture:** 使用 LangGraph StateGraph 构建状态机工作流，包含 supervisor、memory_agent、search_agent、rag_agent、process_agent、aggregator、error_handler 等节点，通过条件边实现动态路由。

**Tech Stack:** LangGraph (StateGraph), LangChain, Pydantic, Redis (内存), PostgreSQL (可选)

---

## 文件结构

```
i3d_agent/workflow/
├── __init__.py              # 导出 I3DWorkflow, WorkflowState 等
├── state.py                 # 状态模型定义 (SubTask, ClarificationRequest, ErrorInfo, WorkflowState)
├── nodes/
│   ├── __init__.py
│   ├── supervisor.py       # supervisor 节点
│   ├── memory_agent.py     # memory_agent 节点
│   ├── search_agent.py     # search_agent 节点包装
│   ├── rag_agent.py        # rag_agent 节点包装
│   ├── process_agent.py    # process_agent 节点包装
│   ├── aggregator.py       # aggregator 节点
│   └── error_handler.py    # error_handler 节点
├── conditions/
│   ├── __init__.py
│   └── routing.py          # 条件路由函数
├── graph.py                # I3DWorkflow 类，构建工作流图
└── utils.py                # 工具函数

tests/test_workflow/
├── __init__.py
├── test_state.py           # 状态模型测试
├── test_nodes.py           # 节点测试
├── test_conditions.py      # 路由条件测试
├── test_graph.py           # 工作流图测试
└── test_integration.py     # 集成测试

i3d_agent/agents/
└── base.py                 # 添加 AgentError, NeedsClarificationError (修改)
```

---

## Task 1: 添加 Agent 异常类

**Files:**
- Modify: `i3d_agent/agents/base.py`
- Test: `tests/test_agents/test_base.py`

- [ ] **Step 1: 在测试文件中添加异常测试**

```python
# tests/test_agents/test_base.py

def test_agent_error():
    """测试 AgentError 基础异常"""
    from i3d_agent.agents.base import AgentError

    with pytest.raises(AgentError) as exc_info:
        raise AgentError("Test error")
    assert str(exc_info.value) == "Test error"


def test_needs_clarification_error():
    """测试 NeedsClarificationError 异常"""
    from i3d_agent.agents.base import NeedsClarificationError

    error = NeedsClarificationError(
        question="请指定搜索类型",
        options=["3d", "2d", "text"]
    )

    assert error.question == "请指定搜索类型"
    assert error.options == ["3d", "2d", "text"]
    assert "请指定搜索类型" in str(error)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /data/yzh/i3d-agent-system
pytest tests/test_agents/test_base.py::test_agent_error -v
pytest tests/test_agents/test_base.py::test_needs_clarification_error -v
```
Expected: FAIL - "AgentError not defined"

- [ ] **Step 3: 在 base.py 中实现异常类**

```python
# i3d_agent/agents/base.py

# 在文件末尾添加

class AgentError(Exception):
    """Agent 基础异常类"""

    pass


class NeedsClarificationError(AgentError):
    """Agent 需要用户澄清时抛出的异常"""

    def __init__(self, question: str, options: Optional[List[str]] = None):
        """
        初始化澄清请求异常。

        Args:
            question: 向用户提出的问题
            options: 可选的答案选项列表
        """
        self.question = question
        self.options = options
        super().__init__(question)

    def __str__(self) -> str:
        """返回异常的字符串表示"""
        if self.options:
            options_str = ", ".join(self.options)
            return f"{self.question} (选项: {options_str})"
        return self.question
```

同时确保导入 Optional, List：
```python
# 在文件顶部确保有这些导入
from typing import Dict, Any, Optional, List
```

- [ ] **Step 4: 更新 __init__.py 导出异常**

```python
# i3d_agent/agents/__init__.py

from i3d_agent.agents.base import (
    AgentConfig,
    BaseAgent,
    AgentError,
    NeedsClarificationError,
)

__all__ = [
    "AgentConfig",
    "BaseAgent",
    "ProcessAgent",
    "RAGAgent",
    "SearchAgent",
    "SupervisorAgent",
    "AgentError",
    "NeedsClarificationError",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_agents/test_base.py::test_agent_error -v
pytest tests/test_agents/test_base.py::test_needs_clarification_error -v
```
Expected: PASS

- [ ] **Step 6: 运行所有现有测试确保无破坏**

```bash
pytest tests/test_agents/ -v
```
Expected: All PASS

- [ ] **Step 7: 提交**

```bash
git add i3d_agent/agents/base.py i3d_agent/agents/__init__.py tests/test_agents/test_base.py
git commit -m "feat: add AgentError and NeedsClarificationError exceptions"
```

---

## Task 2: 创建状态模型

**Files:**
- Create: `i3d_agent/workflow/state.py`
- Test: `tests/test_workflow/test_state.py`

- [ ] **Step 1: 创建 workflow 目录结构**

```bash
cd /data/yzh/i3d-agent-system
mkdir -p i3d_agent/workflow/nodes
mkdir -p i3d_agent/workflow/conditions
mkdir -p tests/test_workflow
touch i3d_agent/workflow/__init__.py
touch i3d_agent/workflow/nodes/__init__.py
touch i3d_agent/workflow/conditions/__init__.py
touch tests/test_workflow/__init__.py
```

- [ ] **Step 2: 先写测试文件**

```python
# tests/test_workflow/test_state.py

import pytest
from datetime import datetime
from pydantic import ValidationError

from i3d_agent.workflow.state import (
    SubTask,
    ClarificationRequest,
    ErrorInfo,
    WorkflowState,
)


class TestSubTask:
    """测试 SubTask 模型"""

    def test_create_subtask(self):
        """测试创建子任务"""
        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="pending",
            input_data={"query": "螺栓"},
        )

        assert task.task_id == "task_1"
        assert task.task_type == "search"
        assert task.status == "pending"
        assert task.output_data is None
        assert task.retry_count == 0

    def test_subtask_with_dependencies(self):
        """测试带依赖关系的子任务"""
        task = SubTask(
            task_id="task_2",
            task_type="rag",
            agent="rag_agent",
            status="pending",
            input_data={"question": "如何使用"},
            dependencies=["task_1"],
        )

        assert task.dependencies == ["task_1"]

    def test_subtask_status_validation(self):
        """测试子任务状态验证"""
        with pytest.raises(ValidationError):
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="invalid_status",  # 无效状态
                input_data={},
            )


class TestClarificationRequest:
    """测试 ClarificationRequest 模型"""

    def test_create_clarification_request(self):
        """测试创建澄清请求"""
        request = ClarificationRequest(
            task_id="task_1",
            question="请指定搜索类型",
            options=["3d", "2d", "text"],
        )

        assert request.task_id == "task_1"
        assert request.question == "请指定搜索类型"
        assert request.options == ["3d", "2d", "text"]

    def test_clarification_request_without_options(self):
        """测试不带选项的澄清请求"""
        request = ClarificationRequest(
            task_id="task_1",
            question="请提供更多细节",
        )

        assert request.options is None


class TestErrorInfo:
    """测试 ErrorInfo 模型"""

    def test_create_error_info(self):
        """测试创建错误信息"""
        error = ErrorInfo(
            task_id="task_1",
            error_type="retriable",
            message="网络超时",
            original_error="TimeoutError",
        )

        assert error.task_id == "task_1"
        assert error.error_type == "retriable"
        assert error.message == "网络超时"

    def test_error_type_validation(self):
        """测试错误类型验证"""
        with pytest.raises(ValidationError):
            ErrorInfo(
                task_id="task_1",
                error_type="invalid_type",  # 无效类型
                message="错误",
            )


class TestWorkflowState:
    """测试 WorkflowState"""

    def test_create_workflow_state(self):
        """测试创建工作流状态"""
        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        assert state["query"] == "搜索螺栓"
        assert state["should_continue"] is True

    def test_workflow_state_with_subtasks(self):
        """测试带子任务的工作流状态"""
        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="pending",
            input_data={"query": "螺栓"},
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        assert len(state["sub_tasks"]) == 1
        assert state["sub_tasks"][0].task_type == "search"
```

- [ ] **Step 3: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_state.py -v
```
Expected: FAIL - "module not found: i3d_agent.workflow.state"

- [ ] **Step 4: 实现状态模型**

```python
# i3d_agent/workflow/state.py

"""
Workflow state models for I3D Agent System.

This module defines the state models used in the LangGraph workflow,
including sub-tasks, clarification requests, error info, and the main
workflow state.
"""

from typing import Dict, Any, Optional, List, TypedDict, Literal

from pydantic import BaseModel, Field


class SubTask(BaseModel):
    """子任务模型。

    表示工作流中的一个原子任务，可以由特定的 Agent 执行。
    """

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

    class Config:
        """Pydantic 配置"""

        json_schema_extra = {
            "examples": [
                {
                    "task_id": "task_1",
                    "task_type": "search",
                    "agent": "search_agent",
                    "status": "pending",
                    "input_data": {"query": "螺栓"},
                }
            ]
        }


class ClarificationRequest(BaseModel):
    """澄清请求模型。

    当 Agent 需要用户提供更多信息时创建此请求。
    """

    task_id: str = Field(..., description="需要澄清的任务 ID")
    question: str = Field(..., description="向用户提出的问题")
    options: Optional[List[str]] = Field(default=None, description="可选的答案选项")
    context: Optional[Dict[str, Any]] = Field(default=None, description="额外的上下文信息")

    class Config:
        """Pydantic 配置"""

        json_schema_extra = {
            "examples": [
                {
                    "task_id": "task_1",
                    "question": "请指定搜索类型",
                    "options": ["3d", "2d", "text"],
                }
            ]
        }


class ErrorInfo(BaseModel):
    """错误信息模型。

    包含任务执行失败的详细信息，用于错误处理器决策。
    """

    task_id: str = Field(..., description="失败的任务 ID")
    error_type: Literal["retriable", "degradable", "user_help_needed", "critical"] = Field(
        ..., description="错误类型分类"
    )
    message: str = Field(..., description="错误消息描述")
    original_error: Optional[str] = Field(default=None, description="原始错误信息")

    class Config:
        """Pydantic 配置"""

        json_schema_extra = {
            "examples": [
                {
                    "task_id": "task_1",
                    "error_type": "retriable",
                    "message": "网络超时",
                    "original_error": "TimeoutError",
                }
            ]
        }


class WorkflowState(TypedDict):
    """工作流状态类型定义。

    这是 LangGraph 工作流的主要状态结构，在整个执行过程中
    节点之间通过此状态传递信息。
    """

    # === 输入字段 ===
    query: str
    """用户查询字符串"""

    user_id: str
    """用户标识符"""

    tenant_id: str
    """租户标识符"""

    session_id: str
    """会话标识符，用于维护多轮对话"""

    stream: bool
    """是否流式返回响应"""

    # === 对话历史 ===
    messages: List[Any]
    """当前会话的消息列表"""

    conversation_history: List[Dict[str, Any]]
    """从记忆加载的对话历史"""

    # === 任务管理 ===
    sub_tasks: List[SubTask]
    """子任务列表"""

    current_task_index: int
    """当前执行的任务索引"""

    # === 澄清与错误 ===
    pending_clarification: Optional[ClarificationRequest]
    """待处理的澄清请求"""

    clarification_answer: Optional[str]
    """用户对澄清问题的回答"""

    error: Optional[ErrorInfo]
    """待处理的错误信息"""

    # === 输出字段 ===
    response: Optional[str]
    """最终响应文本"""

    sources: Optional[List[Any]]
    """来源文档列表"""

    thought_process: Optional[str]
    """思考过程说明"""

    metadata: Optional[Dict[str, Any]]
    """额外的元数据信息"""

    # === 流程控制 ===
    next_action: Optional[str]
    """下一步要执行的动作名称"""

    should_continue: bool
    """是否继续执行工作流"""
```

- [ ] **Step 5: 更新 workflow __init__.py**

```python
# i3d_agent/workflow/__init__.py

"""Workflow module for I3D Agent System."""

from i3d_agent.workflow.state import (
    SubTask,
    ClarificationRequest,
    ErrorInfo,
    WorkflowState,
)

__all__ = [
    "SubTask",
    "ClarificationRequest",
    "ErrorInfo",
    "WorkflowState",
]
```

- [ ] **Step 6: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_state.py -v
```
Expected: All PASS

- [ ] **Step 7: 提交**

```bash
git add i3d_agent/workflow/ tests/test_workflow/
git commit -m "feat: add workflow state models (SubTask, ClarificationRequest, ErrorInfo, WorkflowState)"
```

---

## Task 3: 实现工具函数

**Files:**
- Create: `i3d_agent/workflow/utils.py`
- Test: `tests/test_workflow/test_utils.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_workflow/test_utils.py

import pytest

from i3d_agent.workflow.state import SubTask, ErrorInfo
from i3d_agent.workflow.utils import (
    is_simple_query,
    get_task_by_id,
    get_next_pending_task,
    get_failed_task,
    is_retriable_error,
    is_degradable_error,
)


class TestQueryComplexity:
    """测试查询复杂度判断"""

    def test_simple_search_query(self):
        """测试简单搜索查询"""
        assert is_simple_query("搜索螺栓") is True
        assert is_simple_query("查找螺丝") is True
        assert is_simple_query("推荐零件") is True

    def test_simple_rag_query(self):
        """测试简单 RAG 查询"""
        assert is_simple_query("文档怎么用") is True
        assert is_simple_query("api 使用方法") is True

    def test_simple_process_query(self):
        """测试简单处理状态查询"""
        assert is_simple_query("处理状态") is True
        assert is_simple_query("任务进度") is True

    def test_complex_multi_intent_query(self):
        """测试多意图复杂查询"""
        assert is_simple_query("搜索螺栓并查看文档") is False
        assert is_simple_query("找零件然后看怎么处理") is False

    def test_complex_vague_query(self):
        """测试模糊复杂查询"""
        assert is_simple_query("我需要一些东西") is False
        assert is_simple_query("帮我看看") is False


class TestTaskHelpers:
    """测试任务辅助函数"""

    def test_get_task_by_id(self):
        """测试通过 ID 获取任务"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="pending",
                input_data={},
            ),
            SubTask(
                task_id="task_2",
                task_type="rag",
                agent="rag_agent",
                status="completed",
                input_data={},
            ),
        ]

        task = get_task_by_id(tasks, "task_1")
        assert task is not None
        assert task.task_id == "task_1"

    def test_get_task_by_id_not_found(self):
        """测试获取不存在的任务"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="pending",
                input_data={},
            )
        ]

        task = get_task_by_id(tasks, "task_999")
        assert task is None

    def test_get_next_pending_task(self):
        """测试获取下一个待处理任务"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="completed",
                input_data={},
            ),
            SubTask(
                task_id="task_2",
                task_type="rag",
                agent="rag_agent",
                status="pending",
                input_data={},
            ),
        ]

        task = get_next_pending_task(tasks)
        assert task is not None
        assert task.task_id == "task_2"

    def test_get_next_pending_task_none(self):
        """测试没有待处理任务时返回 None"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="completed",
                input_data={},
            )
        ]

        task = get_next_pending_task(tasks)
        assert task is None

    def test_get_failed_task(self):
        """测试获取失败任务"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="completed",
                input_data={},
            ),
            SubTask(
                task_id="task_2",
                task_type="rag",
                agent="rag_agent",
                status="failed",
                input_data={},
                error_message="网络错误",
            ),
        ]

        task = get_failed_task(tasks)
        assert task is not None
        assert task.task_id == "task_2"
        assert task.error_message == "网络错误"

    def test_get_failed_task_none(self):
        """测试没有失败任务时返回 None"""
        tasks = [
            SubTask(
                task_id="task_1",
                task_type="search",
                agent="search_agent",
                status="completed",
                input_data={},
            )
        ]

        task = get_failed_task(tasks)
        assert task is None


class TestErrorClassification:
    """测试错误分类"""

    def test_is_retriable_error(self):
        """测试可重试错误判断"""
        error_timeout = ErrorInfo(
            task_id="task_1", error_type="retriable", message="超时"
        )
        assert is_retriable_error(error_timeout) is True

        error_critical = ErrorInfo(
            task_id="task_1", error_type="critical", message="严重错误"
        )
        assert is_retriable_error(error_critical) is False

    def test_is_degradable_error(self):
        """测试可降级错误判断"""
        error_degradable = ErrorInfo(
            task_id="task_1", error_type="degradable", message="服务降级"
        )
        assert is_degradable_error(error_degradable) is True

        error_critical = ErrorInfo(
            task_id="task_1", error_type="critical", message="严重错误"
        )
        assert is_degradable_error(error_critical) is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_utils.py -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现工具函数**

```python
# i3d_agent/workflow/utils.py

"""
Utility functions for the I3D Agent workflow.

This module provides helper functions for query analysis, task management,
and error classification.
"""

from typing import Dict, List, Optional, Any

from i3d_agent.agents.supervisor import SupervisorAgent
from i3d_agent.workflow.state import SubTask, ErrorInfo


# === 查询复杂度判断 ===

def is_simple_query(query: str, max_length: int = 50) -> bool:
    """判断查询是否为简单查询。

    简单查询的标准：
    1. 只包含单一意图（基于 Supervisor 的关键词匹配）
    2. 查询长度不超过 max_length
    3. 不包含"并"、"然后"、"之后"等多意图连接词

    Args:
        query: 用户查询字符串
        max_length: 最大查询长度，默认 50

    Returns:
        True 如果是简单查询，False 如果是复杂查询
    """
    if len(query) > max_length:
        return False

    # 检查多意图连接词
    multi_intent_keywords = ["并", "然后", "之后", "接着", "再", "和", "同时"]
    query_lower = query.lower()
    for keyword in multi_intent_keywords:
        if keyword in query_lower:
            return False

    # 使用 Supervisor 的关键词匹配判断意图
    supervisor = SupervisorAgent()
    intent_result = supervisor.analyze_intent(query)

    # 如果匹配到明确意图且置信度为 high，认为是简单查询
    if intent_result["confidence"] == "high" and intent_result["task_type"] != "general":
        return True

    # 模糊查询（置信度为 low 且没有关键词匹配）视为复杂查询
    if intent_result["confidence"] == "low" and not intent_result["matched_keywords"]:
        return False

    return True


# === 任务管理辅助函数 ===

def get_task_by_id(tasks: List[SubTask], task_id: str) -> Optional[SubTask]:
    """通过任务 ID 获取任务。

    Args:
        tasks: 子任务列表
        task_id: 要查找的任务 ID

    Returns:
        找到的任务，如果不存在则返回 None
    """
    for task in tasks:
        if task.task_id == task_id:
            return task
    return None


def get_next_pending_task(tasks: List[SubTask]) -> Optional[SubTask]:
    """获取下一个待处理的任务。

    返回第一个状态为 pending 或 running 的任务。

    Args:
        tasks: 子任务列表

    Returns:
        下一个待处理的任务，如果没有则返回 None
    """
    for task in tasks:
        if task.status in ["pending", "running"]:
            return task
    return None


def get_failed_task(tasks: List[SubTask]) -> Optional[SubTask]:
    """获取失败的任务。

    Args:
        tasks: 子任务列表

    Returns:
        失败的任务，如果没有则返回 None
    """
    for task in tasks:
        if task.status == "failed":
            return task
    return None


def update_task_status(
    tasks: List[SubTask],
    task_id: str,
    status: str,
    output_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> List[SubTask]:
    """更新任务状态。

    Args:
        tasks: 子任务列表
        task_id: 要更新的任务 ID
        status: 新的状态
        output_data: 可选的输出数据
        error_message: 可选的错误消息

    Returns:
        更新后的任务列表
    """
    for task in tasks:
        if task.task_id == task_id:
            task.status = status  # type: ignore
            if output_data is not None:
                task.output_data = output_data
            if error_message is not None:
                task.error_message = error_message
            break
    return tasks


# === 错误分类辅助函数 ===

def is_retriable_error(error: ErrorInfo) -> bool:
    """判断错误是否可重试。

    可重试错误通常是临时性错误，如网络超时、服务暂时不可用等。

    Args:
        error: 错误信息

    Returns:
        True 如果错误可重试
    """
    return error.error_type == "retriable"


def is_degradable_error(error: ErrorInfo) -> bool:
    """判断错误是否可降级处理。

    可降级错误意味着可以使用备用方案继续执行。

    Args:
        error: 错误信息

    Returns:
        True 如果错误可降级
    """
    return error.error_type == "degradable"


def is_critical_error(error: ErrorInfo) -> bool:
    """判断是否为严重错误。

    严重错误无法恢复，需要终止执行。

    Args:
        error: 错误信息

    Returns:
        True 如果是严重错误
    """
    return error.error_type == "critical"
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_utils.py -v
```
Expected: All PASS

- [ ] **Step 5: 更新 workflow __init__.py**

```python
# i3d_agent/workflow/__init__.py (添加)

from i3d_agent.workflow.utils import (
    is_simple_query,
    get_task_by_id,
    get_next_pending_task,
    get_failed_task,
    update_task_status,
    is_retriable_error,
    is_degradable_error,
    is_critical_error,
)

__all__ = [
    "SubTask",
    "ClarificationRequest",
    "ErrorInfo",
    "WorkflowState",
    "is_simple_query",
    "get_task_by_id",
    "get_next_pending_task",
    "get_failed_task",
    "update_task_status",
    "is_retriable_error",
    "is_degradable_error",
    "is_critical_error",
]
```

- [ ] **Step 6: 提交**

```bash
git add i3d_agent/workflow/utils.py tests/test_workflow/test_utils.py i3d_agent/workflow/__init__.py
git commit -m "feat: add workflow utility functions"
```

---

## Task 4: 实现条件路由函数

**Files:**
- Create: `i3d_agent/workflow/conditions/routing.py`
- Test: `tests/test_workflow/test_conditions.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_workflow/test_conditions.py

import pytest

from i3d_agent.workflow.state import SubTask, ErrorInfo, ClarificationRequest
from i3d_agent.workflow.conditions.routing import (
    should_route_to_memory,
    check_clarification_needed,
    check_all_tasks_completed,
    decide_next_agent,
    classify_error,
)


class TestShouldRouteToMemory:
    """测试记忆路由判断"""

    def test_no_conversation_history_routes_to_memory(self):
        """测试无对话历史时路由到 memory_agent"""
        state = {
            "conversation_history": [],
        }
        result = should_route_to_memory(state)
        assert result == "load_memory"

    def test_with_conversation_history_skips_memory(self):
        """测试有对话历史时跳过 memory_agent"""
        state = {
            "conversation_history": [{"role": "user", "content": "上次查询"}],
        }
        result = should_route_to_memory(state)
        assert result == "skip_memory"


class TestCheckClarificationNeeded:
    """测试澄清需求检查"""

    def test_no_pending_clarification_continues(self):
        """测试无待处理澄清时继续执行"""
        state = {
            "pending_clarification": None,
        }
        result = check_clarification_needed(state)
        assert result == "continue_execution"

    def test_pending_clarification_requests_user_input(self):
        """测试有待处理澄清时请求用户输入"""
        state = {
            "pending_clarification": ClarificationRequest(
                task_id="task_1",
                question="请指定搜索类型",
            ),
        }
        result = check_clarification_needed(state)
        assert result == "request_clarification"


class TestCheckAllTasksCompleted:
    """测试任务完成检查"""

    def test_all_pending_returns_continue(self):
        """测试有待处理任务时返回继续"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="pending",
                    input_data={},
                )
            ]
        }
        result = check_all_tasks_completed(state)
        assert result == "continue_tasks"

    def test_all_completed_returns_aggregate(self):
        """测试所有任务完成时返回聚合"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="completed",
                    input_data={},
                    output_data={"results": []},
                )
            ]
        }
        result = check_all_tasks_completed(state)
        assert result == "aggregate_results"

    def test_has_failed_returns_handle_error(self):
        """测试有失败任务时返回错误处理"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="failed",
                    input_data={},
                    error_message="网络错误",
                )
            ]
        }
        result = check_all_tasks_completed(state)
        assert result == "handle_error"


class TestDecideNextAgent:
    """测试下一个 Agent 决策"""

    def test_no_pending_task_returns_aggregator(self):
        """测试无待处理任务时返回 aggregator"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="completed",
                    input_data={},
                )
            ]
        }
        result = decide_next_agent(state)
        assert result == "aggregator"

    def test_pending_search_task_returns_search_agent(self):
        """测试待处理搜索任务返回 search_agent"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="search",
                    agent="search_agent",
                    status="pending",
                    input_data={"query": "螺栓"},
                )
            ]
        }
        result = decide_next_agent(state)
        assert result == "search_agent"

    def test_pending_rag_task_returns_rag_agent(self):
        """测试待处理 RAG 任务返回 rag_agent"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="rag",
                    agent="rag_agent",
                    status="pending",
                    input_data={"question": "如何使用"},
                )
            ]
        }
        result = decide_next_agent(state)
        assert result == "rag_agent"

    def test_pending_process_task_returns_process_agent(self):
        """测试待处理 Process 任务返回 process_agent"""
        state = {
            "sub_tasks": [
                SubTask(
                    task_id="task_1",
                    task_type="process",
                    agent="process_agent",
                    status="pending",
                    input_data={"task_id": "task_123"},
                )
            ]
        }
        result = decide_next_agent(state)
        assert result == "process_agent"


class TestClassifyError:
    """测试错误分类"""

    def test_retriable_error_returns_retry(self):
        """测试可重试错误返回 retry"""
        state = {
            "error": ErrorInfo(
                task_id="task_1",
                error_type="retriable",
                message="网络超时",
            )
        }
        result = classify_error(state)
        assert result == "retry"

    def test_degradable_error_returns_degrade(self):
        """测试可降级错误返回 degrade"""
        state = {
            "error": ErrorInfo(
                task_id="task_1",
                error_type="degradable",
                message="服务降级",
            )
        }
        result = classify_error(state)
        assert result == "degrade"

    def test_critical_error_returns_fail(self):
        """测试严重错误返回 fail"""
        state = {
            "error": ErrorInfo(
                task_id="task_1",
                error_type="critical",
                message="严重错误",
            )
        }
        result = classify_error(state)
        assert result == "fail"

    def test_no_error_returns_no_error(self):
        """测试无错误时返回 no_error"""
        state = {
            "error": None,
        }
        result = classify_error(state)
        assert result == "no_error"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_conditions.py -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现条件路由函数**

```python
# i3d_agent/workflow/conditions/routing.py

"""
Conditional routing functions for the I3D Agent workflow.

This module provides functions that determine the next step in the
workflow based on the current state.
"""

from typing import Dict, Any, List

from i3d_agent.workflow.state import SubTask, WorkflowState
from i3d_agent.workflow.utils import get_next_pending_task, get_failed_task


# === 记忆路由 ===

def should_route_to_memory(state: WorkflowState) -> str:
    """判断是否需要加载记忆。

    Args:
        state: 当前工作流状态

    Returns:
        "load_memory" 如果需要加载，"skip_memory" 如果跳过
    """
    if not state.get("conversation_history"):
        return "load_memory"
    return "skip_memory"


# === 澄清路由 ===

def check_clarification_needed(state: WorkflowState) -> str:
    """检查是否有 Agent 需要澄清。

    Args:
        state: 当前工作流状态

    Returns:
        "request_clarification" 如果需要澄清，"continue_execution" 如果继续
    """
    if state.get("pending_clarification"):
        return "request_clarification"
    return "continue_execution"


# === 任务完成检查 ===

def check_all_tasks_completed(state: WorkflowState) -> str:
    """检查所有任务是否完成。

    Args:
        state: 当前工作流状态

    Returns:
        "aggregate_results" 如果全部完成
        "handle_error" 如果有失败任务
        "continue_tasks" 如果有待处理任务
    """
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])

    # 检查是否有失败任务
    failed_task = get_failed_task(sub_tasks)
    if failed_task:
        return "handle_error"

    # 检查是否还有待处理任务
    pending_task = get_next_pending_task(sub_tasks)
    if pending_task:
        return "continue_tasks"

    # 所有任务完成
    return "aggregate_results"


# === Agent 路由 ===

def decide_next_agent(state: WorkflowState) -> str:
    """决定下一个执行的 Agent。

    Args:
        state: 当前工作流状态

    Returns:
        下一个 Agent 的节点名称（"search_agent", "rag_agent", "process_agent", "aggregator"）
    """
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])

    # 获取下一个待处理任务
    next_task = get_next_pending_task(sub_tasks)

    if not next_task:
        return "aggregator"

    # 根据 task_type 返回对应的 Agent 节点
    return f"{next_task.task_type}_agent"


# === 错误分类 ===

def classify_error(state: WorkflowState) -> str:
    """分类错误并决定处理方式。

    Args:
        state: 当前工作流状态

    Returns:
        "retry" 如果可重试，"degrade" 如果可降级，"fail" 如果严重错误，"no_error" 如果无错误
    """
    error = state.get("error")

    if not error:
        return "no_error"

    if error.error_type == "retriable":
        return "retry"
    elif error.error_type == "degradable":
        return "degrade"
    else:
        return "fail"


# === 任务完成检查（单任务） ===

def check_task_completion(state: WorkflowState, task_id: str) -> str:
    """检查单个任务的完成状态。

    Args:
        state: 当前工作流状态
        task_id: 要检查的任务 ID

    Returns:
        "completed" 如果任务完成，"needs_clarification" 如果需要澄清，"failed" 如果失败
    """
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])

    for task in sub_tasks:
        if task.task_id == task_id:
            if task.status == "completed":
                return "completed"
            elif task.status == "needs_clarification":
                return "needs_clarification"
            elif task.status == "failed":
                return "failed"

    return "completed"  # 默认，任务不存在时认为完成
```

- [ ] **Step 4: 更新 conditions __init__.py**

```python
# i3d_agent/workflow/conditions/__init__.py

"""Conditional routing for I3D Agent workflow."""

from i3d_agent.workflow.conditions.routing import (
    should_route_to_memory,
    check_clarification_needed,
    check_all_tasks_completed,
    decide_next_agent,
    classify_error,
    check_task_completion,
)

__all__ = [
    "should_route_to_memory",
    "check_clarification_needed",
    "check_all_tasks_completed",
    "decide_next_agent",
    "classify_error",
    "check_task_completion",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_conditions.py -v
```
Expected: All PASS

- [ ] **Step 6: 提交**

```bash
git add i3d_agent/workflow/conditions/ tests/test_workflow/test_conditions.py
git commit -m "feat: add conditional routing functions"
```

---

## Task 5: 实现 memory_agent 节点

**Files:**
- Create: `i3d_agent/workflow/nodes/memory_agent.py`
- Test: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 在测试文件中添加 memory_agent 测试**

```python
# tests/test_workflow/test_nodes.py (添加到文件开头)

import pytest
from unittest.mock import Mock, patch

from i3d_agent.workflow.state import WorkflowState
from i3d_agent.workflow.nodes.memory_agent import memory_agent_node


class TestMemoryAgentNode:
    """测试 memory_agent 节点"""

    @pytest.mark.asyncio
    async def test_memory_agent_loads_conversation_history(self):
        """测试 memory_agent 加载对话历史"""
        # Mock memory manager
        mock_manager = Mock()
        mock_manager.store.get.return_value = {
            "messages": [
                {"role": "user", "content": "搜索螺栓"},
                {"role": "assistant", "content": "找到结果"},
            ]
        }

        state: WorkflowState = {
            "query": "再来一次",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        with patch("i3d_agent.workflow.nodes.memory_agent.get_memory_manager", return_value=mock_manager):
            new_state = await memory_agent_node(state)

        assert len(new_state["conversation_history"]) == 2
        assert new_state["conversation_history"][0]["content"] == "搜索螺栓"

    @pytest.mark.asyncio
    async def test_memory_agent_saves_context(self):
        """测试 memory_agent 保存上下文"""
        mock_manager = Mock()
        mock_manager.store.get.return_value = None

        state: WorkflowState = {
            "query": "搜索螺丝",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        with patch("i3d_agent.workflow.nodes.memory_agent.get_memory_manager", return_value=mock_manager):
            new_state = await memory_agent_node(state)

        # 验证调用了 set_context
        mock_manager.set_context.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_nodes.py::TestMemoryAgentNode -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现 memory_agent 节点**

```python
# i3d_agent/workflow/nodes/memory_agent.py

"""
Memory agent node for the I3D Agent workflow.

This node handles loading conversation history and saving context
 to the memory manager.
"""

import asyncio
from typing import Dict, Any

from i3d_agent.config.settings import get_settings
from i3d_agent.memory.manager import MemoryManager
from i3d_agent.workflow.state import WorkflowState


# 全局 memory manager 实例（延迟初始化）
_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """获取或创建全局 MemoryManager 实例。

    Returns:
        MemoryManager 实例
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


async def memory_agent_node(state: WorkflowState) -> WorkflowState:
    """Memory agent 节点函数。

    此节点负责：
    1. 加载用户的对话历史
    2. 保存当前查询到工作记忆

    Args:
        state: 当前工作流状态

    Returns:
        更新后的工作流状态
    """
    memory_manager = get_memory_manager()
    user_id = state["user_id"]
    query = state["query"]
    session_id = state["session_id"]

    # 1. 加载对话历史
    context = memory_manager.get_context(user_id)
    if context:
        conversation_history = context.get("messages", [])
        state["conversation_history"] = conversation_history
    else:
        state["conversation_history"] = []

    # 2. 保存当前查询到工作记忆
    memory_manager.set_context(
        user_id,
        {
            "current_query": query,
            "session_id": session_id,
            "timestamp": None,  # 可以添加时间戳
        }
    )

    return state
```

- [ ] **Step 4: 更新 nodes __init__.py**

```python
# i3d_agent/workflow/nodes/__init__.py

"""Workflow nodes for I3D Agent System."""

from i3d_agent.workflow.nodes.memory_agent import memory_agent_node, get_memory_manager

__all__ = [
    "memory_agent_node",
    "get_memory_manager",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_nodes.py::TestMemoryAgentNode -v
```
Expected: All PASS

- [ ] **Step 6: 提交**

```bash
git add i3d_agent/workflow/nodes/memory_agent.py i3d_agent/workflow/nodes/__init__.py tests/test_workflow/test_nodes.py
git commit -m "feat: add memory_agent node"
```

---

## Task 6: 实现 supervisor 节点

**Files:**
- Create: `i3d_agent/workflow/nodes/supervisor.py`
- Modify: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 添加 supervisor 节点测试**

```python
# tests/test_workflow/test_nodes.py (添加)

import uuid
from i3d_agent.workflow.nodes.supervisor import supervisor_node


class TestSupervisorNode:
    """测试 supervisor 节点"""

    @pytest.mark.asyncio
    async def test_supervisor_simple_query_creates_single_task(self):
        """测试 supervisor 对简单查询创建单个任务"""
        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await supervisor_node(state)

        assert len(new_state["sub_tasks"]) == 1
        assert new_state["sub_tasks"][0].task_type == "search"
        assert new_state["sub_tasks"][0].status == "pending"

    @pytest.mark.asyncio
    async def test_supervisor_with_clarification_answer(self):
        """测试 supervisor 处理澄清答案"""
        from i3d_agent.workflow.state import SubTask

        # 先创建一个需要澄清的任务
        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="needs_clarification",
            input_data={"query": "搜索"},
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": "3d",  # 用户选择了 3d
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await supervisor_node(state)

        # 验证澄清答案已应用到任务
        assert new_state["clarification_answer"] is None  # 已消费
        assert new_state["sub_tasks"][0].status == "pending"  # 重置为待处理
        assert new_state["sub_tasks"][0].input_data.get("search_type") == "3d"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_nodes.py::TestSupervisorNode -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现 supervisor 节点**

```python
# i3d_agent/workflow/nodes/supervisor.py

"""
Supervisor node for the I3D Agent workflow.

This node handles intent analysis, task decomposition, and routing.
"""

import uuid
from typing import Dict, Any, List

from i3d_agent.agents.supervisor import SupervisorAgent
from i3d_agent.workflow.state import WorkflowState, SubTask
from i3d_agent.workflow.utils import is_simple_query


async def supervisor_node(state: WorkflowState) -> WorkflowState:
    """Supervisor 节点函数。

    此节点负责：
    1. 处理澄清问题的答案（如果有）
    2. 判断查询复杂度
    3. 简单查询：直接创建单个任务
    4. 复杂查询：分解为多个子任务（预留 LLM 接口）

    Args:
        state: 当前工作流状态

    Returns:
        更新后的工作流状态
    """
    query = state["query"]
    tenant_id = state["tenant_id"]
    clarification_answer = state.get("clarification_answer")
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])

    # 1. 处理澄清答案
    if clarification_answer and sub_tasks:
        # 找到需要澄清的任务并更新
        for task in sub_tasks:
            if task.status == "needs_clarification":
                task.status = "pending"  # 重置为待处理
                task.input_data["clarification"] = clarification_answer
                break

        state["clarification_answer"] = None  # 消费答案
        return state

    # 2. 如果已有任务，跳过任务创建
    if sub_tasks:
        return state

    # 3. 判断查询复杂度
    if is_simple_query(query):
        # 4a. 简单查询：使用规则匹配直接路由
        supervisor = SupervisorAgent()
        intent_result = supervisor.analyze_intent(query)

        task_type = intent_result["task_type"]
        agent_name = intent_result["agent"]

        # 创建单个任务
        task = SubTask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            agent=agent_name,
            status="pending",
            input_data={
                "query": query,
                "tenant_id": tenant_id,
            },
        )

        state["sub_tasks"] = [task]
    else:
        # 4b. 复杂查询：分解为子任务
        # TODO: 实现 LLM 驱动的任务分解
        # 目前先创建一个通用任务
        task = SubTask(
            task_id=str(uuid.uuid4()),
            task_type="search",  # 默认
            agent="search_agent",
            status="pending",
            input_data={
                "query": query,
                "tenant_id": tenant_id,
            },
        )

        state["sub_tasks"] = [task]

    return state
```

- [ ] **Step 4: 更新 nodes __init__.py**

```python
# i3d_agent/workflow/nodes/__init__.py (添加)

from i3d_agent.workflow.nodes.supervisor import supervisor_node

__all__ = [
    "memory_agent_node",
    "get_memory_manager",
    "supervisor_node",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_nodes.py::TestSupervisorNode -v
```
Expected: All PASS

- [ ] **Step 6: 提交**

```bash
git add i3d_agent/workflow/nodes/supervisor.py i3d_agent/workflow/nodes/__init__.py tests/test_workflow/test_nodes.py
git commit -m "feat: add supervisor node"
```

---

## Task 7: 实现 search_agent 节点

**Files:**
- Create: `i3d_agent/workflow/nodes/search_agent.py`
- Modify: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 添加 search_agent 节点测试**

```python
# tests/test_workflow/test_nodes.py (添加)

from i3d_agent.workflow.nodes.search_agent import search_agent_node
from i3d_agent.agents.base import NeedsClarificationError


class TestSearchAgentNode:
    """测试 search_agent 节点"""

    @pytest.mark.asyncio
    @patch("i3d_agent.workflow.nodes.search_agent.SearchAgent")
    async def test_search_agent_executes_successfully(self, mock_agent_class):
        """测试 search_agent 成功执行"""
        # Mock SearchAgent
        mock_agent = Mock()
        mock_agent.search.return_value = {
            "results": [
                {"item_code": "BOLT001", "name": "螺栓"},
            ]
        }
        mock_agent_class.return_value = mock_agent

        from i3d_agent.workflow.state import SubTask

        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="pending",
            input_data={"query": "螺栓", "search_type": "3d"},
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await search_agent_node(state)

        assert new_state["sub_tasks"][0].status == "completed"
        assert new_state["sub_tasks"][0].output_data is not None
        assert len(new_state["sub_tasks"][0].output_data["results"]) == 1

    @pytest.mark.asyncio
    @patch("i3d_agent.workflow.nodes.search_agent.SearchAgent")
    async def test_search_agent_requests_clarification(self, mock_agent_class):
        """测试 search_agent 请求澄清"""
        # Mock SearchAgent 抛出 NeedsClarificationError
        mock_agent = Mock()
        mock_agent.search.side_effect = NeedsClarificationError(
            "请指定搜索类型",
            options=["3d", "2d"]
        )
        mock_agent_class.return_value = mock_agent

        from i3d_agent.workflow.state import SubTask, ClarificationRequest

        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="pending",
            input_data={"query": "螺栓"},
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await search_agent_node(state)

        assert new_state["sub_tasks"][0].status == "needs_clarification"
        assert new_state["pending_clarification"] is not None
        assert new_state["pending_clarification"].question == "请指定搜索类型"

    @pytest.mark.asyncio
    @patch("i3d_agent.workflow.nodes.search_agent.SearchAgent")
    async def test_search_agent_handles_error(self, mock_agent_class):
        """测试 search_agent 处理错误"""
        # Mock SearchAgent 抛出普通异常
        mock_agent = Mock()
        mock_agent.search.side_effect = Exception("网络错误")
        mock_agent_class.return_value = mock_agent

        from i3d_agent.workflow.state import SubTask, ErrorInfo

        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="pending",
            input_data={"query": "螺栓"},
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await search_agent_node(state)

        assert new_state["sub_tasks"][0].status == "failed"
        assert new_state["error"] is not None
        assert new_state["error"].message == "网络错误"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_nodes.py::TestSearchAgentNode -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现 search_agent 节点**

```python
# i3d_agent/workflow/nodes/search_agent.py

"""
Search agent node for the I3D Agent workflow.

This node wraps the SearchAgent to handle 3D/2D model searches.
"""

from typing import Dict, Any
from unittest.mock import Mock

from i3d_agent.agents.search import SearchAgent
from i3d_agent.agents.base import NeedsClarificationError, AgentError
from i3d_agent.workflow.state import WorkflowState, SubTask, ClarificationRequest, ErrorInfo
from i3d_agent.workflow.utils import get_task_by_id, update_task_status


async def search_agent_node(state: WorkflowState) -> WorkflowState:
    """Search agent 节点函数。

    此节点负责：
    1. 获取当前待处理的搜索任务
    2. 调用 SearchAgent 执行搜索
    3. 处理 NeedsClarificationError（转为澄清请求）
    4. 处理其他错误（转为 ErrorInfo）

    Args:
        state: 当前工作流状态

    Returns:
        更新后的工作流状态
    """
    sub_tasks = state.get("sub_tasks", [])
    tenant_id = state["tenant_id"]
    user_id = state["user_id"]

    # 找到当前待处理的搜索任务
    current_task: SubTask | None = None
    for task in sub_tasks:
        if task.task_type == "search" and task.status in ["pending", "running"]:
            current_task = task
            break

    if not current_task:
        # 没有待处理的搜索任务，返回原状态
        return state

    # 更新任务状态为 running
    current_task.status = "running"  # type: ignore

    try:
        # 调用 SearchAgent 执行搜索
        agent = SearchAgent()
        input_data = current_task.input_data

        result = await agent.search(
            query=input_data.get("query", ""),
            search_type=input_data.get("search_type", "3d"),
            params=input_data.get("params", {}),
            tenant_id=tenant_id,
        )

        # 更新任务状态为完成
        current_task.status = "completed"  # type: ignore
        current_task.output_data = result

    except NeedsClarificationError as e:
        # 需要用户澄清
        current_task.status = "needs_clarification"  # type: ignore
        current_task.error_message = str(e)

        state["pending_clarification"] = ClarificationRequest(
            task_id=current_task.task_id,
            question=e.question,
            options=e.options,
        )

    except Exception as e:
        # 其他错误
        error_message = str(e)

        # 分类错误类型（简化版本）
        if "timeout" in error_message.lower() or "网络" in error_message:
            error_type = "retriable"
        elif "服务" in error_message or "降级" in error_message:
            error_type = "degradable"
        else:
            error_type = "critical"

        current_task.status = "failed"  # type: ignore
        current_task.error_message = error_message

        state["error"] = ErrorInfo(
            task_id=current_task.task_id,
            error_type=error_type,  # type: ignore
            message=error_message,
            original_error=type(e).__name__,
        )

    return state
```

- [ ] **Step 4: 更新 nodes __init__.py**

```python
# i3d_agent/workflow/nodes/__init__.py (添加)

from i3d_agent.workflow.nodes.search_agent import search_agent_node

__all__ = [
    "memory_agent_node",
    "get_memory_manager",
    "supervisor_node",
    "search_agent_node",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_nodes.py::TestSearchAgentNode -v
```
Expected: All PASS

- [ ] **Step 6: 提交**

```bash
git add i3d_agent/workflow/nodes/search_agent.py i3d_agent/workflow/nodes/__init__.py tests/test_workflow/test_nodes.py
git commit -m "feat: add search_agent node"
```

---

## Task 8: 实现 rag_agent 节点

**Files:**
- Create: `i3d_agent/workflow/nodes/rag_agent.py`
- Modify: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 添加 rag_agent 节点测试**

```python
# tests/test_workflow/test_nodes.py (添加)

from i3d_agent.workflow.nodes.rag_agent import rag_agent_node


class TestRAGAgentNode:
    """测试 rag_agent 节点"""

    @pytest.mark.asyncio
    @patch("i3d_agent.workflow.nodes.rag_agent.RAGAgent")
    async def test_rag_agent_executes_successfully(self, mock_agent_class):
        """测试 rag_agent 成功执行"""
        mock_agent = Mock()
        mock_agent.answer.return_value = {
            "answer": "API 使用方法如下...",
            "sources": [{"title": "API 文档", "source": "api.pdf"}],
        }
        mock_agent_class.return_value = mock_agent

        from i3d_agent.workflow.state import SubTask

        task = SubTask(
            task_id="task_1",
            task_type="rag",
            agent="rag_agent",
            status="pending",
            input_data={"question": "如何使用 API"},
        )

        state: WorkflowState = {
            "query": "如何使用 API",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await rag_agent_node(state)

        assert new_state["sub_tasks"][0].status == "completed"
        assert new_state["sub_tasks"][0].output_data is not None

    @pytest.mark.asyncio
    @patch("i3d_agent.workflow.nodes.rag_agent.RAGAgent")
    async def test_rag_agent_requests_clarification(self, mock_agent_class):
        """测试 rag_agent 请求澄清"""
        mock_agent = Mock()
        mock_agent.answer.side_effect = NeedsClarificationError(
            "请指定要查询的组件",
            options=["组件A", "组件B"]
        )
        mock_agent_class.return_value = mock_agent

        from i3d_agent.workflow.state import SubTask

        task = SubTask(
            task_id="task_1",
            task_type="rag",
            agent="rag_agent",
            status="pending",
            input_data={"question": "文档怎么用"},
        )

        state: WorkflowState = {
            "query": "文档怎么用",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await rag_agent_node(state)

        assert new_state["sub_tasks"][0].status == "needs_clarification"
        assert new_state["pending_clarification"] is not None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_nodes.py::TestRAGAgentNode -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现 rag_agent 节点**

```python
# i3d_agent/workflow/nodes/rag_agent.py

"""
RAG agent node for the I3D Agent workflow.

This node wraps the RAGAgent to handle document-based Q&A.
"""

from typing import Dict, Any

from i3d_agent.agents.rag import RAGAgent
from i3d_agent.agents.base import NeedsClarificationError
from i3d_agent.workflow.state import WorkflowState, SubTask, ClarificationRequest, ErrorInfo


async def rag_agent_node(state: WorkflowState) -> WorkflowState:
    """RAG agent 节点函数。

    此节点负责：
    1. 获取当前待处理的 RAG 任务
    2. 调用 RAGAgent 执行问答
    3. 处理 NeedsClarificationError（转为澄清请求）
    4. 处理其他错误（转为 ErrorInfo）

    Args:
        state: 当前工作流状态

    Returns:
        更新后的工作流状态
    """
    sub_tasks = state.get("sub_tasks", [])
    tenant_id = state["tenant_id"]

    # 找到当前待处理的 RAG 任务
    current_task: SubTask | None = None
    for task in sub_tasks:
        if task.task_type == "rag" and task.status in ["pending", "running"]:
            current_task = task
            break

    if not current_task:
        return state

    # 更新任务状态为 running
    current_task.status = "running"  # type: ignore

    try:
        # 调用 RAGAgent 执行问答
        agent = RAGAgent()
        input_data = current_task.input_data

        result = await agent.answer(
            question=input_data.get("question", ""),
            tenant_id=tenant_id,
        )

        # 更新任务状态为完成
        current_task.status = "completed"  # type: ignore
        current_task.output_data = result

    except NeedsClarificationError as e:
        # 需要用户澄清
        current_task.status = "needs_clarification"  # type: ignore
        current_task.error_message = str(e)

        state["pending_clarification"] = ClarificationRequest(
            task_id=current_task.task_id,
            question=e.question,
            options=e.options,
        )

    except Exception as e:
        # 其他错误
        error_message = str(e)

        # 分类错误类型
        if "timeout" in error_message.lower():
            error_type = "retriable"
        else:
            error_type = "degradable"

        current_task.status = "failed"  # type: ignore
        current_task.error_message = error_message

        state["error"] = ErrorInfo(
            task_id=current_task.task_id,
            error_type=error_type,  # type: ignore
            message=error_message,
            original_error=type(e).__name__,
        )

    return state
```

- [ ] **Step 4: 更新 nodes __init__.py**

```python
# i3d_agent/workflow/nodes/__init__.py (添加)

from i3d_agent.workflow.nodes.rag_agent import rag_agent_node

__all__ = [
    "memory_agent_node",
    "get_memory_manager",
    "supervisor_node",
    "search_agent_node",
    "rag_agent_node",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_nodes.py::TestRAGAgentNode -v
```
Expected: All PASS

- [ ] **Step 6: 提交**

```bash
git add i3d_agent/workflow/nodes/rag_agent.py i3d_agent/workflow/nodes/__init__.py tests/test_workflow/test_nodes.py
git commit -m "feat: add rag_agent node"
```

---

## Task 9: 实现 process_agent 节点

**Files:**
- Create: `i3d_agent/workflow/nodes/process_agent.py`
- Modify: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 添加 process_agent 节点测试**

```python
# tests/test_workflow/test_nodes.py (添加)

from i3d_agent.workflow.nodes.process_agent import process_agent_node


class TestProcessAgentNode:
    """测试 process_agent 节点"""

    @pytest.mark.asyncio
    @patch("i3d_agent.workflow.nodes.process_agent.ProcessAgent")
    async def test_process_agent_executes_successfully(self, mock_agent_class):
        """测试 process_agent 成功执行"""
        mock_agent = Mock()
        mock_agent.get_status.return_value = {
            "task_id": "task_123",
            "status": "completed",
            "progress": 100,
        }
        mock_agent_class.return_value = mock_agent

        from i3d_agent.workflow.state import SubTask

        task = SubTask(
            task_id="task_1",
            task_type="process",
            agent="process_agent",
            status="pending",
            input_data={"task_id": "task_123"},
        )

        state: WorkflowState = {
            "query": "处理状态",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await process_agent_node(state)

        assert new_state["sub_tasks"][0].status == "completed"
        assert new_state["sub_tasks"][0].output_data is not None

    @pytest.mark.asyncio
    @patch("i3d_agent.workflow.nodes.process_agent.ProcessAgent")
    async def test_process_agent_handles_error(self, mock_agent_class):
        """测试 process_agent 处理错误"""
        mock_agent = Mock()
        mock_agent.get_status.side_effect = Exception("任务不存在")
        mock_agent_class.return_value = mock_agent

        from i3d_agent.workflow.state import SubTask

        task = SubTask(
            task_id="task_1",
            task_type="process",
            agent="process_agent",
            status="pending",
            input_data={"task_id": "invalid_task"},
        )

        state: WorkflowState = {
            "query": "处理状态",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await process_agent_node(state)

        assert new_state["sub_tasks"][0].status == "failed"
        assert new_state["error"] is not None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_nodes.py::TestProcessAgentNode -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现 process_agent 节点**

```python
# i3d_agent/workflow/nodes/process_agent.py

"""
Process agent node for the I3D Agent workflow.

This node wraps the ProcessAgent to handle file processing status queries.
"""

from typing import Dict, Any

from i3d_agent.agents.process import ProcessAgent
from i3d_agent.agents.base import NeedsClarificationError
from i3d_agent.workflow.state import WorkflowState, SubTask, ClarificationRequest, ErrorInfo


async def process_agent_node(state: WorkflowState) -> WorkflowState:
    """Process agent 节点函数。

    此节点负责：
    1. 获取当前待处理的 process 任务
    2. 调用 ProcessAgent 查询状态
    3. 处理错误（转为 ErrorInfo）

    Args:
        state: 当前工作流状态

    Returns:
        更新后的工作流状态
    """
    sub_tasks = state.get("sub_tasks", [])
    tenant_id = state["tenant_id"]

    # 找到当前待处理的 process 任务
    current_task: SubTask | None = None
    for task in sub_tasks:
        if task.task_type == "process" and task.status in ["pending", "running"]:
            current_task = task
            break

    if not current_task:
        return state

    # 更新任务状态为 running
    current_task.status = "running"  # type: ignore

    try:
        # 调用 ProcessAgent 查询状态
        agent = ProcessAgent()
        input_data = current_task.input_data

        # 根据输入数据决定调用哪个方法
        if "task_id" in input_data:
            result = await agent.get_status(
                task_id=input_data["task_id"],
                tenant_id=tenant_id,
            )
        elif "item_code" in input_data:
            result = await agent.get_history(
                item_code=input_data["item_code"],
                tenant_id=tenant_id,
            )
        else:
            raise ValueError("Invalid input data for process task")

        # 更新任务状态为完成
        current_task.status = "completed"  # type: ignore
        current_task.output_data = result

    except NeedsClarificationError as e:
        # 需要用户澄清
        current_task.status = "needs_clarification"  # type: ignore
        current_task.error_message = str(e)

        state["pending_clarification"] = ClarificationRequest(
            task_id=current_task.task_id,
            question=e.question,
            options=e.options,
        )

    except Exception as e:
        # 其他错误
        error_message = str(e)

        # 分类错误类型
        if "timeout" in error_message.lower():
            error_type = "retriable"
        else:
            error_type = "degradable"

        current_task.status = "failed"  # type: ignore
        current_task.error_message = error_message

        state["error"] = ErrorInfo(
            task_id=current_task.task_id,
            error_type=error_type,  # type: ignore
            message=error_message,
            original_error=type(e).__name__,
        )

    return state
```

- [ ] **Step 4: 更新 nodes __init__.py**

```python
# i3d_agent/workflow/nodes/__init__.py (添加)

from i3d_agent.workflow.nodes.process_agent import process_agent_node

__all__ = [
    "memory_agent_node",
    "get_memory_manager",
    "supervisor_node",
    "search_agent_node",
    "rag_agent_node",
    "process_agent_node",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_nodes.py::TestProcessAgentNode -v
```
Expected: All PASS

- [ ] **Step 6: 提交**

```bash
git add i3d_agent/workflow/nodes/process_agent.py i3d_agent/workflow/nodes/__init__.py tests/test_workflow/test_nodes.py
git commit -m "feat: add process_agent node"
```

---

## Task 10: 实现 aggregator 节点

**Files:**
- Create: `i3d_agent/workflow/nodes/aggregator.py`
- Modify: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 添加 aggregator 节点测试**

```python
# tests/test_workflow/test_nodes.py (添加)

from i3d_agent.workflow.nodes.aggregator import aggregator_node
from i3d_agent.models.chat import SourceDocument


class TestAggregatorNode:
    """测试 aggregator 节点"""

    @pytest.mark.asyncio
    async def test_aggregator_single_search_task(self):
        """测试聚合单个搜索任务"""
        from i3d_agent.workflow.state import SubTask

        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="completed",
            input_data={},
            output_data={
                "results": [
                    {"item_code": "BOLT001", "name": "螺栓"},
                ]
            },
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await aggregator_node(state)

        assert new_state["response"] is not None
        assert "螺栓" in new_state["response"]
        assert new_state["should_continue"] is False

    @pytest.mark.asyncio
    async def test_aggregator_multiple_tasks(self):
        """测试聚合多个任务"""
        from i3d_agent.workflow.state import SubTask

        search_task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="completed",
            input_data={},
            output_data={
                "results": [{"item_code": "BOLT001", "name": "螺栓"}],
            },
        )

        rag_task = SubTask(
            task_id="task_2",
            task_type="rag",
            agent="rag_agent",
            status="completed",
            input_data={},
            output_data={
                "answer": "API 使用方法...",
                "sources": [{"title": "API 文档"}],
            },
        )

        state: WorkflowState = {
            "query": "搜索螺栓并查看文档",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [search_task, rag_task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await aggregator_node(state)

        assert new_state["response"] is not None
        assert new_state["sources"] is not None
        assert new_state["should_continue"] is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_nodes.py::TestAggregatorNode -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现 aggregator 节点**

```python
# i3d_agent/workflow/nodes/aggregator.py

"""
Aggregator node for the I3D Agent workflow.

This node collects results from all completed tasks and builds
the final response.
"""

from typing import List, Dict, Any, Optional

from i3d_agent.workflow.state import WorkflowState, SubTask


async def aggregator_node(state: WorkflowState) -> WorkflowState:
    """Aggregator 节点函数。

    此节点负责：
    1. 收集所有已完成任务的输出
    2. 合并来源文档
    3. 构建统一响应
    4. 设置 should_continue 为 False

    Args:
        state: 当前工作流状态

    Returns:
        更新后的工作流状态，包含最终响应
    """
    sub_tasks: List[SubTask] = state.get("sub_tasks", [])

    # 收集已完成任务
    completed_tasks = [task for task in sub_tasks if task.status == "completed"]

    if not completed_tasks:
        # 没有完成的任务，返回默认响应
        state["response"] = "抱歉，无法完成您的请求。"
        state["should_continue"] = False
        return state

    # 构建响应
    response_parts = []
    sources = []
    thought_process_parts = []

    for task in completed_tasks:
        output = task.output_data
        if not output:
            continue

        if task.task_type == "search":
            # 搜索结果
            results = output.get("results", [])
            if results:
                response_parts.append(f"找到 {len(results)} 个结果：")
                for i, result in enumerate(results[:5], 1):  # 最多显示 5 个
                    name = result.get("name", result.get("item_code", ""))
                    response_parts.append(f"{i}. {name}")

                thought_process_parts.append(f"执行搜索任务，找到 {len(results)} 个结果")

        elif task.task_type == "rag":
            # RAG 问答
            answer = output.get("answer", "")
            if answer:
                response_parts.append(answer)

            task_sources = output.get("sources", [])
            sources.extend(task_sources)

            thought_process_parts.append("执行文档检索任务")

        elif task.task_type == "process":
            # 处理状态
            status = output.get("status", "unknown")
            progress = output.get("progress", 0)
            response_parts.append(f"任务状态：{status}，进度：{progress}%")

            thought_process_parts.append("查询处理状态")

    # 构建最终响应
    if response_parts:
        state["response"] = "\n\n".join(response_parts)
    else:
        state["response"] = "已完成任务，但没有返回结果。"

    # 设置来源文档
    if sources:
        state["sources"] = sources

    # 设置思考过程
    if thought_process_parts:
        state["thought_process"] = "；".join(thought_process_parts)

    # 设置元数据
    state["metadata"] = {
        "completed_tasks": len(completed_tasks),
        "total_tasks": len(sub_tasks),
    }

    # 标记流程结束
    state["should_continue"] = False

    return state
```

- [ ] **Step 4: 更新 nodes __init__.py**

```python
# i3d_agent/workflow/nodes/__init__.py (添加)

from i3d_agent.workflow.nodes.aggregator import aggregator_node

__all__ = [
    "memory_agent_node",
    "get_memory_manager",
    "supervisor_node",
    "search_agent_node",
    "rag_agent_node",
    "process_agent_node",
    "aggregator_node",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_nodes.py::TestAggregatorNode -v
```
Expected: All PASS

- [ ] **Step 6: 提交**

```bash
git add i3d_agent/workflow/nodes/aggregator.py i3d_agent/workflow/nodes/__init__.py tests/test_workflow/test_nodes.py
git commit -m "feat: add aggregator node"
```

---

## Task 11: 实现 error_handler 节点

**Files:**
- Create: `i3d_agent/workflow/nodes/error_handler.py`
- Modify: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 添加 error_handler 节点测试**

```python
# tests/test_workflow/test_nodes.py (添加)

from i3d_agent.workflow.nodes.error_handler import error_handler_node
from i3d_agent.workflow.state import ErrorInfo


class TestErrorHandlerNode:
    """测试 error_handler 节点"""

    @pytest.mark.asyncio
    async def test_error_handler_retriable_error(self):
        """测试处理可重试错误"""
        from i3d_agent.workflow.state import SubTask

        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="failed",
            input_data={},
            error_message="网络超时",
            retry_count=0,
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": ErrorInfo(
                task_id="task_1",
                error_type="retriable",
                message="网络超时",
            ),
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await error_handler_node(state)

        # 验证任务重置为 pending 且重试计数增加
        assert new_state["sub_tasks"][0].status == "pending"
        assert new_state["sub_tasks"][0].retry_count == 1
        assert new_state["error"] is None  # 错误已清除

    @pytest.mark.asyncio
    async def test_error_handler_degradable_error(self):
        """测试处理可降级错误"""
        from i3d_agent.workflow.state import SubTask

        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="failed",
            input_data={},
            error_message="服务降级",
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": ErrorInfo(
                task_id="task_1",
                error_type="degradable",
                message="服务降级",
            ),
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": "degrade",
            "should_continue": True,
        }

        new_state = await error_handler_node(state)

        # 验证降级处理
        assert new_state["next_action"] == "aggregate"
        assert new_state["response"] is not None  # 包含降级消息

    @pytest.mark.asyncio
    async def test_error_handler_critical_error(self):
        """测试处理严重错误"""
        from i3d_agent.workflow.state import SubTask

        task = SubTask(
            task_id="task_1",
            task_type="search",
            agent="search_agent",
            status="failed",
            input_data={},
            error_message="严重错误",
        )

        state: WorkflowState = {
            "query": "搜索螺栓",
            "user_id": "user123",
            "tenant_id": "huabei",
            "session_id": "session456",
            "stream": False,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [task],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": ErrorInfo(
                task_id="task_1",
                error_type="critical",
                message="严重错误",
            ),
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        new_state = await error_handler_node(state)

        # 验证终止执行
        assert new_state["should_continue"] is False
        assert "严重错误" in new_state["response"]
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_nodes.py::TestErrorHandlerNode -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现 error_handler 节点**

```python
# i3d_agent/workflow/nodes/error_handler.py

"""
Error handler node for the I3D Agent workflow.

This node analyzes errors and decides on retry, degradation,
or termination.
"""

from typing import Dict, Any

from i3d_agent.workflow.state import WorkflowState, SubTask, ErrorInfo


async def error_handler_node(state: WorkflowState) -> WorkflowState:
    """Error handler 节点函数。

    此节点负责：
    1. 分析错误类型
    2. 可重试错误：重置任务状态，增加重试计数
    3. 可降级错误：设置降级响应
    4. 严重错误：终止执行

    Args:
        state: 当前工作流状态

    Returns:
        更新后的工作流状态
    """
    error: ErrorInfo | None = state.get("error")
    if not error:
        return state

    sub_tasks: list[SubTask] = state.get("sub_tasks", [])
    failed_task: SubTask | None = None

    # 找到失败的任务
    for task in sub_tasks:
        if task.task_id == error.task_id:
            failed_task = task
            break

    if not failed_task:
        # 找不到失败任务，清除错误并继续
        state["error"] = None
        return state

    if error.error_type == "retriable":
        # 可重试错误
        if failed_task.retry_count < 3:
            # 重置任务状态为 pending
            failed_task.status = "pending"  # type: ignore
            failed_task.retry_count += 1
            # 清除错误
            state["error"] = None
        else:
            # 超过最大重试次数，转为严重错误
            state["should_continue"] = False
            state["response"] = f"请求失败：{error.message}（已重试 {failed_task.retry_count} 次）"

    elif error.error_type == "degradable":
        # 可降级错误
        state["next_action"] = "aggregate"
        state["response"] = f"（部分服务不可用：{error.message}）"
        # 清除错误，继续执行
        state["error"] = None

    else:
        # 严重错误或需要用户帮助
        state["should_continue"] = False
        state["response"] = f"遇到问题：{error.message}"

    return state
```

- [ ] **Step 4: 更新 nodes __init__.py**

```python
# i3d_agent/workflow/nodes/__init__.py (添加)

from i3d_agent.workflow.nodes.error_handler import error_handler_node

__all__ = [
    "memory_agent_node",
    "get_memory_manager",
    "supervisor_node",
    "search_agent_node",
    "rag_agent_node",
    "process_agent_node",
    "aggregator_node",
    "error_handler_node",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_nodes.py::TestErrorHandlerNode -v
```
Expected: All PASS

- [ ] **Step 6: 提交**

```bash
git add i3d_agent/workflow/nodes/error_handler.py i3d_agent/workflow/nodes/__init__.py tests/test_workflow/test_nodes.py
git commit -m "feat: add error_handler node"
```

---

## Task 12: 构建工作流图

**Files:**
- Create: `i3d_agent/workflow/graph.py`
- Test: `tests/test_workflow/test_graph.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_workflow/test_graph.py

import pytest

from i3d_agent.workflow.graph import I3DWorkflow
from i3d_agent.workflow.nodes.memory_agent import get_memory_manager


class TestI3DWorkflow:
    """测试 I3DWorkflow 工作流"""

    def test_workflow_initialization(self):
        """测试工作流初始化"""
        memory_manager = get_memory_manager()
        workflow = I3DWorkflow(memory_manager)

        assert workflow.graph is not None
        assert workflow.memory_manager is not None

    def test_workflow_creates_state_graph(self):
        """测试工作流创建 StateGraph"""
        memory_manager = get_memory_manager()
        workflow = I3DWorkflow(memory_manager)

        # 验证工作流图已编译
        assert workflow.graph is not None

    @pytest.mark.asyncio
    async def test_workflow_run_simple_search(self):
        """测试工作流执行简单搜索"""
        from unittest.mock import patch, Mock

        memory_manager = get_memory_manager()
        workflow = I3DWorkflow(memory_manager)

        # Mock 所有 Agent
        with patch("i3d_agent.workflow.nodes.search_agent.SearchAgent") as mock_search:
            mock_agent = Mock()
            mock_agent.search.return_value = {
                "results": [{"item_code": "BOLT001", "name": "螺栓"}],
            }
            mock_search.return_value = mock_agent

            response = await workflow.run(
                query="搜索螺栓",
                user_id="user123",
                tenant_id="huabei",
                session_id="session456",
            )

            assert response.response is not None
            assert "螺栓" in response.response or "结果" in response.response

    @pytest.mark.asyncio
    async def test_workflow_with_error(self):
        """测试工作流处理错误"""
        from unittest.mock import patch, Mock

        memory_manager = get_memory_manager()
        workflow = I3DWorkflow(memory_manager)

        # Mock SearchAgent 抛出错误
        with patch("i3d_agent.workflow.nodes.search_agent.SearchAgent") as mock_search:
            mock_agent = Mock()
            mock_agent.search.side_effect = Exception("网络错误")
            mock_search.return_value = mock_agent

            response = await workflow.run(
                query="搜索螺栓",
                user_id="user123",
                tenant_id="huabei",
                session_id="session456",
            )

            # 验证错误被处理
            assert response.response is not None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_workflow/test_graph.py -v
```
Expected: FAIL - "module not found"

- [ ] **Step 3: 实现工作流图**

```python
# i3d_agent/workflow/graph.py

"""
I3D Agent workflow graph.

This module builds the LangGraph StateGraph workflow that coordinates
all agents and nodes.
"""

import os
from typing import Optional, Dict, Any, AsyncIterator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from i3d_agent.memory.manager import MemoryManager
from i3d_agent.models.chat import ChatResponse, SourceDocument
from i3d_agent.workflow.state import WorkflowState
from i3d_agent.workflow.nodes.memory_agent import memory_agent_node
from i3d_agent.workflow.nodes.supervisor import supervisor_node
from i3d_agent.workflow.nodes.search_agent import search_agent_node
from i3d_agent.workflow.nodes.rag_agent import rag_agent_node
from i3d_agent.workflow.nodes.process_agent import process_agent_node
from i3d_agent.workflow.nodes.aggregator import aggregator_node
from i3d_agent.workflow.nodes.error_handler import error_handler_node
from i3d_agent.workflow.conditions.routing import (
    should_route_to_memory,
    check_all_tasks_completed,
    decide_next_agent,
    classify_error,
)


class I3DWorkflow:
    """I3D Agent System 工作流。

    此类构建并管理 LangGraph 工作流图，协调所有 Agent 执行任务。
    """

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ):
        """初始化工作流。

        Args:
            memory_manager: 可选的 MemoryManager 实例
            checkpointer: 可选的检查点保存器
        """
        self.memory_manager = memory_manager or MemoryManager()
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流图。

        Returns:
            编译后的 StateGraph
        """

        # 创建状态图
        workflow = StateGraph(WorkflowState)

        # === 添加节点 ===
        workflow.add_node("memory_agent", memory_agent_node)
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("search_agent", search_agent_node)
        workflow.add_node("rag_agent", rag_agent_node)
        workflow.add_node("process_agent", process_agent_node)
        workflow.add_node("aggregator", aggregator_node)
        workflow.add_node("error_handler", error_handler_node)

        # === 设置入口 ===
        workflow.set_entry_point("route_memory")

        # === 添加边 ===

        # 1. 记忆路由
        workflow.add_conditional_edges(
            "route_memory",
            should_route_to_memory,
            {
                "load_memory": "memory_agent",
                "skip_memory": "supervisor",
            },
        )

        # 2. memory_agent → supervisor
        workflow.add_edge("memory_agent", "supervisor")

        # 3. supervisor → dispatcher (decide_next_agent 的别名)
        workflow.add_conditional_edges(
            "supervisor",
            lambda state: "has_tasks" if state.get("sub_tasks") else "no_tasks",
            {
                "has_tasks": "dispatcher",
                "no_tasks": "aggregator",
            },
        )

        # 4. dispatcher → 各个 Agent
        workflow.add_conditional_edges(
            "dispatcher",
            decide_next_agent,
            {
                "search_agent": "search_agent",
                "rag_agent": "rag_agent",
                "process_agent": "process_agent",
                "aggregator": "aggregator",
            },
        )

        # 5. Agent 执行后检查任务完成状态
        for agent_name in ["search_agent", "rag_agent", "process_agent"]:
            workflow.add_conditional_edges(
                agent_name,
                check_all_tasks_completed,
                {
                    "continue_tasks": "dispatcher",
                    "aggregate_results": "aggregator",
                    "handle_error": "error_handler",
                },
            )

        # 6. error_handler → 根据错误类型决定
        workflow.add_conditional_edges(
            "error_handler",
            classify_error,
            {
                "retry": "dispatcher",
                "degrade": "aggregator",
                "fail": END,
                "no_error": "dispatcher",
            },
        )

        # 7. aggregator → END
        workflow.add_edge("aggregator", END)

        # === 编译工作流 ===
        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)

        # 使用 SQLite 检查点（用于会话恢复）
        checkpoint_path = os.path.join(os.getcwd(), "workflow_checkpoints.db")
        checkpointer = SqliteSaver.from_conn_string(checkpoint_path)
        return workflow.compile(checkpointer=checkpointer)

    async def run(
        self,
        query: str,
        user_id: str,
        tenant_id: str,
        session_id: str,
        stream: bool = False,
    ) -> ChatResponse:
        """运行工作流。

        Args:
            query: 用户查询
            user_id: 用户 ID
            tenant_id: 租户 ID
            session_id: 会话 ID
            stream: 是否流式返回

        Returns:
            ChatResponse 响应对象
        """

        # 初始化状态
        initial_state: WorkflowState = {
            "query": query,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "stream": stream,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        # 执行工作流
        config = {"configurable": {"thread_id": session_id}}

        if stream:
            # 流式执行（返回事件迭代器）
            # 注意：这里简化处理，实际需要实现流式逻辑
            final_state = await self.graph.ainvoke(initial_state, config)
        else:
            # 一次性执行
            final_state = await self.graph.ainvoke(initial_state, config)

        # 构建 ChatResponse
        return ChatResponse(
            response=final_state.get("response", ""),
            sources=final_state.get("sources"),
            thought_process=final_state.get("thought_process"),
            session_id=session_id,
            metadata=final_state.get("metadata"),
        )

    async def astream_events(
        self,
        query: str,
        user_id: str,
        tenant_id: str,
        session_id: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式执行工作流并返回事件。

        Args:
            query: 用户查询
            user_id: 用户 ID
            tenant_id: 租户 ID
            session_id: 会话 ID

        Yields:
            工作流事件字典
        """

        # 初始化状态
        initial_state: WorkflowState = {
            "query": query,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "stream": True,
            "messages": [],
            "conversation_history": [],
            "sub_tasks": [],
            "current_task_index": 0,
            "pending_clarification": None,
            "clarification_answer": None,
            "error": None,
            "response": None,
            "sources": None,
            "thought_process": None,
            "metadata": None,
            "next_action": None,
            "should_continue": True,
        }

        config = {"configurable": {"thread_id": session_id}}

        # 流式执行
        async for event in self.graph.astream(initial_state, config):
            yield event
```

- [ ] **Step 4: 更新 workflow __init__.py**

```python
# i3d_agent/workflow/__init__.py (更新)

"""Workflow module for I3D Agent System."""

from i3d_agent.workflow.state import (
    SubTask,
    ClarificationRequest,
    ErrorInfo,
    WorkflowState,
)
from i3d_agent.workflow.utils import (
    is_simple_query,
    get_task_by_id,
    get_next_pending_task,
    get_failed_task,
    update_task_status,
    is_retriable_error,
    is_degradable_error,
    is_critical_error,
)
from i3d_agent.workflow.graph import I3DWorkflow

__all__ = [
    # State models
    "SubTask",
    "ClarificationRequest",
    "ErrorInfo",
    "WorkflowState",
    # Utils
    "is_simple_query",
    "get_task_by_id",
    "get_next_pending_task",
    "get_failed_task",
    "update_task_status",
    "is_retriable_error",
    "is_degradable_error",
    "is_critical_error",
    # Main workflow
    "I3DWorkflow",
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_workflow/test_graph.py -v
```
Expected: All PASS

- [ ] **Step 6: 运行所有工作流测试**

```bash
pytest tests/test_workflow/ -v
```
Expected: All PASS

- [ ] **Step 7: 提交**

```bash
git add i3d_agent/workflow/graph.py i3d_agent/workflow/__init__.py tests/test_workflow/test_graph.py
git commit -m "feat: add I3DWorkflow graph"
```

---

## Task 13: 更新 requirements.txt

**Files:**
- Modify: `i3d_agent/requirements.txt`

- [ ] **Step 1: 更新 langgraph 版本**

```bash
# 检查当前 langgraph 版本
grep langgraph /data/yzh/i3d-agent-system/i3d_agent/requirements.txt
```

- [ ] **Step 2: 确保版本符合要求**

当前 requirements.txt 中已有 `langgraph>=0.0.20`，更新为 `langgraph>=0.2.0`：

```bash
sed -i 's/langgraph>=0.0.20/langgraph>=0.2.0/g' /data/yzh/i3d-agent-system/i3d_agent/requirements.txt
```

- [ ] **Step 3: 验证更新**

```bash
grep langgraph /data/yzh/i3d-agent-system/i3d_agent/requirements.txt
```
Expected: `langgraph>=0.2.0`

- [ ] **Step 4: 提交**

```bash
git add i3d_agent/requirements.txt
git commit -m "chore: update langgraph to >=0.2.0"
```

---

## Task 14: 更新进度文档

**Files:**
- Modify: `IMPLEMENTATION_PROGRESS.md`

- [ ] **Step 1: 更新 Phase 6 状态为已完成**

在 IMPLEMENTATION_PROGRESS.md 中更新 Phase 6 部分：

```bash
cd /data/yzh/i3d-agent-system
```

手动编辑或使用命令更新文档：

将 Phase 6 部分从：

```markdown
## Phase 6: LangGraph 工作流

**状态**: 待执行

### 任务清单

| 任务 | 描述 | 提交哈希 | 状态 |
|------|------|----------|------|
| 6.1 | 工作流状态定义 | - | ⏳ |
| 6.2 | 工作流图构建 | - | ⏳ |
```

更新为：

```markdown
## Phase 6: LangGraph 工作流 ✅

**完成时间**: 2026-05-29
**状态**: 已完成

### 任务清单

| 任务 | 描述 | 提交哈希 | 状态 |
|------|------|----------|------|
| 6.1 | Agent 异常类 | `xxxxxx` | ✅ |
| 6.2 | 状态模型定义 | `xxxxxx` | ✅ |
| 6.3 | 工具函数 | `xxxxxx` | ✅ |
| 6.4 | 条件路由 | `xxxxxx` | ✅ |
| 6.5 | 节点实现 | `xxxxxx` | ✅ |
| 6.6 | 工作流图构建 | `xxxxxx` | ✅ |
```

同时更新总体进度：

```markdown
## 总体进度

```
█████████████████████████████████████████████████  100%
├─ Phase 1: 项目设置与基础设施  ✅ 100%
├─ Phase 2: 数据模型           ✅ 100%
├─ Phase 3: 记忆系统           ✅ 100%
├─ Phase 4: 工具实现           ✅ 100%
├─ Phase 5: Agent 实现         ✅ 100%
├─ Phase 6: LangGraph 工作流   ✅ 100%
├─ Phase 7: FastAPI 应用       ⏳   0%
├─ Phase 8: Docker 部署        ⏳   0%
└─ Phase 9: 文档               ⏳   0%
```
```

- [ ] **Step 2: 提交**

```bash
git add IMPLEMENTATION_PROGRESS.md
git commit -m "docs: update Phase 6 completion status"
```

---

## 总结

本计划包含 14 个主要任务，涵盖：

1. ✅ 添加 Agent 异常类
2. ✅ 创建状态模型
3. ✅ 实现工具函数
4. ✅ 实现条件路由函数
5. ✅ 实现 memory_agent 节点
6. ✅ 实现 supervisor 节点
7. ✅ 实现 search_agent 节点
8. ✅ 实现 rag_agent 节点
9. ✅ 实现 process_agent 节点
10. ✅ 实现 aggregator 节点
11. ✅ 实现 error_handler 节点
12. ✅ 构建工作流图
13. ✅ 更新依赖
14. ✅ 更新进度文档

---

**计划版本**: 1.0
**创建日期**: 2026-05-29

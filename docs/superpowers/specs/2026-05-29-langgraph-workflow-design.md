# LangGraph 工作流设计文档

**项目**: I3D Agent System
**日期**: 2026-05-29
**Phase**: Phase 6 - LangGraph 工作流实现
**状态**: 设计阶段

---

## 1. 概述

本文档描述 I3D Agent System 的 LangGraph 工作流设计。工作流负责协调多个 Agent（Supervisor、Search、RAG、Process、Memory）处理用户查询，支持任务分解、迭代细化、并行执行和智能错误恢复。

---

## 2. 设计目标

1. **混合任务分解**：简单查询使用规则匹配，复杂查询使用 LLM 智能分解
2. **迭代/细化流程**：Agent 可通过 Supervisor 请求用户澄清
3. **多步骤编排**：支持子任务的顺序和并行执行
4. **智能错误恢复**：Supervisor 分析错误类型，决定重试、降级或请求用户帮助
5. **会话管理**：基于 session_id 维护多轮对话历史
6. **集中式记忆**：MemoryAgent 统一管理所有记忆操作

---

## 3. 核心组件

### 3.1 技术选型

使用 **LangGraph StateGraph** 构建状态机工作流：
- 原生支持循环、条件分支、并行执行
- 内置状态管理，适合迭代/细化流程
- 与 LangChain 生态系统深度集成

### 3.2 状态模型 (WorkflowState)

```python
class SubTask(BaseModel):
    """子任务模型"""
    task_id: str
    task_type: Literal["search", "rag", "process", "memory"]
    agent: str
    status: Literal["pending", "running", "completed", "failed", "needs_clarification"]
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    dependencies: List[str] = []
    retry_count: int = 0

class ClarificationRequest(BaseModel):
    """澄清请求模型"""
    task_id: str
    question: str
    options: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None

class ErrorInfo(BaseModel):
    """错误信息模型"""
    task_id: str
    error_type: Literal["retriable", "degradable", "user_help_needed", "critical"]
    message: str
    original_error: Optional[str] = None

class WorkflowState(TypedDict):
    """工作流状态"""
    # 输入
    query: str
    user_id: str
    tenant_id: str
    session_id: str
    stream: bool

    # 对话历史
    messages: List[Message]
    conversation_history: List[Dict[str, Any]]

    # 任务管理
    sub_tasks: List[SubTask]
    current_task_index: int

    # 澄清与错误
    pending_clarification: Optional[ClarificationRequest]
    clarification_answer: Optional[str]
    error: Optional[ErrorInfo]

    # 输出
    response: Optional[str]
    sources: Optional[List[SourceDocument]]
    thought_process: Optional[str]
    metadata: Optional[Dict[str, Any]]

    # 流程控制
    next_action: Optional[str]
    should_continue: bool
```

---

## 4. 工作流节点

### 4.1 节点列表

| 节点 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `memory_agent` | 加载/保存会话历史和用户记忆 | state | state |
| `supervisor` | 分析意图、分解任务、路由 | state | state |
| `search_agent` | 执行搜索任务 | state | state |
| `rag_agent` | 执行 RAG 查询 | state | state |
| `process_agent` | 查询处理状态 | state | state |
| `aggregator` | 聚合多任务结果 | state | state |
| `error_handler` | 智能错误恢复 | state | state |
| `request_clarification` | 向用户请求澄清 | state | state |

### 4.2 节点详细说明

#### 4.2.1 supervisor 节点

- 使用规则判断查询复杂度
- 简单查询：直接路由到单个 Agent
- 复杂查询：调用 LLM 分解为子任务
- 处理澄清问题的答案

#### 4.2.2 memory_agent 节点

- 加载会话历史
- 保存对话上下文到工作记忆
- 记录搜索历史
- 获取用户偏好

#### 4.2.3 search_agent, rag_agent, process_agent 节点

- 调用对应的 Agent 执行任务
- 捕获 `NeedsClarificationError` 并转为澄清请求
- 捕获执行错误并转为 ErrorInfo

#### 4.2.4 aggregator 节点

- 收集所有已完成任务的输出
- 合并来源文档
- 构建统一响应

#### 4.2.5 error_handler 节点

- 分析错误类型（retriable/degradable/user_help_needed/critical）
- 决定重试、降级或请求用户帮助

---

## 5. 条件路由逻辑

### 5.1 路由函数

```python
def should_route_to_memory(state: WorkflowState) -> str:
    """判断是否需要加载记忆"""
    return "load_memory" if not state["conversation_history"] else "skip_memory"

def check_clarification_needed(state: WorkflowState) -> str:
    """检查是否有 Agent 需要澄清"""
    return "request_clarification" if state["pending_clarification"] else "continue_execution"

def check_all_tasks_completed(state: WorkflowState) -> str:
    """检查所有任务是否完成"""
    pending = [t for t in state["sub_tasks"] if t["status"] in ["pending", "running"]]
    failed = [t for t in state["sub_tasks"] if t["status"] == "failed"]

    if failed:
        return "handle_error"
    elif pending:
        return "continue_tasks"
    else:
        return "aggregate_results"

def decide_next_agent(state: WorkflowState) -> str:
    """决定下一个执行的 Agent"""
    next_task = get_next_pending_task(state["sub_tasks"])
    if not next_task:
        return "aggregator"
    return f"{next_task['task_type']}_agent"

def classify_error(state: WorkflowState) -> str:
    """分类错误并决定处理方式"""
    error = state.get("error")
    if not error:
        return "no_error"

    if is_retriable_error(error):
        return "retry"
    elif is_degradable_error(error):
        return "degrade"
    else:
        return "fail"
```

### 5.2 工作流图结构

```
                    ┌─────────────────┐
                    │   start (input) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  should_route_  │──┐
                    │   to_memory     │  │
                    └────────┬────────┘  │
                             │           │
                ┌────────────┼───────────┘
                │            │
        ┌───────▼──────┐    │
        │ memory_agent │    │
        └───────┬──────┘    │
                │            │
                └────────────┴────────┬────────┐
                                     │        │
                              ┌──────▼──────┐ │
                              │ supervisor  │ │
                              └──────┬──────┘ │
                                     │        │
                         ┌───────────┴────────┴────────┐
                         │                            │
                    ┌────▼────┐                  ┌────▼────┐
                    │ search  │                  │   rag   │
                    │ _agent  │ ...              │ _agent  │
                    └────┬────┘                  └────┬────┘
                         │                            │
                         └──────────┬────────────────┘
                                    │
                         ┌──────────▼─────────┐
                         │  check_all_tasks_  │
                         │    completed       │
                         └──────────┬─────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
      ┌───────▼──────┐      ┌─────▼──────┐       ┌──────▼──────┐
      │   aggregator │      │error_      │       │  request_   │
      │              │      │handler     │       │clarification│
      └──────┬───────┘      └─────┬──────┘       └──────┬──────┘
             │                     │                     │
      ┌──────▼────────────────────▼─────────────────────▼─────┐
      │                    end (return response)                 │
      └─────────────────────────────────────────────────────────┘
```

---

## 6. 文件结构

```
i3d_agent/workflow/
├── __init__.py              # 导出 I3DWorkflow, WorkflowState 等
├── state.py                 # 状态模型定义
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
```

---

## 7. 与现有 Agent 的集成

### 7.1 新增异常类

```python
class AgentError(Exception):
    """Agent 基础异常"""
    pass

class NeedsClarificationError(AgentError):
    """Agent 需要用户澄清时抛出"""
    def __init__(self, question: str, options: Optional[List[str]] = None):
        self.question = question
        self.options = options
        super().__init__(question)
```

### 7.2 Agent 接口调整

现有 Agent 类需要：
1. 返回结构化结果，便于工作流处理
2. 在需要澄清时抛出 `NeedsClarificationError`
3. 确保方法签名与工作流调用一致

---

## 8. 入口点

### 8.1 I3DWorkflow 类

```python
class I3DWorkflow:
    """I3D Agent System 工作流"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流图"""
        # ... 构建逻辑

    async def run(
        self,
        query: str,
        user_id: str,
        tenant_id: str,
        session_id: str,
        stream: bool = False
    ) -> ChatResponse:
        """运行工作流"""
        # ... 执行逻辑
```

### 8.2 使用方式

```python
workflow = I3DWorkflow(memory_manager)
response = await workflow.run(
    query="搜索一个螺栓模型",
    user_id="user123",
    tenant_id="huabei",
    session_id="session456"
)
```

---

## 9. 依赖更新

需要在 `requirements.txt` 中更新：
```
langgraph>=0.2.0
```

---

## 10. 测试策略

### 10.1 单元测试

- 测试每个节点函数
- 测试每个路由函数
- 测试状态模型验证

### 10.2 集成测试

- 测试完整工作流执行
- 测试澄清问题流程
- 测试错误恢复流程
- 测试多任务并行执行

### 10.3 测试文件

```
tests/test_workflow/
├── __init__.py
├── test_state.py           # 状态模型测试
├── test_nodes.py           # 节点测试
├── test_conditions.py      # 路由条件测试
├── test_graph.py           # 工作流图测试
└── test_integration.py     # 集成测试
```

---

## 11. 实施计划

1. **Phase 6.1**: 定义状态模型 (`state.py`)
2. **Phase 6.2**: 实现节点函数 (`nodes/*.py`)
3. **Phase 6.3**: 实现条件路由 (`conditions/routing.py`)
4. **Phase 6.4**: 构建工作流图 (`graph.py`)
5. **Phase 6.5**: 编写测试
6. **Phase 6.6**: 集成现有 Agent

---

*文档版本: 1.0*
*最后更新: 2026-05-29*

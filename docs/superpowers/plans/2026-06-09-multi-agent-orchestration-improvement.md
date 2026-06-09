# Multi-Agent Orchestration Improvement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 I3D Agent System 从“单意图路由到单 Agent”的工作流，升级为支持复杂意图拆解、任务依赖、并行执行、澄清回合、共享产物、综合生成和质量校验的多 Agent 协作系统。

**Architecture:** 保留 LangGraph StateGraph 作为核心编排框架。新增 Planner、Dependency-aware Dispatcher、Artifact Blackboard、Synthesizer、Verifier 等能力，在现有 `memory_agent -> supervisor -> dispatcher -> domain agents -> aggregator/error_handler` 基础上逐步演进为 `context -> planner -> task DAG scheduler -> parallel domain agents -> artifact store -> synthesizer -> verifier -> final`。

**Tech Stack:** LangGraph, FastAPI, Pydantic, asyncio, PostgreSQL/Redis memory, OpenTelemetry, pytest

---

## 背景与现状

当前系统已经具备 LangGraph 工作流骨架和 Search/RAG/Process 专业 Agent，但实现层面仍是中心化串行路由：

- `I3DWorkflow` 固定从 `memory_agent` 进入，再到 `supervisor`、`dispatcher`、专业 agent、`aggregator`。
- `supervisor_node` 每轮只创建一个 `SubTask`，复杂请求会被压缩为单一任务类型。
- `decide_next_agent` 只取第一个 pending/running task，未使用 `SubTask.dependencies`。
- `aggregator_node` 只按任务类型拼接模板，不做跨 Agent 综合推理、引用校验或冲突检测。
- `check_clarification_needed` 已存在，但工作流图未接入澄清回合。
- Process 任务的 supervisor 输入和 process node 期望字段不一致，存在真实执行失败风险。

本计划优先解决正确性和可测试性，再逐步提升协作效率。

---

## 目标架构

```
Chat API
  |
  v
Context Loader
  |
  v
Planner / Supervisor
  |    - intent classification
  |    - task decomposition
  |    - missing parameter detection
  |    - dependency graph creation
  v
Dependency-aware Dispatcher
  |    - ready task selection
  |    - parallel batch execution
  |    - retry/degrade policy
  v
Domain Agents
  |    - SearchAgent
  |    - RAGAgent
  |    - ProcessAgent
  v
Artifact Blackboard
  |    - normalized agent outputs
  |    - errors and partial results
  |    - provenance and confidence
  v
Synthesizer
  |
  v
Verifier
  |    - source coverage
  |    - contradiction check
  |    - missing parameter check
  v
Final Response
```

---

## 设计原则

1. **保留 LangGraph，不整体迁移框架。** 当前项目已有工作流、测试和 API 集成，重构应在现有图上增量演进。
2. **先修正确性，再做并行和智能化。** 澄清、Process 输入、错误降级等问题会直接影响生产稳定性。
3. **结构化状态优先。** Agent 之间通过 `SubTask`、`Artifact`、`TaskPlan` 共享数据，避免靠自然语言拼接中间结果。
4. **复杂请求走计划，简单请求走快速路径。** 保持单 search/rag/process 查询的低延迟。
5. **每个阶段必须配测试。** 路由、计划、调度、错误、澄清、综合输出都要有单测或集成测试覆盖。

---

## Phase 0: 基线确认与保护网

### Task 0.1: 固化当前工作流行为

**Files:**
- Test: `tests/test_workflow/test_graph.py`
- Test: `tests/test_workflow/test_conditions.py`
- Test: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 添加当前单意图路由测试**

覆盖：
- `搜索螺栓` -> search task
- `如何使用 API` -> rag task
- `查询任务状态` -> process task
- 普通问候 -> supervisor direct response

- [ ] **Step 2: 添加复杂意图失败/限制测试**

覆盖当前限制，作为后续重构前的基线：
- `搜索螺栓并告诉我 API 怎么用`
- `查询任务状态，然后根据文档解释失败原因`

Expected: 当前只能生成单个 task。测试命名应明确标注为 current behavior 或 limitation。

- [ ] **Step 3: 运行工作流测试**

```bash
pytest tests/test_workflow/ -v
```

### Task 0.2: 定义验收用例集

**Files:**
- Create: `tests/test_workflow/test_multi_agent_scenarios.py`

- [ ] **Step 1: 定义高价值场景**

至少包含：
- 单 Search 快速路径
- 单 RAG 快速路径
- 单 Process 快速路径
- Search + RAG 并行场景
- Process + RAG 依赖场景
- 缺少 task_id 触发澄清
- RAG 失败后部分降级
- Search 和 RAG 输出冲突时触发 verifier

- [ ] **Step 2: 先用 skipped 或 xfail 标记未来目标**

这些测试用于指导后续阶段，不要求 Phase 0 全部通过。

---

## Phase 1: 正确性修复

### Task 1.1: 修复 Process 任务输入解析

**Files:**
- Modify: `i3d_agent/workflow/nodes/supervisor.py`
- Modify: `i3d_agent/agents/supervisor.py`
- Modify: `i3d_agent/workflow/nodes/process_agent.py`
- Test: `tests/test_workflow/test_nodes.py`
- Test: `tests/test_agents/test_supervisor.py` or `i3d_agent/tests/test_agents/test_supervisor.py`

- [ ] **Step 1: 为 Process 意图补充结构化解析测试**

覆盖：
- `查询任务 task_123 状态` -> `input_data.task_id == "task_123"`
- `查询物料 BOLT001 处理历史` -> `input_data.item_code == "BOLT001"`
- `查询处理进度` -> 需要澄清

- [ ] **Step 2: 实现 Process 参数提取**

建议：
- 在 `SupervisorAgent` 中新增轻量解析函数，例如 `extract_process_params(query)`。
- 只做确定性解析，不要在此阶段引入 LLM planner。
- 无法提取时，创建 process task 并标记缺失字段，交给 process node 触发澄清。

- [ ] **Step 3: 调整 `process_agent_node`**

要求：
- 对缺少 `task_id` 和 `item_code` 的请求抛出 `NeedsClarificationError`，不要直接走 degradable error。
- 保留已有 `get_status` 和 `get_history` 行为。

- [ ] **Step 4: 运行相关测试**

```bash
pytest tests/test_workflow/test_nodes.py -v
pytest tests/test_workflow/test_graph.py -v
```

### Task 1.2: 接入澄清回合

**Files:**
- Modify: `i3d_agent/workflow/graph.py`
- Modify: `i3d_agent/workflow/conditions/routing.py`
- Modify: `i3d_agent/models/chat.py`
- Modify: `i3d_agent/api/routes/chat.py`
- Test: `tests/test_workflow/test_conditions.py`
- Test: `tests/test_workflow/test_graph.py`
- Test: `tests/test_api/test_chat.py`

- [ ] **Step 1: 明确澄清响应协议**

建议 `ChatResponse.metadata` 包含：

```python
{
    "needs_clarification": True,
    "task_id": "...",
    "question": "...",
    "options": [...]
}
```

- [ ] **Step 2: 图中接入澄清路由**

要求：
- Agent 设置 `pending_clarification` 后，不进入普通 aggregator。
- 返回澄清问题给前端/API。
- 下一轮用户回答能带回 `clarification_answer` 或通过 message 继续恢复任务。

- [ ] **Step 3: 增加会话恢复测试**

覆盖：
- 第一次请求触发澄清。
- 第二次请求携带澄清答案后，原 task 恢复为 pending 并继续执行。

### Task 1.3: 修复降级错误聚合

**Files:**
- Modify: `i3d_agent/workflow/nodes/error_handler.py`
- Modify: `i3d_agent/workflow/nodes/aggregator.py`
- Modify: `i3d_agent/workflow/state.py`
- Test: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 在状态中增加降级/错误摘要字段**

建议字段：
- `warnings: Optional[List[Dict[str, Any]]]`
- 或在 `metadata["warnings"]` 中统一保存。

- [ ] **Step 2: 避免 aggregator 覆盖 error_handler 已生成的降级提示**

要求：
- 有部分 completed task 时，正常聚合结果并附加 warning。
- 无 completed task 时，返回明确降级失败说明。

- [ ] **Step 3: 添加测试**

覆盖：
- RAG 失败但 Search 成功，最终响应保留 Search 结果和 RAG warning。
- 单任务失败且不可降级，最终直接 fail。

### Task 1.4: 统一状态和响应 schema

**Files:**
- Modify: `i3d_agent/workflow/state.py`
- Modify: `i3d_agent/models/chat.py`
- Modify: `i3d_agent/workflow/nodes/*.py`
- Test: `tests/test_workflow/test_state.py`
- Test: `tests/test_api/test_chat.py`

- [ ] **Step 1: 补齐 WorkflowState 可选字段**

建议新增：
- `task_plan`
- `artifacts`
- `warnings`
- `verification`
- `execution_trace`

- [ ] **Step 2: 确保所有节点只写自己负责的字段**

要求：
- domain agent 只更新 task 和 artifact。
- synthesizer/aggregator 负责 response。
- error_handler 负责 warnings/error policy。

---

## Phase 2: Planner 和多任务拆解

### Task 2.1: 定义 TaskPlan 模型

**Files:**
- Modify: `i3d_agent/workflow/state.py`
- Create: `i3d_agent/workflow/planner.py`
- Test: `tests/test_workflow/test_state.py`
- Test: `tests/test_workflow/test_planner.py`

- [ ] **Step 1: 添加模型测试**

建议模型：

```python
class TaskPlan(BaseModel):
    plan_id: str
    query: str
    intent_types: list[str]
    tasks: list[SubTask]
    missing_slots: list[dict[str, Any]]
    can_parallelize: bool
    confidence: float
```

- [ ] **Step 2: 扩展 SubTask 字段**

建议字段：
- `priority: int = 0`
- `required_artifacts: list[str] = []`
- `produces: list[str] = []`
- `confidence: Optional[float] = None`
- `created_by: str = "planner"`

- [ ] **Step 3: 保持向后兼容**

现有单任务测试必须继续通过。

### Task 2.2: 从关键词 Router 升级为 Planner

**Files:**
- Modify: `i3d_agent/workflow/nodes/supervisor.py`
- Modify: `i3d_agent/agents/supervisor.py`
- Create: `i3d_agent/workflow/planner.py`
- Test: `tests/test_workflow/test_planner.py`
- Test: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 实现确定性 planner v1**

先不依赖 LLM，使用规则识别多意图：
- search keywords -> search task
- rag keywords -> rag task
- process keywords -> process task
- connectors: `并`, `然后`, `同时`, `再`, `顺便`

- [ ] **Step 2: 复杂请求生成多个 SubTask**

示例：
- `搜索螺栓并告诉我 API 怎么用` -> search + rag
- `查询 task_123 状态并解释失败原因` -> process + rag，其中 rag 依赖 process 输出

- [ ] **Step 3: 建立依赖规则**

建议：
- Search + RAG 一般可并行。
- Process 状态结果用于后续解释时，RAG 依赖 Process。
- 需要用户补充 slot 的 task 不进入 ready 队列。

- [ ] **Step 4: 保留 general direct response**

普通问候、帮助类问题仍允许 supervisor 直接回答。

### Task 2.3: 可选 LLM Planner

**Files:**
- Modify: `i3d_agent/workflow/planner.py`
- Modify: `i3d_agent/config/settings.py`
- Test: `tests/test_workflow/test_planner.py`

- [ ] **Step 1: 增加配置开关**

建议：
- `ENABLE_LLM_PLANNER=false`
- `LLM_PLANNER_TIMEOUT_SECONDS=3`

- [ ] **Step 2: 使用结构化输出**

要求：
- LLM planner 只输出 JSON。
- JSON 必须经过 Pydantic 校验。
- 校验失败回退 deterministic planner。

- [ ] **Step 3: 增加失败回退测试**

覆盖：
- LLM 返回非法 JSON。
- LLM 超时。
- LLM 返回不支持的 task type。

---

## Phase 3: 依赖感知调度和并行执行

### Task 3.1: 实现 ready task 选择器

**Files:**
- Modify: `i3d_agent/workflow/conditions/routing.py`
- Modify: `i3d_agent/workflow/utils.py`
- Test: `tests/test_workflow/test_conditions.py`

- [ ] **Step 1: 实现 `get_ready_tasks(tasks)`**

规则：
- task.status == pending
- 所有 dependencies 已 completed
- 无 pending clarification
- 未超过 retry limit

- [ ] **Step 2: 保留 `get_next_pending_task` 兼容旧测试**

旧函数可继续存在，但 dispatcher 应优先使用 ready task。

### Task 3.2: 引入并行执行节点

**Files:**
- Modify: `i3d_agent/workflow/graph.py`
- Create: `i3d_agent/workflow/nodes/parallel_executor.py`
- Test: `tests/test_workflow/test_graph.py`
- Test: `tests/test_workflow/test_multi_agent_scenarios.py`

- [ ] **Step 1: 创建 `parallel_executor_node`**

职责：
- 找出当前 ready tasks。
- 对不同 domain agent 调用对应执行函数。
- 使用 `asyncio.gather(..., return_exceptions=True)` 执行独立任务。
- 将结果写回对应 task 和 artifacts。

- [ ] **Step 2: 控制并发上限**

建议配置：
- `MAX_PARALLEL_AGENT_TASKS=3`
- 对外部服务调用保留 timeout。

- [ ] **Step 3: 图中接入 parallel executor**

建议路径：
- supervisor -> dispatcher
- dispatcher 如果 ready tasks 数量 > 1 -> parallel_executor
- dispatcher 如果 ready tasks 数量 == 1 -> 原单 agent 节点

- [ ] **Step 4: 测试并行节省耗时**

用 mock agent sleep 验证两个独立任务并行执行，总耗时应接近 max(task durations)，不是 sum(task durations)。

### Task 3.3: 防止任务循环和重复执行

**Files:**
- Modify: `i3d_agent/workflow/state.py`
- Modify: `i3d_agent/workflow/utils.py`
- Test: `tests/test_workflow/test_conditions.py`

- [ ] **Step 1: 增加执行轮次限制**

建议：
- `max_iterations`
- `iteration_count`

- [ ] **Step 2: 对重复 running task 做保护**

要求：
- task 被执行前状态从 pending -> running。
- 执行完成后只能进入 completed/failed/needs_clarification。
- running 超时可被 error_handler 重置。

---

## Phase 4: Artifact Blackboard

### Task 4.1: 定义 Artifact 模型

**Files:**
- Modify: `i3d_agent/workflow/state.py`
- Test: `tests/test_workflow/test_state.py`

- [ ] **Step 1: 添加 Artifact 模型**

建议：

```python
class Artifact(BaseModel):
    artifact_id: str
    task_id: str
    artifact_type: Literal["search_results", "rag_answer", "process_status", "warning", "verification"]
    content: dict[str, Any]
    provenance: dict[str, Any] = {}
    confidence: Optional[float] = None
```

- [ ] **Step 2: WorkflowState 添加 artifacts**

```python
artifacts: List[Artifact]
```

### Task 4.2: Domain Agent 输出标准化

**Files:**
- Modify: `i3d_agent/workflow/nodes/search_agent.py`
- Modify: `i3d_agent/workflow/nodes/rag_agent.py`
- Modify: `i3d_agent/workflow/nodes/process_agent.py`
- Test: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: Search 输出 `search_results` artifact**

内容包含：
- results
- count
- search_type
- query
- tenant_id

- [ ] **Step 2: RAG 输出 `rag_answer` artifact**

内容包含：
- answer
- sources
- source_count
- retrieval metadata

- [ ] **Step 3: Process 输出 `process_status` artifact**

内容包含：
- status
- progress
- task_id or item_code
- history/details

- [ ] **Step 4: aggregator 暂时兼容 task.output_data 和 artifacts**

迁移期间两种数据源都要可用，避免一次性破坏现有功能。

---

## Phase 5: Synthesizer 和 Verifier

### Task 5.1: 将 aggregator 升级为 Synthesizer

**Files:**
- Rename or Modify: `i3d_agent/workflow/nodes/aggregator.py`
- Optional Create: `i3d_agent/workflow/nodes/synthesizer.py`
- Test: `tests/test_workflow/test_nodes.py`
- Test: `tests/test_workflow/test_multi_agent_scenarios.py`

- [ ] **Step 1: 定义综合策略**

要求：
- 单 Search: 保持简洁结果列表。
- 单 RAG: 返回答案和来源。
- Search + RAG: 先给结论，再列搜索结果，再补充文档依据。
- Process + RAG: 先给状态，再解释含义和处理建议。
- 有 warning: 在答案末尾说明部分服务不可用。

- [ ] **Step 2: 结构化 sources**

确保 RAG sources 进入 `ChatResponse.sources`，Search 结果不要伪装成 RAG source。

- [ ] **Step 3: 生成 execution summary**

`thought_process` 不暴露详细链式推理，只描述执行路径：
- `已并行执行搜索和文档检索`
- `已先查询任务状态，再根据文档生成解释`

### Task 5.2: 增加 Verifier 节点

**Files:**
- Create: `i3d_agent/workflow/nodes/verifier.py`
- Modify: `i3d_agent/workflow/graph.py`
- Test: `tests/test_workflow/test_nodes.py`
- Test: `tests/test_workflow/test_graph.py`

- [ ] **Step 1: 定义 VerificationResult**

建议字段：
- `passed: bool`
- `issues: list[dict[str, Any]]`
- `requires_clarification: bool`
- `requires_retry: bool`
- `confidence: float`

- [ ] **Step 2: 实现规则 verifier v1**

检查：
- RAG 有答案但 sources 为空时 warning。
- 用户要求状态但无 process artifact 时 fail 或 clarification。
- Search 结果为空时提示无结果，不编造。
- 多个 artifact 内容冲突时标注 issue。

- [ ] **Step 3: 图中接入 verifier**

建议：
- synthesizer -> verifier
- verifier passed -> END
- verifier requires_clarification -> clarification response
- verifier requires_retry -> dispatcher 或 error_handler

### Task 5.3: 可选 LLM Verifier

**Files:**
- Modify: `i3d_agent/workflow/nodes/verifier.py`
- Modify: `i3d_agent/config/settings.py`
- Test: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 增加配置开关**

建议：
- `ENABLE_LLM_VERIFIER=false`

- [ ] **Step 2: 只在高风险场景启用**

例如：
- 多 artifact 综合
- RAG source 低置信度
- 用户要求严格依据文档

---

## Phase 6: 记忆、上下文和 Handoff

### Task 6.1: 明确记忆分层

**Files:**
- Modify: `i3d_agent/workflow/nodes/memory_agent.py`
- Modify: `i3d_agent/memory/manager.py`
- Test: `tests/test_memory/test_manager.py`
- Test: `tests/test_workflow/test_nodes.py`

- [ ] **Step 1: 区分四类上下文**

建议：
- `conversation_history`: 对话历史。
- `session_state`: 当前会话 task plan 和 pending clarification。
- `user_preferences`: 用户偏好。
- `artifacts`: 当前请求产物，不长期保存，必要时摘要保存。

- [ ] **Step 2: 保存关键会话状态**

要求：
- pending clarification 能跨请求恢复。
- 最近一次 task plan 可追踪。

### Task 6.2: 引入专业 Agent Handoff 模式

**Files:**
- Modify: `i3d_agent/workflow/state.py`
- Modify: `i3d_agent/workflow/nodes/supervisor.py`
- Modify: `i3d_agent/workflow/conditions/routing.py`
- Test: `tests/test_workflow/test_graph.py`

- [ ] **Step 1: 添加 active_agent 字段**

建议：
- `active_agent: Optional[str]`
- `handoff_reason: Optional[str]`
- `handoff_turns_remaining: int`

- [ ] **Step 2: 定义 handoff 条件**

示例：
- 用户连续追问文档细节 -> handoff to rag_agent。
- 用户连续追问任务状态/失败处理 -> handoff to process_agent。

- [ ] **Step 3: 定义退出条件**

示例：
- 用户切换意图。
- handoff turns 用尽。
- 专业 agent 请求 supervisor 重新规划。

---

## Phase 7: 可观测性、评估和性能

### Task 7.1: 增加执行追踪指标

**Files:**
- Modify: `i3d_agent/utils/telemetry.py`
- Modify: `i3d_agent/workflow/utils.py`
- Modify: `i3d_agent/workflow/graph.py`
- Test: `tests/test_workflow/test_graph.py`

- [ ] **Step 1: 记录核心指标**

建议：
- `planner.task_count`
- `planner.confidence`
- `dispatcher.ready_task_count`
- `dispatcher.parallel_batch_size`
- `agent.duration`
- `agent.success/failure`
- `synthesizer.artifact_count`
- `verifier.passed`

- [ ] **Step 2: 日志中加入 plan_id 和 task_id**

要求后续问题可从一次请求追踪到每个子任务。

### Task 7.2: 建立评估集

**Files:**
- Create: `tests/evals/multi_agent_cases.yaml`
- Create: `tests/test_workflow/test_multi_agent_eval.py`

- [ ] **Step 1: 定义离线 case**

每条包含：
- query
- expected task types
- expected dependencies
- expected response traits
- expected sources required

- [ ] **Step 2: 编写评估测试**

先做 deterministic eval，不调用真实外部服务。

### Task 7.3: 性能预算

**Files:**
- Modify: `i3d_agent/config/settings.py`
- Test: `tests/test_workflow/test_graph.py`

- [ ] **Step 1: 配置 timeout**

建议：
- planner timeout
- agent timeout
- verifier timeout
- total workflow timeout

- [ ] **Step 2: 配置并发限制**

确保不会对外部 Search/RAG/Process 服务造成突刺流量。

---

## 验收标准

- [ ] 单 Search/RAG/Process 快速路径保持可用，响应格式不破坏前端。
- [ ] Process 查询能正确区分 `task_id`、`item_code` 和缺参澄清。
- [ ] 缺参请求能返回澄清问题，用户补充后能继续原任务。
- [ ] 复杂请求能生成多个 `SubTask`，并正确设置依赖。
- [ ] 无依赖的多任务可以并行执行。
- [ ] 有依赖的任务按 DAG 顺序执行。
- [ ] 部分 Agent 失败时能保留已完成结果和 warning。
- [ ] Synthesizer 能根据 artifact 生成统一答案，而不是简单拼接。
- [ ] Verifier 能发现缺来源、无结果、缺状态等基础质量问题。
- [ ] 工作流日志能追踪 request_id、plan_id、task_id、agent duration。
- [ ] `pytest tests/test_workflow/ -v` 通过。
- [ ] `pytest tests/test_api/ -v` 通过。

---

## 风险与回滚

### 风险 1: Planner 引入后简单请求变慢

缓解：
- 保留 deterministic fast path。
- LLM planner 默认关闭。
- 对单意图高置信请求直接生成单 task。

### 风险 2: 并行执行导致外部服务压力增加

缓解：
- 设置 `MAX_PARALLEL_AGENT_TASKS`。
- 对每类外部服务设置 timeout 和 semaphore。
- 默认最多并行 Search/RAG/Process 各一个。

### 风险 3: 状态 schema 变更影响前端

缓解：
- `ChatResponse.response/sources/thought_process/session_id/metadata` 保持兼容。
- 新字段放入 metadata 或可选字段。
- 前端改造单独计划处理。

### 风险 4: Verifier 过严导致正常请求被阻断

缓解：
- 规则 verifier 默认只添加 warning，不直接阻断。
- 只有缺少必要用户参数或明确无法回答时才触发 clarification/fail。

### 回滚策略

- 每个 Phase 独立提交。
- Phase 2 以后新增配置开关：
  - `ENABLE_TASK_PLANNER`
  - `ENABLE_PARALLEL_EXECUTION`
  - `ENABLE_ARTIFACT_BLACKBOARD`
  - `ENABLE_VERIFIER`
- 如线上异常，可关闭新能力退回当前单任务串行路径。

---

## 推荐实施顺序

1. Phase 0: 先补测试基线。
2. Phase 1: 修 Process、clarification、degrade 和 schema。
3. Phase 2: 上 deterministic planner，支持多任务拆解。
4. Phase 3: 做依赖调度和并行执行。
5. Phase 4: 引入 artifact blackboard。
6. Phase 5: 升级 synthesizer/verifier。
7. Phase 6-7: 做 handoff、记忆分层、观测和评估。

Phase 1-3 完成后，系统协作效率会有明显提升；Phase 4-5 完成后，系统才算从“多 Agent 路由器”升级为“多 Agent 协作系统”。

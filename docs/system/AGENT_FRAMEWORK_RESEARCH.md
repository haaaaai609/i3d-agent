# Agent 框架调研报告 - 针对 I3D 系统

> 调研时间: 2026-05-26
> 目的: 为 I3D 3D CAD 智能检索系统选择合适的 Agent 框架，支持多 Agent 协作 + RAG 知识库问答

---

## 一、主流 Agent 框架对比 (2025-2026)

### 1.1 市场地位概览

根据 Langfuse 2026 年框架对比数据：

| 框架 | 月搜索量 | 背后支持 | 定位 |
|------|---------|---------|------|
| **LangGraph** | 27,100 | LangChain | 复杂工作流与状态管理 |
| **CrewAI** | 14,800 | 开源社区 | 快速原型与团队协作 |
| **AutoGen** | 强劲 | Microsoft | 企业级对话系统 |
| **OpenAI Swarm** | 新兴 | OpenAI | 轻量级教育与实验 |

---

## 二、框架详细分析

### 2.1 LangGraph (LangChain)

**官网**: [https://github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)

#### 核心特点
- **状态图架构**: 基于有向图的 Agent 编排，支持循环和条件分支
- **精细控制**: 最大程度的 Agent 交互控制能力
- **生产级**: 专为生产环境设计，具备完善的错误处理和状态恢复

#### 技术优势
```
优势项:
├── 复杂工作流支持 - 支持多层嵌套和循环
├── 状态管理 - 内置持久化和检查点机制
├── RAG 集成 - 与 LangChain 生态无缝集成
├── 可观测性 - LangSmith 全链路追踪
└── 生产验证 - 大量生产部署案例

劣势项:
├── 学习曲线陡峭 - 需要深入理解图编程范式
└── 配置复杂 - 初始设置较为繁琐
```

#### 适用场景
- 复杂的多步骤推理任务
- 需要精确控制 Agent 交互的生产系统
- 集成 RAG 的检索增强生成

#### 代码示例
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    next_agent: str

def search_node(state: AgentState):
    # 3D 搜索逻辑
    results = search_3d_model(state["messages"][-1])
    return {"messages": results}

def rag_node(state: AgentState):
    # RAG 知识库查询
    context = retrieve_from_kb(state["messages"][-1])
    return {"messages": context}

# 构建状态图
workflow = StateGraph(AgentState)
workflow.add_node("search", search_node)
workflow.add_node("rag", rag_node)
workflow.add_conditional_edges("search", should_call_rag, {True: "rag", False: END})
workflow.set_entry_point("search")
app = workflow.compile()
```

---

### 2.2 CrewAI

**官网**: [https://github.com/joaomdmoura/crewAI](https://github.com/joaomdmoura/crewAI)

#### 核心特点
- **角色导向**: 基于角色和任务的 Agent 团队协作
- **最低学习曲线**: 三大框架中最易上手
- **快速原型**: 适合 MVP 和概念验证

#### 技术优势
```
优势项:
├── 极简API - 几行代码即可启动多Agent
├── 角色定义清晰 - 通过role/goal/story描述Agent
├── 任务编排 - 简单的任务依赖关系管理
├── 工具集成 - 丰富的预置工具库
└── 社区活跃 - 快速增长的生态系统

劣势项:
├── 控制粒度有限 - 难以处理复杂状态逻辑
└── 生产案例较少 - 企业级部署经验相对不足
```

#### 适用场景
- 快速原型开发
- 简单的团队协作型 Agent
- 概念验证项目

#### 代码示例
```python
from crewai import Agent, Task, Crew

# 定义搜索专家 Agent
search_agent = Agent(
    role="3D模型搜索专家",
    goal="帮助用户找到相似的CAD模型",
    backstory="你精通3D模型特征提取和相似度搜索",
    tools=[search_3d_tool, search_2d_tool]
)

# 定义知识库 Agent
rag_agent = Agent(
    role="CAD知识库专家",
    goal="从技术文档中回答CAD相关问题",
    backstory="你熟悉CAD软件操作和最佳实践",
    tools=[rag_search_tool]
)

# 定义任务
search_task = Task(
    description="搜索与用户输入相似的3D模型",
    agent=search_agent
)

rag_task = Task(
    description="从知识库中检索相关技术文档",
    agent=rag_agent
)

# 组装团队
crew = Crew(
    agents=[search_agent, rag_agent],
    tasks=[search_task, rag_task],
    verbose=True
)
```

---

### 2.3 AutoGen (Microsoft)

**官网**: [https://github.com/microsoft/autogen](https://github.com/microsoft/autogen)

#### 核心特点
- **对话式架构**: 基于 Agent 间对话模式
- **企业级支持**: Microsoft 官方维护
- **灵活性强**: 支持多种对话模式

#### 技术优势
```
优势项:
├── Microsoft背书 - 企业级支持可靠
├── 对话模式丰富 - 支持单轮、多轮、群聊
├── 代码执行 - 内置代码解释器
├── 可扩展性 - 良好的扩展机制
└── 生态集成 - 与Azure服务深度集成

劣势项:
├── 中等学习曲线 - 需要理解对话模式设计
└── 抽象层次较高 - 某些场景控制不够精细
```

#### 适用场景
- 企业级应用部署
- 需要 Microsoft 生态集成
- 代码生成和执行场景

#### 代码示例
```python
import autogen

config_list = [{"model": "gpt-4", "api_key": "..."}]

# 定义搜索助手
search_assistant = autogen.AssistantAgent(
    name="search_assistant",
    llm_config={"config_list": config_list},
    system_message="你是3D模型搜索专家，帮助用户查找相似模型"
)

# 定义用户代理
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={"work_dir": "coding"}
)

# 启动对话
user_proxy.initiate_chat(
    search_assistant,
    message="帮我找一个和这个螺栓相似的零件"
)
```

---

### 2.4 OpenAI Swarm

**官网**: [https://github.com/openai/swarm](https://github.com/openai/swarm)

#### 核心特点
- **超轻量级**: 专注最小化编排开销
- **教育性质**: OpenAI 官方实验性项目
- **客户端执行**: 几乎无服务器依赖

#### 技术优势
```
优势项:
├── 极简设计 - 核心代码量少
├── Agent交接 - 无缝的Agent切换机制
├── 易于测试 - 纯客户端执行
└── 学习友好 - 适合理解多Agent基础

劣势项:
├── 实验性质 - 不承诺生产稳定性
├── 功能有限 - 缺乏高级特性
└── 支持较少 - 官方维护力度有限
```

#### 适用场景
- 学习多 Agent 基础概念
- 轻量级原型验证
- 不推荐用于生产环境

---

### 2.5 Microsoft GraphRAG

**官网**: [https://github.com/microsoft/graphrag](https://github.com/microsoft/graphrag)

#### 核心特点
- **知识图谱增强**: 将 RAG 与知识图谱结合
- **层次化社区**: 自动构建文档社区层次结构
- **全局理解**: 支持全数据集级语义理解

#### 技术优势
```
优势项:
├── 知识图谱 - 构建实体关系网络
├── 层次化摘要 - 社区级文档摘要
├── 全局查询 - 支持数据集级别问题
├── Microsoft支持 - 研究级项目
└── 开源可用 - 完全开源

劣势项:
├── 复杂度高 - 需要图谱构建和存储
└── 资源消耗 - 图处理计算密集
```

#### 适用场景
- 复杂推理任务
- 需要理解实体关系的领域
- 全局性数据分析

---

## 三、RAG 框架对比

### 3.1 主流 RAG 框架

| 框架 | 特点 | 适用场景 |
|------|------|---------|
| **LangChain** | 生态最完善 | 通用 RAG 应用 |
| **LlamaIndex** | 数据连接器强 | 复杂检索策略 |
| **Haystack** | 生产级管道 | 企业部署 |
| **GraphRAG** | 知识图谱增强 | 复杂推理 |

### 3.2 2025-2026 RAG 最佳实践

```yaml
架构模式:
  - Agentic RAG: Agent + 工具调用 + 多轮检索
  - Hybrid Search: 向量搜索 + BM25 关键词
  - Recursive Retrieval: 多级文档层次
  - Modular RAG: 模块化组件分离

知识库设计:
  - 智能分块: 语义分块 + 固定大小重叠
  - 元数据丰富: 支持过滤和精准检索
  - 多模态支持: 文本、图像、表格、代码
  - 版本控制: 文档变更追踪

检索优化:
  - 查询重写: 扩展和改写用户查询
  - 重排序: Cross-encoder 二次排序
  - 语义缓存: 相似查询结果复用
  - 引用归因: 响应源文档链接

评估与质量:
  - RAGAS: 自动化评估指标
  - TruLens: RAG 专项评估
  - Human-in-the-loop: 人工反馈循环
  - A/B 测试: 检索策略对比
```

---

## 四、针对 I3D 系统的推荐方案

### 4.1 系统特点分析

I3D 系统具有以下特点：
```
├── 微服务架构 - 5 个独立服务协作
├── 多租户隔离 - PostgreSQL RLS + MinIO Bucket隔离
├── 3D 领域专业 - CAD 文件处理与检索
├── 现有向量存储 - pgvector 已集成
├── Python 技术栈 - Django 后端
└── 桌面客户端 - Electron + Vue3 前端
```

### 4.2 推荐方案组合

#### 方案 A: LangGraph + LangChain (推荐用于生产)

```yaml
优势:
  - 状态图完美匹配多服务编排需求
  - 与现有 Django/Python 生态兼容
  - LangSmith 可观测性支持
  - RAG 集成成熟

适用场景:
  - 复杂的多服务工作流编排
  - 需要精细控制 Agent 交互
  - 生产级部署要求

架构设计:
  - LangGraph 编排层: 协调 5 个微服务
  - LangChain RAG 层: 技术文档知识库
  - pgvector: 现有向量存储复用
  - Django 集成: 通过 REST API 调用
```

#### 方案 B: CrewAI + LangChain (推荐用于快速原型)

```yaml
优势:
  - 快速上手，缩短开发周期
  - 角色导向适合业务场景建模
  - 轻松添加新的 Agent 角色

适用场景:
  - MVP 快速验证
  - 概念原型开发
  - 简单协作场景

架构设计:
  - CrewAI Agent 团队: 搜索专家、知识库专家、处理专家
  - LangChain RAG: 文档检索
  - 工具层: 包装现有 API
```

#### 方案 C: GraphRAG + LangGraph (推荐用于复杂推理)

```yaml
优势:
  - 知识图谱增强 CAD 领域推理
  - 层次化理解 3D 模型关系
  - 全局性查询支持

适用场景:
  - 需要理解模型间关系
  - 复杂推理任务
  - 领域知识深度集成

架构设计:
  - GraphRAG: 构建 CAD 零件关系图谱
  - LangGraph: 编排复杂推理流程
  - Neo4j/Memgraph: 知识图谱存储
  - pgvector: 向量检索
```

### 4.3 最终推荐

**生产环境**: **LangGraph + LangChain**

理由：
1. LangGraph 的状态图架构天然适合协调 I3D 的 5 个微服务
2. 现有 Python/Django 技术栈无缝集成
3. 生产级可靠性和可观测性
4. 成熟的 RAG 生态支持
5. 可以复用现有 pgvector 基础设施

**快速验证**: **CrewAI**

理由：
1. 快速验证 Agent 协作价值
2. 低成本试错
3. 可后续迁移到 LangGraph

---

## 五、下一步工作

### 5.1 技术验证
- [ ] LangGraph + Django 集成 PoC
- [ ] RAG 知识库构建（技术文档）
- [ ] Agent 工具封装（现有 API）
- [ ] pgvector 向量检索集成

### 5.2 架构设计
- [ ] Agent 编排层设计
- [ ] 知识库架构设计
- [ ] 多租户隔离方案
- [ ] 可观测性方案

### 5.3 实施计划
- [ ] 第一阶段: 单 Agent + RAG 问答
- [ ] 第二阶段: 多 Agent 协作
- [ ] 第三阶段: 生产级部署

---

## 六、参考资源

### 官方文档
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [CrewAI](https://github.com/joaomdmoura/crewAI)
- [AutoGen](https://github.com/microsoft/autogen)
- [OpenAI Swarm](https://github.com/openai/swarm)
- [GraphRAG](https://github.com/microsoft/graphrag)

### 社区资源
- [Alice Labs - Best AI Agent Frameworks 2026](https://alicelabs.ai/en/insights/best-ai-agent-frameworks-2026)
- [LangGraph vs CrewAI vs AutoGen](https://pecollective.com/blog/ai-agent-frameworks-compared/)
- [GraphRAG Official Docs](https://microsoft.github.io/graphrag/)

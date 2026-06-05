# I3D Agent System - RAG 模块设计文档

> **文档版本**: 1.1
> **创建日期**: 2026-06-01
> **更新日期**: 2026-06-05
> **状态**: 已实现，架构重构完成

---

## 1. 概述

### 1.1 背景

I3D Agent System 是一个智能多代理系统，用于 3D CAD 模型搜索、数据处理和技术文档问答。RAG（Retrieval-Augmented Generation）模块是系统的核心组件之一，负责技术文档和业务文档的检索与问答。

### 1.2 设计目标

- **混合文档支持**：同时支持技术文档（API 文档、部署指南）和业务文档（产品规格、处理记录）
- **增量索引**：新文档加入后无需全量重建，支持高时效性更新
- **Agentic RAG**：多步推理、查询扩展、HyDE、重排序等高级特性
- **混合检索**：向量检索 + BM25 全文检索
- **版本管理**：文档更新历史追踪和回滚
- **监控仪表板**：检索性能指标、索引状态、质量监控

### 1.3 现有基础设施

- PostgreSQL + pgvector（向量数据库）
- Redis 缓存
- 多 Agent 架构（Supervisor、Search、RAG、Process）
- LangGraph 工作流
- 租户隔离架构
- OpenTelemetry 可观测性
- DashScope LLM（qwen-plus）

---

## 2. 整体架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      LangGraph 工作流                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Supervisor│───→│  RAG     │───→│  Search  │───→│ Process  │  │
│  │  Agent   │    │  Agent   │    │  Agent   │    │  Agent   │  │
│  └──────────┘    └────┬─────┘    └──────────┘    └──────────┘  │
│                      │                                         │
│              ┌───────▼────────┐                               │
│              │  Aggregation   │                               │
│              │     Node       │                               │
│              └────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ 调用
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        RAG 模块（重构后）                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              RAG Agent (i3d_agent/agents/rag.py)        │   │
│  │  ┌──────────────────────────────────────────────────────┐ │   │
│  │  │  answer()                                            │ │   │
│  │  │    ├─> controller.retrieve()  ← 委托给 Controller     │ │   │
│  │  │    ├─> _build_context()                             │ │   │
│  │  │    └─> _generate_answer()  ← LLM 生成答案          │ │   │
│  │  └──────────────────────────────────────────────────────┘ │   │
│  └────────────────────────────┬─────────────────────────────┘   │
│                               │                                  │
│                               ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │     AgenticRAGController (i3d_agent/rag/controller.py)  │   │
│  │  ┌──────────────────────────────────────────────────────┐ │   │
│  │  │  retrieve() / retrieve_with_multi_step()           │ │   │
│  │  │    ├─> QueryExpansionService (查询扩展)              │ │   │
│  │  │    ├─> HyDEService (假设文档生成)                    │ │   │
│  │  │    ├─> RetrievalEngine.hybrid_retrieval()           │ │   │
│  │  │    │   ├─> vector_search()  ← HNSW + pgvector       │ │   │
│  │  │    │   └─> bm25_search()    ← PostgreSQL tsvector   │ │   │
│  │  │    ├─> _deduplicate_and_merge()                     │ │   │
│  │  │    ├─> RerankService.rerank()                        │ │   │
│  │  │    └─> _assess_quality() / _rewrite_query()          │ │   │
│  │  └──────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    其他 RAG 组件                          │   │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │   │
│  │  │ Document    │   │   Version   │   │  Monitor    │     │   │
│  │  │   Manager   │   │  Control    │   │   Service   │     │   │
│  │  └─────────────┘   └─────────────┘   └─────────────┘     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ 存储
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL + pgvector                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │rag_documents │  │rag_chunks    │  │rag_versions   │          │
│  │   (元数据)    │  │  (向量+内容)  │  │  (版本历史)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │rag_index_queue│ │rag_metrics   │  │rag_feedback   │          │
│  │ (增量索引队列) │  │ (性能指标)    │  │ (质量反馈)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1.1 重构说明 (2026-06-05)

**重构前问题**：
- RAGAgent 直接管理 RetrievalEngine 和 RerankService
- 与 AgenticRAGController 功能重叠，代码冗余
- Workflow 路径和 API 路径使用不同组件，架构不一致

**重构后架构**：
- RAGAgent 简化为 AgenticRAGController 的包装器
- 职责明确划分：
  - **AgenticRAGController**：负责所有检索逻辑（查询扩展、HyDE、混合检索、重排序、多步推理）
  - **RAGAgent**：负责答案生成（使用 LLM）
- 统一架构：API 层和 Workflow 层都使用 AgenticRAGController 进行检索

**重构效果**：
| 方面 | 重构前 | 重构后 |
|------|--------|--------|
| 代码行数 (RAGAgent) | ~150 行 | ~70 行 |
| 直接依赖 | RetrievalEngine, RerankService | AgenticRAGController |
| 高级能力 | 未启用 | 已启用（查询扩展、HyDE、多步推理） |
| 架构一致性 | 不一致 | 一致 |

### 2.2 组件职责

| 组件 | 文件位置 | 职责 | LLM 用途 |
|------|----------|------|----------|
| **RAGAgent** | `agents/rag.py` | 答案生成，调用 AgenticRAGController | 生成最终答案 |
| **AgenticRAGController** | `rag/controller.py` | 检索编排，协调所有检索组件 | 查询重写 |
| **QueryExpansionService** | `rag/query_expansion.py` | 查询扩展，生成多种表述 | 生成查询变体 |
| **HyDEService** | `rag/hyde.py` | 假设文档生成 | 生成假设文档 |
| **RetrievalEngine** | `rag/retrieval.py` | 混合检索（向量 + BM25） | - |
| **RerankService** | `rag/rerank.py` | 重排序精排 | 外部 Rerank API |
| **EmbeddingService** | `rag/embedding.py` | 向量嵌入生成 | 外部 Embedding API |
| **DocumentManager** | `rag/document_manager.py` | CRUD 操作、版本管理 | - |
| **MonitorService** | `rag/monitor.py` | 性能监控、质量追踪 | - |

### 2.3 项目结构

```
i3d_agent/
├── rag/                          # RAG 模块
│   ├── __init__.py
│   ├── controller.py             # Agentic RAG 控制器
│   ├── document_manager.py       # 文档管理器
│   ├── processor.py              # 文档处理器（切分、embedding）
│   ├── retrieval.py              # 检索引擎
│   ├── rerank.py                 # 重排序服务
│   ├── hyde.py                   # HyDE 实现
│   ├── query_expansion.py        # 查询扩展
│   ├── monitor.py                # 监控服务
│   ├── index_worker.py           # 索引 Worker
│   └── models.py                 # RAG 数据模型
│
├── agents/
│   ├── rag.py                    # RAG Agent
│   └── ...
│
├── tools/
│   ├── rag_tools.py              # RAG 工具
│   └── ...
│
└── config/
    └── settings.py               # 配置
```

---

## 2.3 架构重构详解 (2026-06-05)

### 2.3.1 重构动机

**冗余问题**：
```
┌─────────────────────────────────────────────────────────────────┐
│                        重构前（存在冗余）                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RAGAgent (agents/rag.py)                                       │
│  ├─ self.retrieval_engine = RetrievalEngine()                   │
│  ├─ self.rerank_service = RerankService()                       │
│  └─ answer():                                                   │
│      ├─> hybrid_retrieval()                                     │
│      ├─> rerank()                                               │
│      └─> generate_answer()                                      │
│                                                                  │
│  AgenticRAGController (rag/controller.py)                        │
│  ├─ self.retrieval_engine = RetrievalEngine()                   │
│  ├─ self.rerank_service = RerankService()                       │
│  └─ retrieve():                                                 │
│      ├─> query_expansion                                        │
│      ├─> hyde                                                  │
│      ├─> hybrid_retrieval()                                     │
│      ├─> rerank()                                               │
│      └─> quality_assessment                                     │
│                                                                  │
│  问题：两者都初始化 RetrievalEngine 和 RerankService，功能重叠    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3.2 重构后架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        重构后（职责清晰）                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RAGAgent (agents/rag.py)                                       │
│  ├─ self.controller = AgenticRAGController(...)                  │
│  └─ answer():                                                   │
│      ├─> controller.retrieve()  ← 委托检索                       │
│      ├─> _build_context()                                       │
│      └─> _generate_answer()  ← 专注答案生成                      │
│                                                                  │
│  AgenticRAGController (rag/controller.py)                        │
│  ├─ self.retrieval_engine = RetrievalEngine()                   │
│  ├─ self.rerank_service = RerankService()                       │
│  ├─ self.query_expansion = QueryExpansionService()              │
│  ├─ self.hyde_service = HyDEService()                           │
│  └─ retrieve():                                                 │
│      ├─> query_expansion  ← 新增能力                            │
│      ├─> hyde            ← 新增能力                            │
│      ├─> hybrid_retrieval                                       │
│      ├─> rerank                                                 │
│      └─> quality_assessment  ← 新增能力                        │
│                                                                  │
│  优势：                                                          │
│  - 消除代码冗余                                                 │
│  - 职责清晰分离                                                  │
│  - RAGAgent 自动获得高级能力                                      │
│  - 架构统一（API 和 Workflow 都用同一套）                        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3.3 重构代码对比

**重构前 RAGAgent.answer()**：
```python
async def answer(self, question, tenant_id=None, top_k=5, enable_rerank=True):
    # 生成向量
    embedding_service = EmbeddingService()
    query_vector = await embedding_service.embed_text(question)

    # 检索
    search_type = self.retrieval_engine.classify_query(question)
    results = await self.retrieval_engine.hybrid_retrieval(...)

    # 重排序
    if enable_rerank:
        results = await self.rerank_service.rerank(...)

    # 生成答案
    context = self._build_context(results)
    answer = await self._generate_answer(question, context)
```

**重构后 RAGAgent.answer()**：
```python
async def answer(self, question, tenant_id=None, top_k=5, enable_multi_step=False):
    # 使用 Controller 检索
    if enable_multi_step:
        result = await self.controller.retrieve_with_multi_step(...)
    else:
        result = await self.controller.retrieve(...)

    results = result.results

    # 生成答案
    context = self._build_context(results)
    answer = await self._generate_answer(question, context)
```

---

## 3. 文档切分规则

### 3.1 切分策略矩阵

| 文档类型 | 切分策略 | 块大小 | 重叠 | 特殊处理 |
|---------|---------|--------|------|---------|
| 技术文档 | 语义边界切分 | 800-1200 tokens | 100-200 | 保留代码块、API 表格 |
| 业务文档 | 段落切分 | 500-800 tokens | 50-100 | 保留结构化字段 |
| API 文档 | 端点级切分 | 每个端点独立 | 0 | 提取路径/参数/响应 |
| Markdown | 标题层级切分 | 600-1000 tokens | 100 | 保留标题层级 |
| PDF 文档 | 页面 + 段落 | 视内容而定 | 100 | OCR 后处理 |

### 3.2 核心切分算法

**语义边界切分**（默认策略）：
1. 按句子分割（使用正则或 NLP 工具）
2. 合并句子直到达到 target_chunk_size
3. 在以下边界优先切分：章节标题、列表项、代码块边界、表格边界
4. 添加 overlap 块以保证上下文连续性

### 3.3 元数据结构

```python
{
    "chunk_id": "uuid",
    "doc_id": "parent_doc_uuid",
    "content": "...",
    "embedding": [0.1, 0.2, ...],
    "metadata": {
        "doc_type": "technical|business|api",
        "title": "文档标题",
        "section": "所属章节",
        "chunk_index": 0,
        "token_count": 850,
        "source_type": "md|pdf|html",
        "language": "zh|en",
        "tags": ["api", "deployment"],
        "created_at": "timestamp",
        "tenant_id": "租户ID"
    }
}
```

### 3.4 多模态处理

- **表格**：保留表格结构为 Markdown，提取表头和关键行
- **代码块**：完整代码块作为单个 chunk，提取函数签名
- **图片**：提取周围说明文字，生成图片描述

---

## 4. 增量索引设计

### 4.1 索引流程

```
用户上传 → Document Manager → 索引队列（立即返回）
              ↓
        异步 Worker
              ↓
    文档解析 → 切分 → Embedding → 向量写入
              ↓
          更新状态
```

### 4.2 索引队列表（rag_index_queue）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| doc_id | UUID | 关联 rag_documents |
| tenant_id | varchar | 租户隔离 |
| status | enum | pending/processing/completed/failed |
| operation | enum | create/update/delete |
| priority | int | 优先级（0-9） |
| retry_count | int | 重试次数 |
| error_message | text | 失败原因 |
| created_at | timestamp | 创建时间 |
| started_at | timestamp | 开始时间 |
| completed_at | timestamp | 完成时间 |

### 4.3 更新策略

- **Create**：创建新文档和 chunks，加入索引队列
- **Update**：软删除旧 chunks，创建新 chunks（新版本号）
- **Delete**：软删除文档及其 chunks，定期物理删除

### 4.4 批量优化

- 小批量合并：5 分钟内或 10 个文档批量处理
- Embedding 批处理：利用 DashScope/OpenAI 批量接口

---

## 5. Agentic RAG 设计

### 5.1 执行流程

```
用户查询 → 查询扩展（生成变体） → HyDE（生成假设答案）
    ↓
并行检索（原始查询 + 扩展查询 + HyDE）
    ↓
去重合并 → 重排序（Rerank） → 质量评估
    ↓
[相关性低] → 重新检索（换关键词/重写）
    ↓
答案生成
```

### 5.2 查询扩展

为原始查询生成 3-5 种表述，提高召回率。

**示例**：
- 原始：`"如何配置 3D 搜索 API？"`
- 变体：
  - `"3D 搜索 API 配置方法"`
  - `"设置 3D 搜索 API 的步骤"`
  - `"怎样配置三维搜索接口"`

### 5.3 HyDE（假设生成）

对疑问句生成假设答案，用假设答案进行检索。

**示例**：
- 问题：`"如何处理 RAG 检索质量差的问题？"`
- 假设：`"RAG 检索质量差可能的原因包括：1. 切分策略不当... 改进方法：1. 调整 chunk size... 2. 使用混合检索..."`
- 用假设文档去检索，更容易找到相关的技术文档

### 5.4 去重与合并

1. 按 chunk_id 去重
2. 按 content 相似度去重（阈值 0.95）
3. 保留 score 最高的

### 5.5 重排序

使用 Cohere Rerank API 或本地模型对初步检索结果精排。

### 5.6 多步推理循环

```python
for iteration in range(max_iterations):
    results = await retrieve_and_rerank(query)
    quality = await assess_quality(query, results)
    
    if quality.is_satisfactory:
        return results
    
    # 调整策略重新检索
    if quality.issue == "low_relevance":
        query = await rewrite_query(query, feedback=quality.feedback)
```

---

## 6. 混合检索设计

### 6.1 检索流程

```
查询 → [向量 Embedding] → 向量检索（HNSW）
      ↓
      [查询预处理] → BM25 检索（全文搜索）
      ↓
    结果合并 → 去重 → 分数融合 → 排序
```

### 6.2 向量检索

使用 pgvector HNSW 索引进行向量相似度搜索。

```sql
CREATE INDEX rag_chunks_embedding_idx
ON rag_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### 6.3 BM25 检索

使用 PostgreSQL 全文搜索。

```sql
ALTER TABLE rag_chunks
ADD COLUMN content_tsv tsvector
GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, ''))) STORED;

CREATE INDEX rag_chunks_content_tsv_idx
ON rag_chunks USING gin (content_tsv);
```

### 6.4 分数融合

```python
final_score = alpha * normalized_vector_score + beta * normalized_bm25_score
```

### 6.5 动态权重

根据查询类型动态调整权重：

| 查询类型 | 向量权重 | BM25 权重 |
|---------|---------|----------|
| semantic（语义） | 0.8 | 0.2 |
| keyword（关键词） | 0.3 | 0.7 |
| balanced（平衡） | 0.5 | 0.5 |
| exact_match（精确匹配） | 0.1 | 0.9 |

---

## 7. 文档管理与版本控制

### 7.1 数据库表设计

#### rag_documents（文档元数据表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tenant_id | VARCHAR(100) | 租户 ID |
| title | VARCHAR(500) | 标题 |
| description | TEXT | 描述 |
| doc_type | VARCHAR(50) | 文档类型 |
| source_type | VARCHAR(50) | 来源类型 |
| raw_content | TEXT | 原始内容 |
| content_hash | VARCHAR(64) | 内容哈希 |
| version | INT | 版本号 |
| is_latest | BOOLEAN | 是否最新 |
| parent_doc_id | UUID | 上一版本 |
| status | VARCHAR(20) | 状态 |
| metadata | JSONB | 元数据 |
| tags | TEXT[] | 标签 |
| language | VARCHAR(10) | 语言 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| deleted_at | TIMESTAMP | 删除时间 |

#### rag_chunks（文档分块表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| doc_id | UUID | 文档 ID |
| tenant_id | VARCHAR(100) | 租户 ID |
| content | TEXT | 内容 |
| embedding | vector(1536) | 向量 |
| content_tsv | tsvector | 全文搜索向量 |
| chunk_index | INT | 分块索引 |
| token_count | INT | token 数量 |
| metadata | JSONB | 元数据 |
| doc_version | INT | 文档版本 |
| deleted_at | TIMESTAMP | 删除时间 |

#### rag_versions（版本历史表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| doc_id | UUID | 文档 ID |
| tenant_id | VARCHAR(100) | 租户 ID |
| version | INT | 版本号 |
| content_snapshot | TEXT | 内容快照 |
| chunk_count | INT | 分块数量 |
| change_type | VARCHAR(20) | 变更类型 |
| change_reason | TEXT | 变更原因 |
| changed_by | VARCHAR(100) | 操作人 |
| created_at | TIMESTAMP | 创建时间 |

### 7.2 Document Manager 接口

```python
class DocumentManager:
    async def create_document(...) -> Document
    async def update_document(...) -> Document
    async def delete_document(...) -> bool
    async def restore_document(...) -> Document
    async def get_document_history(...) -> List[VersionInfo]
```

---

## 8. 监控仪表板设计

### 8.1 性能指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| rag检索延迟 | Histogram | 检索请求处理时间 |
| rag向量检索延迟 | Histogram | 向量检索耗时 |
| rag_bm25检索延迟 | Histogram | BM25 检索耗时 |
| rag重排序延迟 | Histogram | 重排序耗时 |
| rag索引队列长度 | Gauge | 待处理文档数量 |
| rag检索请求数 | Counter | 总检索请求数 |
| rag空结果率 | Gauge | 空结果请求占比 |

### 8.2 质量监控

**rag_feedback 表**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tenant_id | VARCHAR(100) | 租户 ID |
| session_id | VARCHAR(100) | 会话 ID |
| query | TEXT | 查询 |
| retrieved_doc_ids | UUID[] | 检索到的文档 |
| rating | INT | 评分（1-5） |
| is_helpful | BOOLEAN | 是否有用 |
| thumb_up | BOOLEAN | 点赞 |
| feedback_text | TEXT | 反馈文本 |
| answer | TEXT | 生成的答案 |
| sources | JSONB | 来源文档 |
| created_at | TIMESTAMP | 创建时间 |

### 8.3 Grafana 仪表板

**面板 1：检索性能概览**
- 检索延迟趋势（P50, P95, P99）
- 向量检索 vs BM25 检索延迟对比
- 每小时请求数

**面板 2：索引状态**
- 队列长度（实时）
- 索引处理速率
- 失败率趋势

**面板 3：质量指标**
- 平均满意度（按时间）
- 有用率趋势
- 空结果率

**面板 4：文档统计**
- 总文档数趋势
- 文档类型分布
- 平均 chunk 大小

---

## 9. API 设计

### 9.1 文档管理 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/rag/documents` | POST | 创建文档 |
| `/api/v1/rag/documents/{id}` | GET | 获取文档详情 |
| `/api/v1/rag/documents/{id}` | PUT | 更新文档 |
| `/api/v1/rag/documents/{id}` | DELETE | 删除文档 |
| `/api/v1/rag/documents/{id}/restore` | POST | 恢复文档 |
| `/api/v1/rag/documents/{id}/history` | GET | 获取版本历史 |
| `/api/v1/rag/documents` | GET | 列出文档 |

### 9.2 检索与问答 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/rag/search` | POST | 检索接口 |
| `/api/v1/rag/ask` | POST | RAG 问答 |

### 9.3 监控 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/rag/index/status` | GET | 索引状态 |
| `/api/v1/rag/index/queue` | GET | 索引队列 |
| `/api/v1/rag/metrics` | GET | 监控指标 |
| `/api/v1/rag/feedback` | POST | 提交反馈 |

---

## 10. 配置项

### 10.1 新增配置

```python
# 文档存储路径
RAG_DATA_PATH: str = "./data/rag"
RAG_DOCUMENTS_PATH: str = "./data/rag/documents"

# 切分配置
CHUNK_SIZE_DEFAULT: int = 800
CHUNK_OVERLAP_DEFAULT: int = 150
CHUNK_SIZE_BY_TYPE: str = '{"technical": 1000, "business": 600, "api": 500}'

# 检索配置
RAG_TOP_K_RESULTS: int = 10
RAG_SIMILARITY_THRESHOLD: float = 0.7
RAG_RERANK_TOP_K: int = 5

# 混合检索权重
HYBRID_ALPHA_SEMANTIC: float = 0.7
HYBRID_ALPHA_KEYWORD: float = 0.3
HYBRID_ALPHA_EXACT: float = 0.1

# Agentic 配置
AGENTIC_QUERY_EXPANSION_COUNT: int = 3
AGENTIC_MAX_ITERATIONS: int = 3
AGENTIC_ENABLE_HYDE: bool = True
AGENTIC_ENABLE_RERANK: bool = True

# Rerank 配置
RERANK_PROVIDER: str = "cohere"
RERANK_MODEL: str = "rerank-english-v2.0"
COHERE_API_KEY: str = ""

# 索引配置
INDEX_BATCH_SIZE: int = 10
INDEX_WORKER_CONCURRENCY: int = 2
```

---

## 11. 依赖更新

```
# RAG 相关
cohere>=4.0                  # Rerank API
rank-bm25>=0.2.3             # BM25 算法
sentence-transformers>=2.2   # 可选：本地 Rerank 模型
unstructured>=0.10.0         # 文档解析
python-magic>=0.4.27         # 文件类型检测
pikepdf>=8.0.0               # PDF 处理

# 任务队列（可选）
celery>=5.3.0                # 异步任务队列
redis>=4.6.0                 # Celery broker
```

---

## 12. 实施阶段

### Phase 1: 基础设施（2-3 周）

- 数据库表创建
- 基础数据模型
- Document Manager
- 文档处理器、切分、Embedding
- 索引队列与 Worker
- 基础 API

### Phase 2: 核心检索（1-2 周）

- 向量检索引擎
- BM25 全文检索
- 混合检索融合
- 检索 API
- 更新 RAG Agent

### Phase 3: Agentic 特性（2-3 周）

- 查询扩展
- HyDE 实现
- 去重合并
- 重排序服务
- 多步推理
- Agentic Controller

### Phase 4: 高级功能（1-2 周）

- 版本管理
- 监控指标
- 质量反馈
- 监控 API
- Grafana 仪表板

### Phase 5: 优化与上线（1 周）

- 性能优化
- 缓存层
- 文档完善
- 部署配置
- 上线验证

---

## 13. 热门功能补充

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 多模态 RAG | 图文结合检索，使用 CLIP 等多模态模型 | 中 |
| 知识图谱增强 | 结合知识图谱进行实体链接和关系推理 | 低 |
| 长文本重组 | 对长文档进行层次化检索和重组 | 中 |
| 跨文档推理 | 支持跨多个文档的复杂推理 | 低 |
| 实时文档同步 | 支持 Webhook/WebSocket 实时同步更新 | 低 |
| 多语言支持 | 跨语言检索（中文查询匹配英文文档） | 中 |

---

## 附录 A：数据库 Schema

详见第 7.1 节的完整表设计。

## 附录 B：API 示例

### 创建文档

```bash
curl -X POST http://localhost:8000/api/v1/rag/documents \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default",
    "title": "3D 搜索 API 文档",
    "content": "...",
    "doc_type": "technical",
    "metadata": {"version": "1.0.0"}
  }'
```

### 检索

```bash
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何配置 3D 搜索 API？",
    "top_k": 10,
    "enable_expansion": true,
    "enable_hyde": true,
    "enable_rerank": true
  }'
```

---

*文档结束*

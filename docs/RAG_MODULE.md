# RAG Module Documentation

## 概述

RAG (Retrieval-Augmented Generation) 模块提供智能文档检索和问答能力，支持混合检索、Agentic 特性和多租户隔离。

## 核心特性

### 1. 文档管理
- **版本控制**: 文档更新自动创建新版本，保留历史快照
- **增量索引**: 异步 Worker 处理索引任务，支持并发
- **软删除/恢复**: 支持文档的软删除和恢复功能
- **多种文档类型**: 支持 Markdown、PDF、HTML、JSON 等格式

### 2. 混合检索
- **向量检索**: 使用 pgvector HNSW 索引进行语义搜索
- **BM25 检索**: 基于 PostgreSQL 全文检索的关键词搜索
- **动态权重**: 根据查询类型自动调整向量/关键词权重

### 3. Agentic RAG
- **查询扩展**: 使用 LLM 生成查询的不同表述
- **HyDE**: 生成假设性文档提高检索质量
- **重排序**: 使用 Cohere Rerank API 优化结果排序
- **多步推理**: 自动评估检索质量并调整策略

### 4. 监控与反馈
- **性能指标**: 记录检索延迟、请求数等指标
- **质量反馈**: 收集用户评分和有用性反馈
- **OpenTelemetry 集成**: 支持分布式追踪

## 快速开始

### 1. 数据库迁移

```bash
psql -U postgres -d i3d_agent -f i3d_agent/migrations/versions/002_add_rag_tables.sql
```

### 2. 配置环境变量

在 `.env` 文件中添加：

```bash
# RAG Configuration
RAG_DATA_PATH=./data/rag
CHUNK_SIZE_DEFAULT=800
RAG_TOP_K_RESULTS=10

# Cohere API (用于重排序)
COHERE_API_KEY=your-cohere-api-key
RERANK_PROVIDER=cohere

# 索引配置
INDEX_WORKER_CONCURRENCY=2
```

### 3. 启动索引 Worker

```bash
# 方式一：直接运行
python scripts/run_rag_worker.py

# 方式二：Docker Compose
docker-compose up rag-worker
```

### 4. 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/rag/documents \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default",
    "title": "API 文档",
    "content": "# API Reference\n\n## GET /api/test\n\n这是一个测试接口。",
    "doc_type": "technical",
    "source_type": "md"
  }'
```

### 5. 搜索文档

```bash
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试接口",
    "tenant_id": "default",
    "top_k": 5
  }'
```

### 6. 问答

```bash
curl -X POST http://localhost:8000/api/v1/rag/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "如何使用测试接口？",
    "tenant_id": "default"
  }'
```

## API 参考

### 文档管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/rag/documents` | POST | 创建文档 |
| `/api/v1/rag/documents/{doc_id}` | GET | 获取文档详情 |
| `/api/v1/rag/documents/{doc_id}` | PUT | 更新文档 |
| `/api/v1/rag/documents/{doc_id}` | DELETE | 删除文档 |
| `/api/v1/rag/documents/{doc_id}/restore` | POST | 恢复文档 |
| `/api/v1/rag/documents/{doc_id}/history` | GET | 获取版本历史 |
| `/api/v1/rag/documents` | GET | 列出文档（分页） |

### 检索与问答

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/rag/search` | POST | 检索文档片段 |
| `/api/v1/rag/ask` | POST | RAG 问答 |

### 监控

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/rag/index/status` | GET | 获取索引状态 |
| `/api/v1/rag/index/queue` | GET | 获取索引队列 |
| `/api/v1/rag/metrics` | GET | 获取监控指标 |
| `/api/v1/rag/quality` | GET | 获取质量指标 |
| `/api/v1/rag/feedback` | POST | 提交质量反馈 |

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAG 模块架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   API 层      │    │  Controller  │    │  Worker 层    │      │
│  │  rag/api.py  │───▶│controller.py │◀───│index_worker.py│      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                     检索层                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐    │  │
│  │  │retrieval.py │  │  rerank.py  │  │query_expansion│    │  │
│  │  │混合检索引擎  │  │  重排序服务  │  │   HyDE服务    │    │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    文档处理层                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐    │  │
│  │  │processor.py │  │embedding.py │  │document_mgr  │    │  │
│  │  │  文档切分   │  │  向量生成    │  │  文档管理    │    │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                     存储层                                │  │
│  │  PostgreSQL + pgvector (向量 + 全文检索 + 元数据)        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 数据库表结构

| 表名 | 描述 |
|------|------|
| `rag_documents` | 文档元数据（版本控制、软删除） |
| `rag_chunks` | 文档分块（向量、全文检索索引） |
| `rag_versions` | 版本历史快照 |
| `rag_index_queue` | 索引任务队列 |
| `rag_metrics` | 监控指标 |
| `rag_feedback` | 质量反馈 |

## 多租户隔离

RAG 模块使用 PostgreSQL Row-Level Security (RLS) 实现租户隔离：

```sql
-- 设置当前租户
SET app.current_tenant = 'tenant_id';

-- 所有查询自动过滤当前租户数据
SELECT * FROM rag_documents WHERE tenant_id = current_setting('app.current_tenant');
```

## 性能优化

### 向量索引优化
- HNSW 索引参数：`m=16, ef_construction=64`
- 支持余弦相似度（`vector_cosine_ops`）

### 全文检索优化
- 预计算 `tsvector` 列
- GIN 索引加速查询

### 并发配置
- 索引 Worker 并发数：`INDEX_WORKER_CONCURRENCY=2`
- 数据库连接池：根据负载调整

## 故障排查

### 问题：索引 Worker 无任务处理

检查队列状态：
```bash
curl http://localhost:8000/api/v1/rag/index/queue?tenant_id=default
```

### 问题：检索结果质量差

1. 检查 chunk 大小配置（`CHUNK_SIZE_DEFAULT`）
2. 启用查询扩展（`enable_expansion=true`）
3. 启用 HyDE（`enable_hyde=true`）
4. 启用重排序（`enable_rerank=true`）

### 问题：重排序失败

检查 Cohere API Key 配置：
```bash
echo $COHERE_API_KEY
```

## 更多信息

- [设计文档](./superpowers/specs/2026-06-01-rag-module-design.md)
- [实施计划](./superpowers/plans/2026-06-01-rag-module-implementation.md)

# I3D 系统 Agent 架构设计方案

> 设计时间: 2026-05-26
> 版本: v1.0
> 基于: AGENT_COMPREHENSIVE_RESEARCH.md

---

## 一、设计目标

```
┌─────────────────────────────────────────────────────────────┐
│                      设计目标                                │
├─────────────────────────────────────────────────────────────┤
│  ✓ 智能 3D 搜索助手 - 理解自然语言查询                       │
│  ✓ 技术文档问答 - RAG 知识库检索                             │
│  ✓ 多租户隔离 - 复用现有 RLS 架构                            │
│  ✓ 微服务编排 - 协调 5 个现有服务                            │
│  ✓ 生产级部署 - 可观测、可评估、可扩展                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              I3D Agent 系统                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                            接入层                                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │  桌面客户端   │  │   Web 界面   │  │   REST API   │                │  │
│  │  │ (Electron)   │  │    (Vue)     │  │  (外部调用)   │                │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │  │
│  └─────────┼──────────────────┼──────────────────┼───────────────────────┘  │
│            │                  │                  │                          │
│            └──────────────────┼──────────────────┘                          │
│                               ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Agent 网关                                     │  │
│  │                    (FastAPI + WebSocket)                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │  认证中间件   │  │ 租户上下文    │  │  限流控制     │                │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Agent 编排层 (LangGraph)                          │  │
│  │                                                                       │  │
│  │                    ┌─────────────────────┐                            │  │
│  │                    │   Supervisor Agent  │                            │  │
│  │                    │   (任务协调与路由)   │                            │  │
│  │                    └──────────┬──────────┘                            │  │
│  │                               │                                       │  │
│  │        ┌──────────────────────┼──────────────────────┐               │  │
│  │        ▼                      ▼                      ▼               │  │
│  │  ┌───────────┐          ┌───────────┐          ┌───────────┐         │  │
│  │  │  Search   │          │   RAG     │          │  Process  │         │  │
│  │  │  Agent    │          │  Agent    │          │  Agent    │         │  │
│  │  │(3D搜索专家)│          │(知识库专家)│          │(处理专家)  │         │  │
│  │  └─────┬─────┘          └─────┬─────┘          └─────┬─────┘         │  │
│  │        │                      │                      │               │  │
│  │        └──────────────────────┼──────────────────────┘               │  │
│  │                               ▼                                       │  │
│  │                    ┌─────────────────────┐                            │  │
│  │                    │    记忆系统          │                            │  │
│  │                    │ (短期 + 长期记忆)     │                            │  │
│  │                    └─────────────────────┘                            │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                          工具层                                       │  │
│  │                                                                       │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │  │
│  │  │   搜索工具组      │  │   知识库工具组    │  │   处理工具组      │     │  │
│  │  │                  │  │                  │  │                  │     │  │
│  │  │ • search_3d      │  │ • retrieve_docs  │  │ • process_file   │     │  │
│  │  │ • search_2d      │  │ • search_api     │  │ • check_status   │     │  │
│  │  │ • filter_results │  │ • get_guide      │  │ • retry_task     │     │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘     │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        RAG 模块层 (新增)                               │  │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │  │
│  │  │ Document    │   │  Embedding  │   │  Retrieval  │               │  │
│  │  │ Processor  │──→│   Service   │──→│   Engine    │               │  │
│  │  └─────────────┘   └─────────────┘   └──────┬──────┘               │  │
│  │                                             │                        │  │
│  │  ┌─────────────────────────────────────────┴────────┐              │  │
│  │  │              Agentic RAG Controller               │              │  │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│              │  │
│  │  │  │ Query   │ │  HyDE   │ │Rerank   │ │ Multi  ││              │  │
│  │  │  │ Rewrite │ │         │ │         │ │ Step   ││              │  │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └────────┘│              │  │
│  │  └──────────────────────────────────────────────────┘              │  │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │  │
│  │  │  Document   │   │   Version   │   │  Monitor    │               │  │
│  │  │   Manager   │   │  Control    │   │   Service   │               │  │
│  │  └─────────────┘   └─────────────┘   └─────────────┘               │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        现有服务层 (复用)                               │  │
│  │                                                                       │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                     │  │
│  │  │InferEngineer-       │  │   3d-search-core    │                     │  │
│  │  │3dRetrieval          │  │   (推理服务)         │                     │  │
│  │  │(搜索服务:18000)     │  │   (推理:28000)      │                     │  │
│  │  └─────────────────────┘  └─────────────────────┘                     │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                     │  │
│  │  │    minio-api        │  │  xxl_job_executor   │                     │  │
│  │  │  (批处理:48000)     │  │  (CAD处理:38000)    │                     │  │
│  │  └─────────────────────┘  └─────────────────────┘                     │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL + pgvector (数据层)                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  │rag_documents │  │rag_chunks    │  │rag_versions  │  │  RAG      │  │
│  │  │   (元数据)    │  │  (向量+内容)  │  │  (版本历史)    │  │  Tables   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  │rag_index_queue│ │rag_metrics   │  │rag_feedback  │  │ Agent     │  │
│  │  │ (增量索引队列) │  │ (性能指标)    │  │ (质量反馈)    │  │  Memory   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │              基础设施层 (Redis / RabbitMQ / MinIO)                     │  │
│  │     Redis(6379)  │  RabbitMQ(5672)  │  MinIO(9000)                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        支撑系统                                       │  │
│  │                                                                       │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │  │
│  │  │   可观测性        │  │     评估          │  │    监控告警       │     │  │
│  │  │ Arize Phoenix    │  │   RAGAS          │  │   Prometheus     │     │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术选型

| 组件 | 技术选型 | 版本 | 理由 |
|------|---------|------|------|
| **Agent 框架** | LangGraph | 0.2+ | 状态图架构，Python 原生 |
| **Web 框架** | FastAPI | 0.110+ | 高性能，类型安全 |
| **LLM 模型** | Claude 3.5 Sonnet | - | 长上下文，中文友好 |
| **向量存储** | pgvector | 已有 | 零成本，RLS 支持 |
| **短期记忆** | Redis | 已有 | 已部署 |
| **长期记忆** | PostgreSQL + pgvector | 已有 | 复用现有设施 |
| **可观测性** | Arize Phoenix | 开源 | OpenTelemetry 原生 |
| **评估框架** | RAGAS | 开源 | RAG 专项评估 |

---

## 三、Agent 角色设计

### 3.1 Supervisor Agent (监督者)

```python
class SupervisorAgent:
    """
    监督者 Agent - 负责任务分解、路由和协调
    """

    role = "任务协调专家"
    goal = "理解用户需求，协调专业 Agent 完成任务"
    backstory = """
    你是 I3D 系统的智能协调者，精通 3D CAD 领域知识。
    你能够：
    - 理解用户的自然语言查询
    - 判断任务类型并路由到合适的 Agent
    - 协调多个 Agent 协作完成复杂任务
    - 汇总结果并以清晰的方式呈现
    """

    # 路由规则
    routing_rules = {
        "search": ["搜索", "查找", "相似", "匹配", "推荐"],
        "rag": ["文档", "手册", "教程", "API", "使用"],
        "process": ["处理", "转换", "入库", "状态"],
        "general": ["你好", "帮助", "是什么"]
    }

    # 支持的工具
    tools = [
        route_to_search_agent,
        route_to_rag_agent,
        route_to_process_agent,
        handle_general_query
    ]
```

### 3.2 Search Agent (搜索专家)

```python
class SearchAgent:
    """
    搜索专家 Agent - 负责 3D/2D 模型搜索
    """

    role = "3D 模型搜索专家"
    goal = "帮助用户找到相似的 CAD 零件或产品"
    backstory = """
    你是 3D CAD 搜索领域的专家，精通：
    - 3D 模型特征提取和相似度计算
    - 2D 图片转 3D 搜索
    - PLM 属性过滤
    - 搜索结果优化和排序
    """

    # 能力
    capabilities = {
        "3d_search": "上传 3D 模型文件进行相似度搜索",
        "2d_search": "上传 2D 图片搜索相似的 3D 零件",
        "attribute_filter": "根据材质、尺寸等属性过滤",
        "hybrid_search": "组合多种搜索策略"
    }

    # 工具
    tools = [
        search_3d_model,
        search_2d_image,
        filter_by_attributes,
        get_model_details
    ]
```

### 3.3 RAG Agent (知识库专家)

```python
class RAGAgent:
    """
    知识库专家 Agent - 负责技术文档问答
    集成 Agentic RAG 能力：查询扩展、HyDE、重排序、多步推理
    """

    role = "I3D 技术文档专家"
    goal = "从技术文档中回答用户问题，支持多步推理和智能检索"
    backstory = """
    你是 I3D 系统的技术文档专家，熟悉：
    - API 使用方法和参数说明
    - 系统架构和组件关系
    - 部署和运维指南
    - 故障排查和最佳实践
    
    你具备先进的检索能力：
    - 查询扩展：生成多种查询表述提高召回率
    - HyDE：假设文档生成，用假设答案检索
    - 混合检索：向量检索 + BM25 全文检索
    - 重排序：使用 Rerank 模型精排结果
    - 多步推理：迭代检索直到满意结果
    """

    # 知识库范围
    knowledge_bases = {
        "api_docs": "API 接口文档",
        "user_guide": "用户使用手册",
        "deploy_guide": "部署运维指南",
        "architecture": "系统架构文档",
        "troubleshooting": "故障排查手册",
        "technical": "技术文档（语义边界切分）",
        "business": "业务文档（段落切分）",
        "api": "API 文档（端点级切分）"
    }

    # Agentic RAG 能力
    agentic_capabilities = {
        "query_expansion": "生成 3-5 种查询变体",
        "hyde": "假设文档生成与检索",
        "hybrid_retrieval": "向量 + BM25 混合检索",
        "reranking": "重排序精排（Cohere/本地）",
        "multi_step": "多步推理迭代检索",
        "deduplication": "去重合并检索结果"
    }

    # 工具（增强版）
    tools = [
        retrieve_documents,
        search_api_reference,
        get_deployment_guide,
        find_troubleshooting_steps,
        # 新增 Agentic RAG 工具
        expand_query,
        generate_hyde_document,
        hybrid_retrieve,
        rerank_results,
        assess_retrieval_quality
    ]
```

### 3.4 Process Agent (处理专家)

```python
class ProcessAgent:
    """
    处理专家 Agent - 负责文件处理状态查询
    """

    role = "文件处理状态专家"
    goal = "查询和管理 CAD 文件处理任务"
    backstory = """
    你是文件处理流程的监控专家，能够：
    - 查询文件处理状态
    - 诊断处理失败原因
    - 触发重试操作
    - 提供处理进度信息
    """

    # 工具
    tools = [
        get_task_status,
        get_processing_history,
        retry_failed_task,
        diagnose_error
    ]
```

---

## 四、工具封装设计

### 4.1 搜索工具组

```python
# i3d_agent/tools/search_tools.py

from langchain.tools import tool
from typing import List, Optional
import httpx

@tool
def search_3d_model(
    item_code: str,
    file_type: int = 1,
    top_k: int = 10,
    tenant_id: str = "huabei"
) -> dict:
    """
    使用 3D 模型编码搜索相似的零件

    Args:
        item_code: 零件编码
        file_type: 1=零件库, 2=产品库
        top_k: 返回结果数量
        tenant_id: 租户ID

    Returns:
        搜索结果列表，包含相似度和详细信息
    """
    url = f"http://localhost:18000/api/search/searchBy3D"
    payload = {
        "item_code": item_code,
        "file_type": file_type,
        "top_k": top_k
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json()


@tool
def search_2d_image(
    image_base64: str,
    file_type: int = 1,
    top_k: int = 10,
    tenant_id: str = "huabei"
) -> dict:
    """
    使用 2D 图片搜索相似的 3D 零件

    Args:
        image_base64: Base64 编码的图片数据
        file_type: 1=零件库, 2=产品库
        top_k: 返回结果数量
        tenant_id: 租户ID

    Returns:
        搜索结果列表
    """
    url = f"http://localhost:18000/api/search/searchBy2D"
    payload = {
        "image": image_base64,
        "file_type": file_type,
        "top_k": top_k
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json()


@tool
def filter_by_attributes(
    results: List[dict],
    material: Optional[str] = None,
    weight_min: Optional[float] = None,
    weight_max: Optional[float] = None
) -> List[dict]:
    """
    根据 PLM 属性过滤搜索结果

    Args:
        results: 原始搜索结果
        material: 材质过滤
        weight_min: 最小重量
        weight_max: 最大重量

    Returns:
        过滤后的结果
    """
    filtered = results

    if material:
        filtered = [r for r in filtered if r.get("material") == material]

    if weight_min is not None:
        filtered = [r for r in filtered if r.get("weight", 0) >= weight_min]

    if weight_max is not None:
        filtered = [r for r in filtered if r.get("weight", 0) <= weight_max]

    return filtered


@tool
def get_model_details(
    item_code: str,
    tenant_id: str = "huabei"
) -> dict:
    """
    获取模型详细信息

    Args:
        item_code: 零件编码
        tenant_id: 租户ID

    Returns:
        模型详细信息，包括 PLM 属性
    """
    url = f"http://localhost:18000/api/product/details"
    params = {"item_code": item_code}
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.get(url, params=params, headers=headers)
        return response.json()
```

### 4.2 知识库工具组（增强版）

```python
# i3d_agent/tools/rag_tools.py

from langchain.tools import tool
from typing import List, Optional, Dict, Any
import httpx

@tool
def retrieve_documents(
    query: str,
    knowledge_base: str = "all",
    top_k: int = 5,
    tenant_id: str = "huabei",
    enable_expansion: bool = False,
    enable_hyde: bool = False,
    enable_rerank: bool = False
) -> List[dict]:
    """
    从技术文档知识库中检索相关文档（支持 Agentic RAG 特性）

    Args:
        query: 查询问题
        knowledge_base: 知识库类型 (api_docs/user_guide/deploy_guide/all)
        top_k: 返回文档数量
        tenant_id: 租户ID
        enable_expansion: 启用查询扩展
        enable_hyde: 启用 HyDE（假设文档生成）
        enable_rerank: 启用重排序

    Returns:
        相关文档列表，包含内容和相似度
    """
    url = "http://localhost:8000/api/v1/rag/search"
    payload = {
        "query": query,
        "top_k": top_k,
        "enable_expansion": enable_expansion,
        "enable_hyde": enable_hyde,
        "enable_rerank": enable_rerank
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json().get("results", [])


@tool
def search_api_reference(
    endpoint: str,
    method: Optional[str] = None,
    tenant_id: str = "huabei"
) -> dict:
    """
    搜索 API 接口文档

    Args:
        endpoint: API 端点路径
        method: HTTP 方法 (GET/POST/PUT/DELETE)
        tenant_id: 租户ID

    Returns:
        API 文档详情
    """
    url = "http://localhost:8000/api/v1/rag/api-docs"
    params = {"endpoint": endpoint}
    if method:
        params["method"] = method
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.get(url, params=params, headers=headers)
        return response.json()


@tool
def get_deployment_guide(
    component: str,
    tenant_id: str = "huabei"
) -> dict:
    """
    获取组件部署指南

    Args:
        component: 组件名称 (search-core/infer-engineer/minio-api)
        tenant_id: 租户ID

    Returns:
        部署指南内容
    """
    url = "http://localhost:8000/api/v1/rag/deploy-guide"
    params = {"component": component}
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.get(url, params=params, headers=headers)
        return response.json()


@tool
def find_troubleshooting_steps(
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    component: Optional[str] = None,
    tenant_id: str = "huabei"
) -> List[dict]:
    """
    查找故障排查步骤

    Args:
        error_code: 错误代码
        error_message: 错误信息
        component: 组件名称
        tenant_id: 租户ID

    Returns:
        故障排查步骤列表
    """
    url = "http://localhost:8000/api/v1/rag/troubleshoot"
    payload = {}
    if error_code:
        payload["error_code"] = error_code
    if error_message:
        payload["error_message"] = error_message
    if component:
        payload["component"] = component

    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json().get("steps", [])


# ============ Agentic RAG 新增工具 ============

@tool
def expand_query(
    query: str,
    num_variants: int = 3,
    tenant_id: str = "huabei"
) -> List[str]:
    """
    查询扩展：生成查询的多种表述

    Args:
        query: 原始查询
        num_variants: 生成变体数量
        tenant_id: 租户ID

    Returns:
        查询变体列表
    """
    url = "http://localhost:8000/api/v1/rag/query/expand"
    payload = {
        "query": query,
        "num_variants": num_variants
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json().get("variants", [])


@tool
def generate_hyde_document(
    query: str,
    tenant_id: str = "huabei"
) -> str:
    """
    HyDE：生成假设文档

    Args:
        query: 用户查询
        tenant_id: 租户ID

    Returns:
        生成的假设文档
    """
    url = "http://localhost:8000/api/v1/rag/hyde/generate"
    payload = {"query": query}
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json().get("hyde_document", "")


@tool
def hybrid_retrieve(
    query: str,
    top_k: int = 10,
    alpha: float = 0.7,
    tenant_id: str = "huabei"
) -> List[dict]:
    """
    混合检索：向量 + BM25

    Args:
        query: 查询内容
        top_k: 返回数量
        alpha: 向量权重（0-1，BM25权重 = 1-alpha）
        tenant_id: 租户ID

    Returns:
        检索结果列表
    """
    url = "http://localhost:8000/api/v1/rag/retrieve/hybrid"
    payload = {
        "query": query,
        "top_k": top_k,
        "alpha": alpha
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json().get("results", [])


@tool
def rerank_results(
    query: str,
    documents: List[str],
    top_k: int = 5,
    tenant_id: str = "huabei"
) -> List[dict]:
    """
    重排序：使用 Rerank 模型精排结果

    Args:
        query: 原始查询
        documents: 待排序文档列表
        top_k: 返回前K个
        tenant_id: 租户ID

    Returns:
        重排序后的结果列表
    """
    url = "http://localhost:8000/api/v1/rag/rerank"
    payload = {
        "query": query,
        "documents": documents,
        "top_k": top_k
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json().get("reranked_results", [])


@tool
def assess_retrieval_quality(
    query: str,
    results: List[dict],
    tenant_id: str = "huabei"
) -> Dict[str, Any]:
    """
    评估检索质量

    Args:
        query: 查询内容
        results: 检索结果
        tenant_id: 租户ID

    Returns:
        质量评估结果
    """
    url = "http://localhost:8000/api/v1/rag/assess"
    payload = {
        "query": query,
        "results": results
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json()


@tool
def create_document(
    title: str,
    content: str,
    doc_type: str = "technical",
    metadata: Optional[dict] = None,
    tenant_id: str = "huabei"
) -> dict:
    """
    创建文档并加入索引队列

    Args:
        title: 文档标题
        content: 文档内容
        doc_type: 文档类型
        metadata: 元数据
        tenant_id: 租户ID

    Returns:
        创建的文档信息
    """
    url = "http://localhost:8000/api/v1/rag/documents"
    payload = {
        "title": title,
        "content": content,
        "doc_type": doc_type,
        "metadata": metadata or {}
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json()


@tool
def get_index_status(
    tenant_id: str = "huabei"
) -> dict:
    """
    获取索引状态

    Args:
        tenant_id: 租户ID

    Returns:
        索引状态信息
    """
    url = "http://localhost:8000/api/v1/rag/index/status"
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.get(url, headers=headers)
        return response.json()
```

### 4.3 处理工具组

```python
# i3d_agent/tools/process_tools.py

from langchain.tools import tool
from typing import Optional
import httpx

@tool
def get_task_status(
    task_id: str,
    tenant_id: str = "huabei"
) -> dict:
    """
    查询文件处理任务状态

    Args:
        task_id: 任务ID
        tenant_id: 租户ID

    Returns:
        任务状态信息
    """
    url = f"http://localhost:38000/api/task/status"
    params = {"task_id": task_id}
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.get(url, params=params, headers=headers)
        return response.json()


@tool
def get_processing_history(
    item_code: str,
    tenant_id: str = "huabei"
) -> list:
    """
    获取零件处理历史记录

    Args:
        item_code: 零件编码
        tenant_id: 租户ID

    Returns:
        处理历史记录列表
    """
    url = f"http://localhost:38000/api/task/history"
    params = {"item_code": item_code}
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.get(url, params=params, headers=headers)
        return response.json()


@tool
def retry_failed_task(
    task_id: str,
    tenant_id: str = "huabei"
) -> dict:
    """
    重试失败的处理任务

    Args:
        task_id: 任务ID
        tenant_id: 租户ID

    Returns:
        重试结果
    """
    url = f"http://localhost:38000/api/task/retry"
    payload = {"task_id": task_id}
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json()


@tool
def diagnose_error(
    error_message: str,
    component: str,
    tenant_id: str = "huabei"
) -> dict:
    """
    诊断错误原因并提供解决方案

    Args:
        error_message: 错误信息
        component: 组件名称
        tenant_id: 租户ID

    Returns:
        诊断结果和建议
    """
    url = f"http://localhost:8000/api/agent/diagnose"
    payload = {
        "error_message": error_message,
        "component": component
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json()
```

---

## 五、记忆系统设计

### 5.1 记忆架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        记忆系统架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │              工作记忆 (Working Memory)                     │   │
│  │              - 当前对话上下文                              │   │
│  │              - 任务状态                                    │   │
│  │              - 存储: 内存                                  │   │
│  │              - 容量: ~100K tokens                          │   │
│  └───────────────────────────────────────────────────────────┘   │
│                          ↕                                        │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │              短期记忆 (Short-term Memory)                  │   │
│  │              - 最近 24-72 小时交互                         │   │
│  │              - 用户偏好                                    │   │
│  │              - 存储: Redis (已有)                          │   │
│  │              - TTL: 72 小时                                │   │
│  └───────────────────────────────────────────────────────────┘   │
│                          ↕                                        │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │              长期记忆 (Long-term Memory)                   │   │
│  │              - 用户搜索历史                                │   │
│  │              - 知识库向量                                  │   │
│  │              - 存储: pgvector (已有)                       │   │
│  │              - 持久化                                      │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 记忆实现

```python
# i3d_agent/memory/memory_manager.py

from typing import Optional, List, Dict, Any
import redis
import json
from pgvector psycopg2 import execute_values

class MemoryManager:
    """统一记忆管理器"""

    def __init__(self):
        # 短期记忆 - Redis
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

        # 长期记忆 - pgvector
        self.pg_conn = psycopg2.connect(
            host='localhost',
            port=15432,
            database='i3d_multitenant',
            user='app_user',
            password='app_pass'
        )

    # ============ 工作记忆 ============

    def set_context(self, session_id: str, key: str, value: Any):
        """设置工作记忆"""
        key = f"wm:{session_id}:{key}"
        self.redis_client.setex(key, 3600, json.dumps(value))

    def get_context(self, session_id: str, key: str) -> Optional[Any]:
        """获取工作记忆"""
        key = f"wm:{session_id}:{key}"
        value = self.redis_client.get(key)
        return json.loads(value) if value else None

    # ============ 短期记忆 ============

    def set_user_preference(self, user_id: str, key: str, value: Any):
        """设置用户偏好 (72小时)"""
        key = f"pref:{user_id}:{key}"
        self.redis_client.setex(key, 259200, json.dumps(value))

    def get_user_preference(self, user_id: str, key: str) -> Optional[Any]:
        """获取用户偏好"""
        key = f"pref:{user_id}:{key}"
        value = self.redis_client.get(key)
        return json.loads(value) if value else None

    def add_search_history(self, user_id: str, query: str, results: List[dict]):
        """添加搜索历史"""
        key = f"history:{user_id}"
        history_item = {
            "query": query,
            "results": results,
            "timestamp": time.time()
        }
        self.redis_client.lpush(key, json.dumps(history_item))
        self.redis_client.ltrim(key, 0, 99)  # 保留最近100条
        self.redis_client.expire(key, 259200)  # 72小时

    def get_recent_searches(self, user_id: str, limit: int = 10) -> List[dict]:
        """获取最近搜索"""
        key = f"history:{user_id}"
        items = self.redis_client.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in items]

    # ============ 长期记忆 ============

    def store_semantic_memory(
        self,
        tenant_id: str,
        user_id: str,
        content: str,
        metadata: dict,
        embedding: List[float]
    ):
        """存储语义记忆 (向量)"""
        with self.pg_conn.cursor() as cur:
            cur.execute("SET app.current_tenant = %s", (tenant_id,))
            execute_values(cur, """
                INSERT INTO agent_memory (user_id, content, embedding, metadata)
                VALUES (%s, %s, %s::vector, %s)
            """, [(user_id, content, embedding, json.dumps(metadata))])
            self.pg_conn.commit()

    def retrieve_semantic_memory(
        self,
        tenant_id: str,
        user_id: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[dict]:
        """检索语义记忆"""
        with self.pg_conn.cursor() as cur:
            cur.execute("SET app.current_tenant = %s", (tenant_id,))
            cur.execute("""
                SELECT content, metadata, 1 - (embedding <=> %s::vector) as similarity
                FROM agent_memory
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, user_id, query_embedding, top_k))

            return [
                {
                    "content": row[0],
                    "metadata": json.loads(row[1]),
                    "similarity": float(row[2])
                }
                for row in cur.fetchall()
            ]
```

### 5.3 记忆表设计

```sql
-- Agent 记忆表 (长期语义记忆)
CREATE TABLE agent_memory (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI embedding 维度
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- HNSW 索引
CREATE INDEX ON agent_memory
USING hnsw (embedding vector_cosine_ops)
WHERE tenant_id = 'huabei';

-- RLS 策略
ALTER TABLE agent_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_memory_tenant_policy ON agent_memory
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true));

-- 用户搜索历史表 (结构化记忆)
CREATE TABLE agent_search_history (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    query_type TEXT NOT NULL,  -- '3d', '2d', 'text'
    query_content TEXT,
    filters JSONB DEFAULT '{}',
    result_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_search_history_user
ON agent_search_history(tenant_id, user_id, created_at DESC);
```

---

## 六、RAG 知识库设计

### 6.1 知识库结构

```
i3d_knowledge_base/
├── api_docs/                    # API 文档
│   ├── search_api.md
│   ├── inference_api.md
│   └── processing_api.md
├── user_guide/                  # 用户手册
│   ├── quick_start.md
│   ├── search_guide.md
│   └── upload_guide.md
├── deploy_guide/                # 部署指南
│   ├── local_deploy.md
│   ├── docker_deploy.md
│   └── cloud_deploy.md
├── architecture/                # 架构文档
│   ├── system_architecture.md
│   ├── service_topology.md
│   └── data_flow.md
└── troubleshooting/             # 故障排查
    ├── common_errors.md
    ├── performance_issues.md
    └── faq.md
```

### 6.2 文档切分策略

| 文档类型 | 切分策略 | 块大小 | 重叠 | 特殊处理 |
|---------|---------|--------|------|---------|
| 技术文档 | 语义边界切分 | 800-1200 tokens | 100-200 | 保留代码块、API 表格 |
| 业务文档 | 段落切分 | 500-800 tokens | 50-100 | 保留结构化字段 |
| API 文档 | 端点级切分 | 每个端点独立 | 0 | 提取路径/参数/响应 |
| Markdown | 标题层级切分 | 600-1000 tokens | 100 | 保留标题层级 |
| PDF 文档 | 页面 + 段落 | 视内容而定 | 100 | OCR 后处理 |

### 6.3 RAG 模块架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG 模块                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │ Document    │   │  Embedding  │   │  Retrieval  │           │
│  │ Processor  │──→│   Service   │──→│   Engine    │           │
│  └─────────────┘   └─────────────┘   └──────┬──────┘           │
│                                             │                    │
│  ┌─────────────────────────────────────────┴────────┐          │
│  │              Agentic RAG Controller               │          │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│          │
│  │  │ Query   │ │  HyDE   │ │Rerank   │ │ Multi  ││          │
│  │  │ Rewrite │ │         │ │         │ │ Step   ││          │
│  │  └─────────┘ └─────────┘ └─────────┘ └────────┘│          │
│  └──────────────────────────────────────────────────┘          │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │  Document   │   │   Version   │   │  Monitor    │           │
│  │   Manager   │   │  Control    │   │   Service   │           │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### 6.4 增量索引设计

```
用户上传 → Document Manager → 索引队列（立即返回）
              ↓
        异步 Worker
              ↓
    文档解析 → 切分 → Embedding → 向量写入
              ↓
          更新状态
```

### 6.5 Agentic RAG 执行流程

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

### 6.6 混合检索设计

```
查询 → [向量 Embedding] → 向量检索（HNSW）
      ↓
      [查询预处理] → BM25 检索（全文搜索）
      ↓
    结果合并 → 去重 → 分数融合 → 排序
```

### 6.7 项目结构

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
│   ├── index_worker.py          # 索引 Worker
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
    └── settings.py                # 配置
```

### 6.8 元数据结构

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

---

## 七、LangGraph 工作流设计

### 7.1 状态定义

```python
# i3d_agent/workflow/graph_state.py

from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """Agent 状态定义"""

    # 用户输入
    user_id: str
    tenant_id: str
    session_id: str
    messages: Annotated[list, add_messages]

    # 推理过程
    thought: str
    next_action: str

    # 任务路由
    task_type: str  # 'search', 'rag', 'process', 'general'
    assigned_agent: str

    # 搜索相关
    search_query: str
    search_type: str  # '3d', '2d', 'text'
    search_params: dict
    search_results: list

    # RAG 相关
    rag_query: str
    rag_context: list
    rag_answer: str

    # 处理相关
    task_id: str
    task_status: dict

    # 记忆
    memory_context: dict

    # 最终输出
    response: str
    sources: list
```

### 7.2 工作流图

```python
# i3d_agent/workflow/graph.py

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from .graph_state import AgentState
from ..agents import SupervisorAgent, SearchAgent, RAGAgent, ProcessAgent

def create_agent_graph():
    """创建 Agent 工作流图"""

    # 创建状态图
    workflow = StateGraph(AgentState)

    # ============ 节点定义 ============

    def supervisor_node(state: AgentState) -> AgentState:
        """监督者节点 - 任务路由"""
        supervisor = SupervisorAgent()

        # 分析用户意图
        intent = supervisor.analyze_intent(state["messages"][-1].content)

        # 更新状态
        state["task_type"] = intent["task_type"]
        state["assigned_agent"] = intent["agent"]
        state["thought"] = intent["reasoning"]

        return state

    def search_node(state: AgentState) -> AgentState:
        """搜索节点"""
        search_agent = SearchAgent()

        # 执行搜索
        results = search_agent.search(
            query=state["search_query"],
            search_type=state["search_type"],
            params=state["search_params"],
            tenant_id=state["tenant_id"]
        )

        state["search_results"] = results
        state["thought"] = f"完成 {state['search_type']} 搜索，找到 {len(results)} 个结果"

        return state

    def rag_node(state: AgentState) -> AgentState:
        """RAG 节点"""
        rag_agent = RAGAgent()

        # 检索和生成
        response = rag_agent.answer(
            question=state["rag_query"],
            tenant_id=state["tenant_id"]
        )

        state["rag_answer"] = response["answer"]
        state["sources"] = response["sources"]

        return state

    def process_node(state: AgentState) -> AgentState:
        """处理节点"""
        process_agent = ProcessAgent()

        # 查询任务状态
        status = process_agent.get_status(
            task_id=state["task_id"],
            tenant_id=state["tenant_id"]
        )

        state["task_status"] = status

        return state

    def format_response_node(state: AgentState) -> AgentState:
        """格式化响应节点"""
        supervisor = SupervisorAgent()

        # 根据任务类型格式化响应
        if state["task_type"] == "search":
            response = supervisor.format_search_response(
                results=state["search_results"],
                query=state["search_query"]
            )
        elif state["task_type"] == "rag":
            response = supervisor.format_rag_response(
                answer=state["rag_answer"],
                sources=state["sources"]
            )
        elif state["task_type"] == "process":
            response = supervisor.format_process_response(
                status=state["task_status"]
            )
        else:
            response = supervisor.format_general_response(
                messages=state["messages"]
            )

        state["response"] = response
        return state

    # ============ 边定义 ============

    def route_to_agent(state: AgentState) -> str:
        """路由到对应 Agent"""
        task_type = state["task_type"]
        if task_type == "search":
            return "search"
        elif task_type == "rag":
            return "rag"
        elif task_type == "process":
            return "process"
        else:
            return "format"

    def should_continue(state: AgentState) -> str:
        """判断是否继续"""
        if state.get("search_results") or state.get("rag_answer"):
            return "format"
        return END

    # ============ 构建图 ============

    # 添加节点
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("search", search_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("process", process_node)
    workflow.add_node("format", format_response_node)

    # 设置入口
    workflow.set_entry_point("supervisor")

    # 添加边
    workflow.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "search": "search",
            "rag": "rag",
            "process": "process",
            "format": "format"
        }
    )

    workflow.add_edge("search", "format")
    workflow.add_edge("rag", "format")
    workflow.add_edge("process", "format")
    workflow.add_edge("format", END)

    return workflow.compile()
```

---

## 八、API 接口设计

### 8.1 REST API

```python
# i3d_agent/api/routes.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid

app = FastAPI(
    title="I3D Agent API",
    description="I3D 系统智能助手 API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 数据模型 ============

class ChatRequest(BaseModel):
    message: str
    user_id: str
    tenant_id: str = "huabei"
    session_id: Optional[str] = None
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    sources: List[dict] = []
    thought_process: str = ""
    session_id: str

class SearchRequest(BaseModel):
    query: str
    search_type: str = "text"  # 'text', '3d', '2d'
    filters: dict = {}
    top_k: int = 10

class StatusResponse(BaseModel):
    status: str
    version: str
    agents: List[str]

# ============ RAG 专用数据模型 ============

class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    enable_expansion: bool = False
    enable_hyde: bool = False
    enable_rerank: bool = False
    tenant_id: str = "huabei"

class DocumentCreateRequest(BaseModel):
    title: str
    content: str
    doc_type: str = "technical"
    source_type: str = "md"
    metadata: dict = {}
    tags: List[str] = []
    language: str = "zh"
    tenant_id: str = "huabei"

# ============ 端点 ============

@app.get("/", response_model=StatusResponse)
async def root():
    """健康检查"""
    return StatusResponse(
        status="ok",
        version="1.0.0",
        agents=["supervisor", "search", "rag", "process"]
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """智能对话接口"""
    # 生成会话 ID
    session_id = request.session_id or str(uuid.uuid4())

    try:
        # 调用 Agent 工作流
        graph = create_agent_graph()
        result = graph.invoke({
            "user_id": request.user_id,
            "tenant_id": request.tenant_id,
            "session_id": session_id,
            "messages": [{"role": "user", "content": request.message}]
        })

        return ChatResponse(
            response=result["response"],
            sources=result.get("sources", []),
            thought_process=result.get("thought", ""),
            session_id=session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search/agent")
async def agent_search(request: SearchRequest, user_id: str, tenant_id: str = "huabei"):
    """Agent 辅助搜索"""
    graph = create_agent_graph()

    result = graph.invoke({
        "user_id": user_id,
        "tenant_id": tenant_id,
        "session_id": str(uuid.uuid4()),
        "messages": [{"role": "user", "content": request.query}],
        "search_query": request.query,
        "search_type": request.search_type,
        "search_params": {"filters": request.filters, "top_k": request.top_k}
    })

    return {
        "results": result.get("search_results", []),
        "thought_process": result.get("thought", "")
    }

@app.get("/api/memory/{user_id}/history")
async def get_memory_history(
    user_id: str,
    limit: int = 10,
    tenant_id: str = "huabei"
):
    """获取用户记忆历史"""
    memory_manager = MemoryManager()

    recent_searches = memory_manager.get_recent_searches(user_id, limit)

    return {
        "user_id": user_id,
        "recent_searches": recent_searches
    }

@app.delete("/api/memory/{user_id}")
async def clear_memory(user_id: str, tenant_id: str = "huabei"):
    """清除用户记忆"""
    memory_manager = MemoryManager()
    # 实现清除逻辑
    return {"status": "ok", "message": "Memory cleared"}


# ============ RAG 模块 API ============

@app.post("/api/v1/rag/search")
async def rag_search(request: RAGSearchRequest):
    """RAG 检索接口（支持 Agentic 特性）"""
    rag_controller = AgenticRAGController()
    
    results = await rag_controller.search(
        query=request.query,
        top_k=request.top_k,
        enable_expansion=request.enable_expansion,
        enable_hyde=request.enable_hyde,
        enable_rerank=request.enable_rerank,
        tenant_id=request.tenant_id
    )
    
    return {"results": results}


@app.post("/api/v1/rag/ask")
async def rag_ask(request: RAGSearchRequest):
    """RAG 问答接口"""
    rag_controller = AgenticRAGController()
    
    answer = await rag_controller.ask(
        question=request.query,
        tenant_id=request.tenant_id,
        options={
            "top_k": request.top_k,
            "enable_expansion": request.enable_expansion,
            "enable_hyde": request.enable_hyde,
            "enable_rerank": request.enable_rerank
        }
    )
    
    return answer


@app.post("/api/v1/rag/documents", status_code=201)
async def create_document(request: DocumentCreateRequest):
    """创建文档"""
    doc_manager = DocumentManager()
    
    document = await doc_manager.create_document(
        title=request.title,
        content=request.content,
        doc_type=request.doc_type,
        source_type=request.source_type,
        metadata=request.metadata,
        tags=request.tags,
        language=request.language,
        tenant_id=request.tenant_id
    )
    
    return {
        "id": str(document.id),
        "status": "pending",
        "message": "文档创建成功，正在索引中"
    }


@app.get("/api/v1/rag/documents/{doc_id}")
async def get_document(doc_id: str, tenant_id: str = "huabei"):
    """获取文档详情"""
    doc_manager = DocumentManager()
    
    document = await doc_manager.get_document(
        doc_id=doc_id,
        tenant_id=tenant_id
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document


@app.put("/api/v1/rag/documents/{doc_id}")
async def update_document(
    doc_id: str,
    request: DocumentCreateRequest,
    tenant_id: str = "huabei"
):
    """更新文档（创建新版本）"""
    doc_manager = DocumentManager()
    
    document = await doc_manager.update_document(
        doc_id=doc_id,
        title=request.title,
        content=request.content,
        doc_type=request.doc_type,
        metadata=request.metadata,
        tenant_id=tenant_id
    )
    
    return {
        "id": str(document.id),
        "version": document.version,
        "status": "pending",
        "message": "文档更新成功，正在重新索引"
    }


@app.delete("/api/v1/rag/documents/{doc_id}")
async def delete_document(doc_id: str, tenant_id: str = "huabei"):
    """删除文档（软删除）"""
    doc_manager = DocumentManager()
    
    success = await doc_manager.delete_document(
        doc_id=doc_id,
        tenant_id=tenant_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"status": "ok", "message": "Document deleted"}


@app.post("/api/v1/rag/documents/{doc_id}/restore")
async def restore_document(doc_id: str, tenant_id: str = "huabei"):
    """恢复已删除的文档"""
    doc_manager = DocumentManager()
    
    document = await doc_manager.restore_document(
        doc_id=doc_id,
        tenant_id=tenant_id
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found or cannot be restored")
    
    return document


@app.get("/api/v1/rag/documents/{doc_id}/history")
async def get_document_history(doc_id: str, tenant_id: str = "huabei"):
    """获取文档版本历史"""
    doc_manager = DocumentManager()
    
    history = await doc_manager.get_document_history(
        doc_id=doc_id,
        tenant_id=tenant_id
    )
    
    return {"versions": history}


@app.get("/api/v1/rag/documents")
async def list_documents(
    tenant_id: str = "huabei",
    doc_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """列出文档"""
    doc_manager = DocumentManager()
    
    documents, total = await doc_manager.list_documents(
        tenant_id=tenant_id,
        doc_type=doc_type,
        page=page,
        page_size=page_size
    )
    
    return {
        "documents": documents,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@app.get("/api/v1/rag/index/status")
async def get_index_status(tenant_id: str = "huabei"):
    """获取索引状态"""
    monitor = MonitorService()
    
    status = await monitor.get_index_status(tenant_id)
    
    return status


@app.get("/api/v1/rag/index/queue")
async def get_index_queue(tenant_id: str = "huabei"):
    """获取索引队列"""
    doc_manager = DocumentManager()
    
    queue = await doc_manager.get_index_queue(tenant_id)
    
    return {"queue": queue}


@app.get("/api/v1/rag/metrics")
async def get_rag_metrics(
    tenant_id: str = "huabei",
    hours: int = 24
):
    """获取 RAG 性能指标"""
    monitor = MonitorService()
    
    metrics = await monitor.get_metrics(tenant_id, hours)
    
    return metrics


@app.post("/api/v1/rag/feedback")
async def submit_feedback(
    query: str,
    rating: int,
    is_helpful: bool,
    answer: str,
    sources: List[dict],
    tenant_id: str = "huabei",
    session_id: Optional[str] = None,
    feedback_text: Optional[str] = None
):
    """提交反馈"""
    monitor = MonitorService()
    
    feedback_id = await monitor.record_feedback(
        tenant_id=tenant_id,
        session_id=session_id,
        query=query,
        rating=rating,
        is_helpful=is_helpful,
        answer=answer,
        sources=sources,
        feedback_text=feedback_text
    )
    
    return {"feedback_id": str(feedback_id), "status": "recorded"}
```

### 8.2 WebSocket 接口

```python
# i3d_agent/api/websocket.py

from fastapi import WebSocket
from typing import Dict
import json

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 对话接口"""
    await websocket.accept()

    session_id = str(uuid.uuid4())
    graph = create_agent_graph()

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            message = data.get("message")
            user_id = data.get("user_id")
            tenant_id = data.get("tenant_id", "huabei")

            # 流式响应
            await websocket.send_json({
                "type": "thinking",
                "message": "正在思考..."
            })

            # 调用 Agent
            result = graph.invoke({
                "user_id": user_id,
                "tenant_id": tenant_id,
                "session_id": session_id,
                "messages": [{"role": "user", "content": message}]
            })

            # 发送结果
            await websocket.send_json({
                "type": "response",
                "response": result["response"],
                "sources": result.get("sources", []),
                "session_id": session_id
            })

    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
```

---

## 九、数据库设计

### 9.1 新增表结构

```sql
-- ============ Agent 记忆表 ============

-- 语义记忆表 (向量存储)
CREATE TABLE agent_semantic_memory (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT,
    content TEXT NOT NULL,
    content_type TEXT DEFAULT 'text',  -- 'text', 'json', 'code'
    embedding VECTOR(512),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- HNSW 索引
CREATE INDEX idx_agent_memory_embedding
ON agent_semantic_memory
USING hnsw (embedding vector_cosine_ops);

-- 复合索引
CREATE INDEX idx_agent_memory_user
ON agent_semantic_memory(tenant_id, user_id, created_at DESC);

-- RLS 策略
ALTER TABLE agent_semantic_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_semantic_memory_tenant_policy
ON agent_semantic_memory
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true));


-- ============ Agent 对话历史表 ============

CREATE TABLE agent_conversation_history (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    message_type TEXT NOT NULL,  -- 'user', 'agent', 'system'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',  -- 包含 tokens, latency, model 等
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversation_session
ON agent_conversation_history(tenant_id, user_id, session_id, created_at);

-- RLS 策略
ALTER TABLE agent_conversation_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_conversation_tenant_policy
ON agent_conversation_history
FOR SELECT
USING (tenant_id = current_setting('app.current_tenant', true));


-- ============ Agent 任务表 ============

CREATE TABLE agent_tasks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    task_type TEXT NOT NULL,  -- 'search', 'rag', 'process'
    task_data JSONB NOT NULL,
    status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_agent_tasks_user
ON agent_tasks(tenant_id, user_id, created_at DESC);

CREATE INDEX idx_agent_tasks_status
ON agent_tasks(tenant_id, status, created_at);

-- RLS 策略
ALTER TABLE agent_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_tasks_tenant_policy
ON agent_tasks
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true));


-- ============ RAG 知识库表（增强版） ============

-- rag_documents（文档元数据表）
CREATE TABLE rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    doc_type VARCHAR(50) NOT NULL,  -- 'technical', 'business', 'api'
    source_type VARCHAR(50),  -- 'md', 'pdf', 'html'
    raw_content TEXT,
    content_hash VARCHAR(64),
    version INT DEFAULT 1,
    is_latest BOOLEAN DEFAULT true,
    parent_doc_id UUID REFERENCES rag_documents(id),
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'indexed', 'failed'
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    language VARCHAR(10) DEFAULT 'zh',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

-- HNSW 索引（元数据）
CREATE INDEX idx_rag_docs_metadata
ON rag_documents USING GIN (metadata);

CREATE INDEX idx_rag_docs_tenant_type
ON rag_documents(tenant_id, doc_type, is_latest);

-- RLS 策略
ALTER TABLE rag_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY rag_documents_tenant_policy
ON rag_documents
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true));


-- rag_chunks（文档分块表）
CREATE TABLE rag_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    tenant_id VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, ''))) STORED,
    chunk_index INT NOT NULL,
    token_count INT,
    metadata JSONB DEFAULT '{}',
    doc_version INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

-- HNSW 索引（向量检索）
CREATE INDEX idx_rag_chunks_embedding
ON rag_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- GIN 索引（全文搜索）
CREATE INDEX idx_rag_chunks_tsv
ON rag_chunks USING GIN (content_tsv);

-- 复合索引
CREATE INDEX idx_rag_chunks_doc_version
ON rag_chunks(doc_id, doc_version, chunk_index);

-- RLS 策略
ALTER TABLE rag_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY rag_chunks_tenant_policy
ON rag_chunks
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true));


-- rag_versions（版本历史表）
CREATE TABLE rag_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    tenant_id VARCHAR(100) NOT NULL,
    version INT NOT NULL,
    content_snapshot TEXT,
    chunk_count INT DEFAULT 0,
    change_type VARCHAR(20),  -- 'create', 'update', 'delete'
    change_reason TEXT,
    changed_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rag_versions_doc
ON rag_versions(doc_id, version);


-- rag_index_queue（增量索引队列表）
CREATE TABLE rag_index_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    tenant_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    operation VARCHAR(20) NOT NULL,  -- 'create', 'update', 'delete'
    priority INT DEFAULT 5,
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_rag_queue_status_priority
ON rag_index_queue(status, priority, created_at);


-- rag_metrics（性能指标表）
CREATE TABLE rag_metrics (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    tags JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rag_metrics_tenant_time
ON rag_metrics(tenant_id, metric_name, timestamp DESC);


-- rag_feedback（质量反馈表）
CREATE TABLE rag_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    query TEXT NOT NULL,
    retrieved_doc_ids UUID[],
    rating INT CHECK (rating >= 1 AND rating <= 5),
    is_helpful BOOLEAN,
    thumb_up BOOLEAN,
    feedback_text TEXT,
    answer TEXT,
    sources JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rag_feedback_tenant
ON rag_feedback(tenant_id, created_at DESC);


-- ============ Agent 反馈表 ============

CREATE TABLE agent_feedback (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT,
    message_id BIGINT,
    feedback_type TEXT NOT NULL,  -- 'thumbs_up', 'thumbs_down', 'report'
    feedback_text TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agent_feedback_user
ON agent_feedback(tenant_id, user_id, created_at DESC);

-- RLS 策略
ALTER TABLE agent_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_feedback_tenant_policy
ON agent_feedback
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true));
```

### 9.2 RAG 模块配置

```python
# i3d_agent/config/settings.py

from pydantic_settings import BaseSettings
from typing import Dict


class RAGSettings(BaseSettings):
    """RAG 模块配置"""
    
    # ========== 文档存储路径 ==========
    RAG_DATA_PATH: str = "./data/rag"
    RAG_DOCUMENTS_PATH: str = "./data/rag/documents"
    
    # ========== 切分配置 ==========
    CHUNK_SIZE_DEFAULT: int = 800
    CHUNK_OVERLAP_DEFAULT: int = 150
    CHUNK_SIZE_BY_TYPE: Dict[str, int] = {
        "technical": 1000,
        "business": 600,
        "api": 500
    }
    
    # ========== 检索配置 ==========
    RAG_TOP_K_RESULTS: int = 10
    RAG_SIMILARITY_THRESHOLD: float = 0.7
    RAG_RERANK_TOP_K: int = 5
    
    # ========== 混合检索权重 ==========
    # 根据查询类型动态调整
    HYBRID_ALPHA_SEMANTIC: float = 0.7      # 语义查询
    HYBRID_ALPHA_KEYWORD: float = 0.3       # 关键词查询
    HYBRID_ALPHA_BALANCED: float = 0.5       # 平衡查询
    HYBRID_ALPHA_EXACT: float = 0.1         # 精确匹配
    
    # ========== Agentic 配置 ==========
    AGENTIC_QUERY_EXPANSION_COUNT: int = 3   # 查询扩展数量
    AGENTIC_MAX_ITERATIONS: int = 3         # 多步推理最大迭代次数
    AGENTIC_ENABLE_HYDE: bool = True        # 启用 HyDE
    AGENTIC_ENABLE_RERANK: bool = True      # 启用重排序
    
    # ========== Rerank 配置 ==========
    RERANK_PROVIDER: str = "cohere"         # 'cohere', 'local'
    RERANK_MODEL: str = "rerank-english-v2.0"
    COHERE_API_KEY: str = ""
    
    # ========== 索引配置 ==========
    INDEX_BATCH_SIZE: int = 10              # 批量索引大小
    INDEX_WORKER_CONCURRENCY: int = 2        # Worker 并发数
    INDEX_QUEUE_MAX_SIZE: int = 1000         # 队列最大长度
    
    # ========== Embedding 配置 ==========
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    EMBEDDING_BATCH_SIZE: int = 100
    
    # ========== LLM 配置 ==========
    RAG_LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    RAG_LLM_TEMPERATURE: float = 0
    RAG_LLM_MAX_TOKENS: int = 2000
    
    # ========== 监控配置 ==========
    RAG_ENABLE_METRICS: bool = True
    RAG_METRICS_RETENTION_HOURS: int = 168  # 7天
    RAG_ENABLE_FEEDBACK: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# ========== 查询类型映射 ==========
QUERY_TYPE_ALPHA = {
    "semantic": 0.7,
    "keyword": 0.3,
    "balanced": 0.5,
    "exact_match": 0.1
}


# ========== 文档类型配置 ==========
DOCUMENT_TYPE_CONFIG = {
    "technical": {
        "chunk_size": 1000,
        "overlap": 150,
        "strategy": "semantic_boundary"
    },
    "business": {
        "chunk_size": 600,
        "overlap": 100,
        "strategy": "paragraph"
    },
    "api": {
        "chunk_size": 500,
        "overlap": 0,
        "strategy": "endpoint"
    },
    "markdown": {
        "chunk_size": 800,
        "overlap": 100,
        "strategy": "heading_hierarchy"
    },
    "pdf": {
        "chunk_size": 800,
        "overlap": 100,
        "strategy": "page_paragraph"
    }
}
```

---

## 十、部署方案

### 10.1 目录结构

```
i3d_agent/
├── api/                          # FastAPI 接口
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用
│   ├── routes.py                 # 路由定义
│   ├── rag_routes.py             # RAG 专用路由
│   └── websocket.py              # WebSocket 处理
├── agents/                       # Agent 实现
│   ├── __init__.py
│   ├── supervisor.py             # 监督者 Agent
│   ├── search.py                 # 搜索 Agent
│   ├── rag.py                    # RAG Agent（增强版）
│   └── process.py                # 处理 Agent
├── tools/                        # 工具定义
│   ├── __init__.py
│   ├── search_tools.py
│   ├── rag_tools.py              # RAG 工具（增强版）
│   └── process_tools.py
├── workflow/                     # LangGraph 工作流
│   ├── __init__.py
│   ├── graph.py                  # 工作流图
│   └── graph_state.py            # 状态定义
├── memory/                       # 记忆系统
│   ├── __init__.py
│   ├── memory_manager.py         # 记忆管理器
│   └── prompts.py                # 提示模板
├── rag/                          # RAG 模块（增强版）
│   ├── __init__.py
│   ├── controller.py             # Agentic RAG 控制器
│   ├── document_manager.py       # 文档管理器
│   ├── processor.py              # 文档处理器（切分、embedding）
│   ├── retrieval.py              # 检索引擎（混合检索）
│   ├── rerank.py                 # 重排序服务
│   ├── hyde.py                   # HyDE 实现
│   ├── query_expansion.py        # 查询扩展
│   ├── monitor.py                # 监控服务
│   ├── index_worker.py           # 索引 Worker
│   ├── models.py                 # RAG 数据模型
│   └── rag_service.py            # RAG 服务
├── config/                       # 配置
│   ├── __init__.py
│   ├── settings.py               # 应用配置（含 RAG 配置）
│   └── prompts.py                # 提示模板
├── utils/                        # 工具函数
│   ├── __init__.py
│   ├── logger.py                 # 日志
│   ├── telemetry.py              # 可观测性
│   └── embedding.py              # Embedding 工具
├── tests/                        # 测试
│   ├── test_agents.py
│   ├── test_tools.py
│   ├── test_workflow.py
│   ├── test_rag/                 # RAG 测试
│   │   ├── test_retrieval.py
│   │   ├── test_rerank.py
│   │   └── test_hyde.py
│   └── test_integration.py
├── docker/                       # Docker 配置
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/                         # 文档
│   └── rag/                      # RAG 文档
│       ├── architecture.md
│       └── api.md
├── requirements.txt              # 依赖（含 RAG 相关）
├── pyproject.toml               # 项目配置
└── README.md
```

### 10.2 Docker 部署

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  i3d-agent:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: i3d-agent
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://app_user:app_pass@postgres:15432/i3d_multitenant
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ../logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - i3d-network

  postgres:
    image: pgvector/pgvector:pg15
    container_name: i3d-postgres
    ports:
      - "15432:5432"
    environment:
      - POSTGRES_USER=app_user
      - POSTGRES_PASSWORD=app_pass
      - POSTGRES_DB=i3d_multitenant
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - i3d-network

  redis:
    image: redis:7-alpine
    container_name: i3d-redis
    ports:
      - "6379:6379"
    networks:
      - i3d-network

  phoenix:  # 可观测性
    image: arizephoenix/phoenix:latest
    container_name: i3d-phoenix
    ports:
      - "6006:6006"
    environment:
      - PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
    networks:
      - i3d-network

volumes:
  postgres_data:

networks:
  i3d-network:
    external: true
```

### 10.3 Dockerfile

```dockerfile
# docker/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 十一、实施计划

### 11.1 阶段划分

```
阶段一: 基础设施 (2-3周)
├── Week 1
│   ├─ 项目初始化
│   ├─ 数据库表创建（含 RAG 表）
│   ├─ 基础工具封装
│   └─ 开发环境搭建
└── Week 2-3
    ├─ RAG 数据模型实现
    ├─ Document Manager 实现
    ├─ 文档处理器实现（切分、embedding）
    ├─ 索引队列与 Worker 实现
    ├─ 记忆系统实现
    └─ API 接口框架

阶段二: 核心检索 (1-2周)
├── Week 4
│   ├─ 向量检索引擎实现
│   ├─ BM25 全文检索实现
│   ├─ 混合检索融合实现
│   └─ 检索 API 实现
└── Week 5
    ├─ RAG Agent 基础版
    ├─ 检索结果评估
    └─ Search Agent 实现

阶段三: Agentic 特性 (2-3周)
├── Week 6
│   ├─ 查询扩展实现
│   ├─ HyDE 实现
│   └─ 去重合并实现
├── Week 7
│   ├─ 重排序服务实现
│   ├─ 多步推理实现
│   └─ Agentic Controller 实现
└── Week 8
    ├─ RAG Agent 增强版
    ├─ 工作流集成
    └─ 初步测试

阶段四: 高级功能 (1-2周)
├── Week 9
│   ├─ 版本管理实现
│   ├─ 监控指标实现
│   ├─ 质量反馈实现
│   └─ 监控 API 实现
└── Week 10
    ├─ Supervisor Agent
    ├─ Process Agent
    └─ Grafana 仪表板

阶段五: 集成测试 (2周)
├── Week 11
│   ├─ 单元测试
│   ├─ 集成测试
│   └─ 性能测试
└── Week 12
    ├─ 用户验收测试
    ├─ Bug 修复
    └─ 文档完善

阶段六: 生产部署 (1周)
├── Week 13
│   ├─ Docker 镜像构建
│   ├─ 生产环境部署
│   ├─ 监控配置
│   └─ 上线验证
```

### 11.2 里程碑

| 里程碑 | 交付物 | 时间 |
|--------|--------|------|
| M1 | 基础设施完成 | Week 3 |
| M2 | 核心检索可用 | Week 5 |
| M3 | Agentic RAG 完成 | Week 8 |
| M4 | 高级功能完成 | Week 10 |
| M5 | 完整功能测试 | Week 12 |
| M6 | 生产环境上线 | Week 13 |

### 11.3 RAG 模块实施细节

#### Phase 1: 基础设施（2-3周）
- 数据库表创建（rag_documents, rag_chunks, rag_versions, rag_index_queue, rag_metrics, rag_feedback）
- 基础数据模型（Document, Chunk, Version, IndexQueue）
- Document Manager CRUD 操作
- 文档处理器（支持 Markdown、PDF、HTML）
- Embedding 服务集成
- 索引队列和异步 Worker
- 基础 API（创建、查询、删除文档）

#### Phase 2: 核心检索（1-2周）
- 向量检索（pgvector HNSW）
- BM25 全文检索（PostgreSQL GIN）
- 混合检索融合算法
- 动态权重调整
- 检索 API 开发

#### Phase 3: Agentic 特性（2-3周）
- 查询扩展（生成 3-5 种变体）
- HyDE（假设文档生成与检索）
- 去重与合并
- 重排序服务（Cohere API / 本地模型）
- 多步推理循环
- Agentic Controller

#### Phase 4: 高级功能（1-2周）
- 版本管理（版本历史、回滚）
- 监控指标（检索延迟、队列状态）
- 质量反馈（用户评分、有用性）
- 监控 API
- Grafana 仪表板

#### Phase 5: 优化与上线（1周）
- 性能优化（缓存、批处理）
- 文档完善
- 部署配置
- 上线验证

---

## 十二、总结

本设计方案为 I3D 系统提供了一个完整的 Agent 架构解决方案，集成了增强的 RAG 模块：

### 核心特点

1. **复用现有设施**: pgvector、Redis、PostgreSQL、RabbitMQ
2. **多租户隔离**: 通过 RLS 和租户上下文实现
3. **模块化设计**: Agent、工具、记忆系统、RAG 模块独立可测试
4. **可观测性**: Arize Phoenix + Prometheus 集成
5. **生产级**: 完整的错误处理、日志、监控

### 技术亮点

- LangGraph 状态图编排
- 三层记忆架构
- **Agentic RAG**: 查询扩展、HyDE、重排序、多步推理
- **混合检索**: 向量检索 + BM25 全文检索
- **增量索引**: 新文档无需全量重建
- **版本管理**: 文档更新历史追踪和回滚
- WebSocket 流式响应
- 完整的评估体系

### RAG 模块新增特性

| 特性 | 描述 | 价值 |
|------|------|------|
| 查询扩展 | 生成 3-5 种查询变体 | 提高召回率 |
| HyDE | 假设文档生成与检索 | 改善语义匹配 |
| 混合检索 | 向量 + BM25 融合 | 兼顾语义和关键词 |
| 重排序 | Cohere/本地模型精排 | 提升准确率 |
| 多步推理 | 迭代检索直到满意 | 处理复杂查询 |
| 增量索引 | 队列 + 异步处理 | 高时效性 |
| 版本管理 | 历史追踪与回滚 | 可追溯性 |
| 监控仪表板 | 性能指标可视化 | 运维友好 |

### 下一步行动

1. 评审本设计方案
2. 确认技术选型和资源
3. 启动阶段一开发（基础设施）
4. 建立定期同步机制
5. 准备 RAG 模块详细设计文档

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
│  │                        基础设施层 (复用)                               │  │
│  │                                                                       │  │
│  │  PostgreSQL ─ pgvector ─ RabbitMQ ─ Redis ─ MinIO                     │  │
│  │     (15432)      (向量)      (5672)    (6379)   (9000)                 │  │
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
    """

    role = "I3D 技术文档专家"
    goal = "从技术文档中回答用户问题"
    backstory = """
    你是 I3D 系统的技术文档专家，熟悉：
    - API 使用方法和参数说明
    - 系统架构和组件关系
    - 部署和运维指南
    - 故障排查和最佳实践
    """

    # 知识库范围
    knowledge_bases = {
        "api_docs": "API 接口文档",
        "user_guide": "用户使用手册",
        "deploy_guide": "部署运维指南",
        "architecture": "系统架构文档",
        "troubleshooting": "故障排查手册"
    }

    # 工具
    tools = [
        retrieve_documents,
        search_api_reference,
        get_deployment_guide,
        find_troubleshooting_steps
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

### 4.2 知识库工具组

```python
# i3d_agent/tools/rag_tools.py

from langchain.tools import tool
from typing import List, Optional
import httpx

@tool
def retrieve_documents(
    query: str,
    knowledge_base: str = "all",
    top_k: int = 5,
    tenant_id: str = "huabei"
) -> List[dict]:
    """
    从技术文档知识库中检索相关文档

    Args:
        query: 查询问题
        knowledge_base: 知识库类型 (api_docs/user_guide/deploy_guide/all)
        top_k: 返回文档数量
        tenant_id: 租户ID

    Returns:
        相关文档列表，包含内容和相似度
    """
    url = "http://localhost:8000/api/rag/retrieve"
    payload = {
        "query": query,
        "knowledge_base": knowledge_base,
        "top_k": top_k
    }
    headers = {"X-Tenant-ID": tenant_id}

    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=headers)
        return response.json().get("documents", [])


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
    url = "http://localhost:8000/api/rag/api-docs"
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
    url = "http://localhost:8000/api/rag/deploy-guide"
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
    url = "http://localhost:8000/api/rag/troubleshoot"
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

### 6.2 RAG 服务实现

```python
# i3d_agent/rag/rag_service.py

from typing import List, Optional
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import PGVector
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatAnthropic
from langchain.prompts import PromptTemplate

class RAGService:
    """RAG 知识库服务"""

    def __init__(self):
        # 嵌入模型
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            dimensions=512  # 与 pgvector 一致
        )

        # 向量存储 (复用 pgvector)
        self.vectorstore = PGVector(
            connection_string="postgresql://app_user:app_pass@localhost:15432/i3d_multitenant",
            embedding_function=self.embeddings,
            collection_name="rag_documents",
            distance_strategy="cosine"
        )

        # LLM
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0,
            max_tokens=2000
        )

        # 提示模板
        self.prompt_template = PromptTemplate(
            template="""你是一个 I3D 3D CAD 系统的技术支持专家。
请基于以下技术文档回答用户的问题。如果文档中没有相关信息，请明确说明。

技术文档:
{context}

用户问题:
{question}

请提供详细、准确的回答，并在回答中引用相关的文档部分。
""",
            input_variables=["context", "question"]
        )

    def retrieve(self, query: str, top_k: int = 5, filters: dict = None) -> List[dict]:
        """检索相关文档"""
        search_kwargs = {"k": top_k}
        if filters:
            search_kwargs["filter"] = filters

        docs = self.vectorstore.similarity_search(
            query,
            **search_kwargs
        )

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": getattr(doc, 'score', None)
            }
            for doc in docs
        ]

    def answer(self, question: str, tenant_id: str = "huabei") -> dict:
        """生成回答"""
        # 设置租户上下文
        filters = {"tenant_id": tenant_id}

        # 检索
        docs = self.retrieve(question, top_k=5, filters=filters)

        # 构建上下文
        context = "\n\n".join([
            f"【{doc['metadata'].get('title', '文档')}】\n{doc['content']}"
            for doc in docs
        ])

        # 生成回答
        prompt = self.prompt_template.format(
            context=context,
            question=question
        )

        response = self.llm.predict(prompt)

        return {
            "answer": response,
            "sources": [
                {
                    "title": doc["metadata"].get("title"),
                    "source": doc["metadata"].get("source"),
                    "score": doc.get("score")
                }
                for doc in docs
            ]
        }

    def ingest_document(
        self,
        content: str,
        metadata: dict,
        tenant_id: str
    ):
        """导入文档到知识库"""
        metadata["tenant_id"] = tenant_id

        self.vectorstore.add_texts(
            texts=[content],
            metadatas=[metadata]
        )
```

### 6.3 文档处理管道

```python
# i3d_agent/rag/document_processor.py

from pathlib import Path
from typing import List, Dict
import markdown
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentProcessor:
    """文档处理器"""

    def __init__(self):
        # 文本分割器
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        )

    def process_markdown(self, file_path: Path, metadata: dict) -> List[dict]:
        """处理 Markdown 文档"""
        # 读取内容
        content = file_path.read_text(encoding="utf-8")

        # 解析 Markdown
        html = markdown.markdown(content)
        soup = BeautifulSoup(html, 'html.parser')

        # 提取标题和段落
        sections = []
        current_section = {"title": metadata.get("title", ""), "content": []}

        for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'code']):
            if element.name in ['h1', 'h2', 'h3']:
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {
                    "title": element.get_text(),
                    "content": []
                }
            else:
                text = element.get_text(strip=True)
                if text:
                    current_section["content"].append(text)

        if current_section["content"]:
            sections.append(current_section)

        # 分割成块
        chunks = []
        for section in sections:
            section_text = "\n".join(section["content"])
            section_chunks = self.splitter.split_text(section_text)

            for i, chunk in enumerate(section_chunks):
                chunks.append({
                    "content": chunk,
                    "metadata": {
                        **metadata,
                        "section": section["title"],
                        "chunk_index": i
                    }
                })

        return chunks

    def process_directory(
        self,
        directory: Path,
        base_metadata: dict
    ) -> List[dict]:
        """处理整个目录"""
        all_chunks = []

        for md_file in directory.rglob("*.md"):
            file_metadata = {
                **base_metadata,
                "source": str(md_file.relative_to(directory)),
                "title": md_file.stem
            }
            chunks = self.process_markdown(md_file, file_metadata)
            all_chunks.extend(chunks)

        return all_chunks
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


-- ============ RAG 知识库表 ============

CREATE TABLE rag_documents (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,  -- 文档唯一标识
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding VECTOR(512),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, doc_id, chunk_index)
);

-- HNSW 索引
CREATE INDEX idx_rag_docs_embedding
ON rag_documents
USING hnsw (embedding vector_cosine_ops);

-- 元数据索引
CREATE INDEX idx_rag_docs_metadata
ON rag_documents USING GIN (metadata);

-- RLS 策略
ALTER TABLE rag_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY rag_documents_tenant_policy
ON rag_documents
FOR ALL
USING (tenant_id = current_setting('app.current_tenant', true));


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

---

## 十、部署方案

### 10.1 目录结构

```
i3d_agent/
├── api/                          # FastAPI 接口
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用
│   ├── routes.py                 # 路由定义
│   └── websocket.py              # WebSocket 处理
├── agents/                       # Agent 实现
│   ├── __init__.py
│   ├── supervisor.py             # 监督者 Agent
│   ├── search.py                 # 搜索 Agent
│   ├── rag.py                    # RAG Agent
│   └── process.py                # 处理 Agent
├── tools/                        # 工具定义
│   ├── __init__.py
│   ├── search_tools.py
│   ├── rag_tools.py
│   └── process_tools.py
├── workflow/                     # LangGraph 工作流
│   ├── __init__.py
│   ├── graph.py                  # 工作流图
│   └── graph_state.py            # 状态定义
├── memory/                       # 记忆系统
│   ├── __init__.py
│   ├── memory_manager.py         # 记忆管理器
│   └── prompts.py                # 提示模板
├── rag/                          # RAG 服务
│   ├── __init__.py
│   ├── rag_service.py            # RAG 服务
│   └── document_processor.py     # 文档处理
├── config/                       # 配置
│   ├── __init__.py
│   ├── settings.py               # 应用配置
│   └── prompts.py                # 提示模板
├── utils/                        # 工具函数
│   ├── __init__.py
│   ├── logger.py                 # 日志
│   └── telemetry.py              # 可观测性
├── tests/                        # 测试
│   ├── test_agents.py
│   ├── test_tools.py
│   └── test_workflow.py
├── docker/                       # Docker 配置
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt              # 依赖
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
阶段一: 基础设施 (2周)
├── Week 1
│   ├─ 项目初始化
│   ├─ 数据库表创建
│   ├─ 基础工具封装
│   └─ 开发环境搭建
└── Week 2
    ├─ RAG 服务搭建
    ├─ 记忆系统实现
    └─ API 接口框架

阶段二: Agent 实现 (3周)
├── Week 3
│   ├─ Search Agent
│   ├─ RAG Agent
│   └─ 基础工具测试
├── Week 4
│   ├─ Supervisor Agent
│   ├─ Process Agent
│   └─ 工作流集成
└── Week 5
    ├─ WebSocket 支持
    ├─ 错误处理
    └─ 初步测试

阶段三: 集成测试 (2周)
├── Week 6
│   ├─ 单元测试
│   ├─ 集成测试
│   └─ 性能测试
└── Week 7
    ├─ 用户验收测试
    ├─ Bug 修复
    └─ 文档完善

阶段四: 生产部署 (1周)
├── Week 8
│   ├─ Docker 镜像构建
│   ├─ 生产环境部署
│   ├─ 监控配置
│   └─ 上线验证
```

### 11.2 里程碑

| 里程碑 | 交付物 | 时间 |
|--------|--------|------|
| M1 | 基础设施完成 | Week 2 |
| M2 | Agent 原型可用 | Week 4 |
| M3 | 完整功能测试 | Week 7 |
| M4 | 生产环境上线 | Week 8 |

---

## 十二、总结

本设计方案为 I3D 系统提供了一个完整的 Agent 架构解决方案：

### 核心特点

1. **复用现有设施**: pgvector、Redis、PostgreSQL、RabbitMQ
2. **多租户隔离**: 通过 RLS 和租户上下文实现
3. **模块化设计**: Agent、工具、记忆系统独立可测试
4. **可观测性**: Arize Phoenix 集成
5. **生产级**: 完整的错误处理、日志、监控

### 技术亮点

- LangGraph 状态图编排
- 三层记忆架构
- RAG 知识库增强
- WebSocket 流式响应
- 完整的评估体系

### 下一步行动

1. 评审本设计方案
2. 确认技术选型和资源
3. 启动阶段一开发
4. 建立定期同步机制

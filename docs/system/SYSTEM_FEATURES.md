# I3D 3D CAD 智能检索与处理系统 - 功能清单

> 文档创建时间: 2026-05-26
> 系统版本: Cloud-Native Multi-Tenant (PostgreSQL + RLS)

---

## 系统概述

I3D 系统是一个综合性的 **3D CAD 智能检索与处理系统**，采用云原生多租户架构，支持从文件处理、特征提取到智能搜索的完整能力链路。

### 核心特点

- **云原生多租户架构**: PostgreSQL + RLS (Row-Level Security) 单数据库多租户隔离
- **微服务协作**: 5 个独立微服务协同工作
- **AI 智能推理**: 深度学习模型特征提取与相似度搜索
- **多设备支持**: GPU/NPU/CPU 推理后端

---

## 子项目功能清单

### 1. InferEngineer-3dRetrieval (搜索服务)

**路径**: `/data/i3d_migrate_arm/InferEngineer-3dRetrieval`
**技术栈**: Django 4.2+ + PostgreSQL pgvector
**端口**: 8000/18000


| 功能模块         | 功能说明                                         |
| ---------------- | ------------------------------------------------ |
| **2D 图片搜索**  | 上传 2D 图片搜索相似的 3D 零件                   |
| **3D 模型搜索**  | 上传 3D 模型文件进行相似度搜索                   |
| **特征点选搜索** | 通过点选模型特征进行搜索                         |
| **属性过滤**     | 基于 PLM 属性（材质、尺寸、状态等）过滤搜索结果  |
| **向量搜索**     | 基于 PostgreSQL pgvector 的 512 维向量相似度搜索 |
| **多租户隔离**   | 支持 shenfa/meidi/dongjiang/huabei 四个租户      |
| **API 文档**     | Swagger/OpenAPI 自动生成                         |

**核心 API**:

- `POST /api/search/searchBy2D` - 2D 图片搜索
- `POST /api/search/searchBy3D` - 3D 模型搜索
- `POST /api/search/featureSearch` - 特征点选搜索

---

### 2. 3d-search-core (推理服务)

**路径**: `/data/i3d_migrate_arm/3d-search-core`
**技术栈**: Django 4.2+ + PyTorch/ONNX Runtime
**端口**: 28000/8081


| 功能模块         | 功能说明                                           |
| ---------------- | -------------------------------------------------- |
| **3D 模型推理**  | 提取 3D CAD 模型（零部件/产品级）的 512 维特征向量 |
| **2D 图片推理**  | 提取 2D 图片（三视图/剖面图）的 512 维特征向量     |
| **批量推理**     | 支持批量文件异步处理                               |
| **局部特征推理** | 基于 AAGNet 和 PyTorch 的局部特征提取              |
| **多设备支持**   | GPU (CUDA)、NPU (华为昇腾)、CPU 推理后端           |
| **模型管理**     | LRU 缓存 + ONNX 实例池                             |
| **回调机制**     | 支持华贝客户定制回调接口                           |

**推理类型** (insert_type):

- `[1]` - 3D 全局特征
- `[2]` - 3D 局部特征
- `[3]` - 2D 三视图
- `[4]` - 2D 剖面图
- `[1,3]` - 3D+2D 组合

**核心 API**:

- `POST /api/huabei/modelinfer/create_batch_infer_3d` - 批量 3D 推理
- `POST /api/huabei/modelinfer/create_batch_infer_2d` - 批量 2D 推理
- `POST /api/huabei/modelinfer/fea_extraction_3dwhole` - 查询特征提取

---

### 3. minio-api (批处理调度服务)

**路径**: `/data/i3d_migrate_arm/minio-api`
**技术栈**: Django 4.2+ + Celery + RabbitMQ
**端口**: 48000/19010


| 功能模块          | 功能说明                                  |
| ----------------- | ----------------------------------------- |
| **ZIP 批量处理**  | 解压并批量上传文件到 MinIO                |
| **智能任务调度**  | RedisTaskQueue 智能批处理任务调度         |
| **文件入库**      | 文件入库与查询任务处理                    |
| **批量推理调用**  | 调用 3D/2D 批量推理 API                   |
| **RabbitMQ 消费** | 消息队列消费与处理                        |
| **查询直调链路**  | xxl_job_executor 完成后直接调用的查询处理 |
| **仅上传链路**    | 仅上传文件不执行推理                      |

**处理流程**:

```
MQ消息 → RabbitMQConsumer → MessageHandler → Celery Queue → Worker → 执行锁检查 → 入库主链路
```

**核心 API**:

- `POST /api/v1/file-processor/query-process/` - 查询直调处理
- `POST /api/v1/file-processor/upload-only-process/` - 仅上传处理

---

### 4. 3d-desktopprogram (桌面客户端)

**路径**: `/data/i3d_migrate_arm/3d-desktopprogram`
**技术栈**: Electron 22 + Vue 3 + TypeScript
**端口**: 5678/5173


| 功能模块        | 功能说明                                   |
| --------------- | ------------------------------------------ |
| **3D 模型搜索** | 三维 AI 智能搜索软件 V2.01                 |
| **3D 模型查看** | 基于 NDSWebViewer 和 Three.js 的模型可视化 |
| **3D 模型管理** | 模型文件的管理和组织                       |
| **微前端架构**  | 基于 Qiankun 的微前端                      |
| **多租户支持**  | 默认租户 huabei，支持国创/东江/美的        |

**应用结构**:

- `app-container` - Electron 主应用 (端口 5678)
- `app-web-views` - Vue 3 Web 应用 (端口 5173)

**技术组件**:

- Element Plus - UI 组件库
- Tailwind CSS - 样式框架
- Pinia - 状态管理
- Three.js - 3D 可视化

---

### 5. xxl_job_executor (CAD 处理服务)

**路径**: `/data/i3d_migrate_arm/xxl_job_executor`
**技术栈**: Django 4.2+ + XXL-Job + Celery
**端口**: 38000


| 功能模块         | 功能说明                                      |
| ---------------- | --------------------------------------------- |
| **CAD 文件处理** | STEP/PRT/X_T/IGES/BREP 文件下载、转换、预处理 |
| **3D 模型对比**  | 几何、拓扑、聚类算法对比                      |
| **属性提取**     | PLM 属性提取和入库                            |
| **表路由**       | 原表/备份表切换                               |
| **异步任务**     | 基于 Celery + RabbitMQ 的异步处理             |
| **REST API**     | HTTP 服务接口                                 |
| **3D 可视化**    | React + Three.js 前端界面 (端口 38001)        |

**CAD 处理能力**:

- 文件格式: STEP, PRT, X_T, IGES, BREP
- 转换引擎: DEE SDK (新迪 3D 引擎)
- 对比算法: 几何聚类、拓扑 DEE、匹配器 DEE

**核心 API**:

- XXL-Job 执行器接口 (端口 38000)
- REST API 服务接口

---

## 共享基础设施

### Shared SDKs (军规 - 必须使用)


| SDK                  | 用途                    | 禁止直接使用         |
| -------------------- | ----------------------- | -------------------- |
| `i3d-django-models`  | Django 模型和数据库访问 | `psycopg2`, 原生 SQL |
| `i3d-pgvector-sdk`   | pgvector 向量搜索       | `psycopg2` 查询      |
| `i3d-mq-cloudevents` | RabbitMQ 消息队列       | 直接`pika` 发布/消费 |
| `i3d-redis-sdk`      | Redis 缓存操作          | `redis-py`           |
| `i3d-tenant-sdk`     | 多租户上下文管理        | 手动实现             |

### 基础设施服务


| 服务          | 端口        | 说明                |
| ------------- | ----------- | ------------------- |
| PostgreSQL    | 15433       | 主数据库 + pgvector |
| Redis         | 6379        | 缓存和消息队列      |
| RabbitMQ      | 5672        | 消息队列            |
| RabbitMQ 管理 | 15672       | 管理界面            |
| MinIO         | 19002/19003 | 对象存储            |
| XXL-Job Admin | 4091        | 任务调度中心        |

---

## 多租户架构

### 支持的租户

- shenfa (申发)
- meidi (美的)
- dongjiang (东江)
- huabei (华贝)

### 租户隔离机制

- **数据库**: PostgreSQL RLS (Row-Level Security)
- **标识**: X-Tenant-ID HTTP Header
- **存储**: MinIO Bucket-per-tenant (`{tenant}-files`)
- **向量**: product_embeddings 表 RLS 隔离

---

## 数据流向

### 入库流程

```
上游系统 → RabbitMQ → minio-api → 3d-search-core (特征提取) → PostgreSQL pgvector
```

### 搜索流程

```
用户请求 → InferEngineer-3dRetrieval → PostgreSQL pgvector (向量搜索) → 返回结果
```

### CAD 文件处理

```
XXL-Job 调度 → xxl_job_executor → Celery 任务 → 文件处理/入库
```

---

## 向量存储架构

### product_embeddings 表

- **向量维度**: 512 维 (3D 和 2D 统一)
- **索引**: HNSW 索引加速相似度搜索
- **隔离**: RLS 策略租户隔离

### 字段说明


| 字段        | 说明                                                                |
| ----------- | ------------------------------------------------------------------- |
| file_type   | 1=零件库, 2=产品库                                                  |
| search_type | 1=模型搜索, 2=图片搜索, 3=多图搜索                                  |
| insert_type | [1]=3D全局, [2]=3D局部, [3]=2D三视图, [4]=2D剖面图, [1,3]=3D+2D组合 |

---

## 命名规范

### URL/API 命名


| 场景          | 规范       | 示例                            |
| ------------- | ---------- | ------------------------------- |
| URL 模块名    | 全小写     | `/api/search/`, `/api/cadFile/` |
| URL 动作名    | camelCase  | `getPrtPathByItemCode`          |
| 请求/响应参数 | snake_case | `item_code`, `page_size`        |

### Python 代码命名


| 场景      | 规范             | 示例             |
| --------- | ---------------- | ---------------- |
| 类名      | PascalCase       | `CadFileManager` |
| 函数/变量 | snake_case       | `get_cad_file()` |
| 常量      | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE`  |

### 数据库命名


| 场景   | 规范                      | 示例           |
| ------ | ------------------------- | -------------- |
| 表名   | snake_case (无 i3d_ 前缀) | `cad_file_plm` |
| 字段名 | snake_case                | `create_time`  |

---

## 相关文档


| 项目                      | 主要文档                              | 云原生文档                                  |
| ------------------------- | ------------------------------------- | ------------------------------------------- |
| InferEngineer-3dRetrieval | `InferEngineer-3dRetrieval/AGENTS.md` | `InferEngineer-3dRetrieval/CLOUDNATIVE.md`  |
| 3d-search-core            | `3d-search-core/AGENTS.md`            | `3d-search-core/CLOUDNATIVE.md`             |
| minio-api                 | `minio-api/AGENTS.md`                 | `minio-api/CLOUDNATIVE.md`                  |
| 3d-desktopprogram         | `3d-desktopprogram/AGENTS.md`         | `3d-desktopprogram/CLOUDNATIVE_FRONTEND.md` |
| xxl_job_executor          | `xxl_job_executor/AGENTS.md`          | `xxl_job_executor/CLOUDNATIVE.md`           |

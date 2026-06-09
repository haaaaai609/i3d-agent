# RAG 管理前端设计方案

## 目标

在现有 Vue3 前端中新增一个 RAG 管理工作台，用于知识库文档接入、索引状态监控、检索调试和质量反馈。该页面面向运维/研发/知识库管理员，不替代当前聊天页，而是补齐 RAG 数据侧的管理能力。

首期必须支持：

- 单文件上传并入库。
- 输入服务器已挂载目录，批量扫描和导入文档。
- 索引状态和索引队列监控。

同时应加入主流 RAG 管理台中常见、且与本项目现有接口能匹配的能力：文档列表、文档详情、版本历史、检索测试、问答测试、来源展示、质量反馈和指标概览。

## 外部产品调研

### Dify Knowledge

Dify 的知识库管理重点在知识库设置、文档处理和检索配置。可借鉴点：

- 知识库层配置：名称、描述、权限、索引方式、Embedding 模型、摘要生成、检索设置。
- 检索节点层配置：对检索结果做进一步过滤、重排和加权，语义相似度与关键词匹配可配置权重。
- 管理界面应把“接入文档”和“调试检索”放在同一个知识库上下文里，便于改完配置后立刻验证效果。

参考：https://docs.dify.ai/en/use-dify/knowledge/manage-knowledge/introduction  
参考：https://docs.dify.ai/en/use-dify/nodes/knowledge-retrieval

### RAGFlow

RAGFlow 的知识库管理强调数据集、文档解析、chunk 和检索测试。可借鉴点：

- 数据集作为知识源容器，支持上传文件、解析文件、选择 chunk 方法。
- 提供 Retrieval Test，用查询直接检查命中的 chunk 是否符合预期。
- 对解析结果进行人工干预和检查，这对企业内部技术文档尤其重要。

参考：https://ragflow.com.cn/docs/configure_knowledge_base  
参考：https://ragflow.com.cn/docs/run_retrieval_test

### Open WebUI Knowledge

Open WebUI 的 Knowledge/RAG 能力强调上传文档、知识库范围、检索模式和引用来源。可借鉴点：

- 区分 Focused Retrieval 和 Full Context 两种使用模式。
- 支持混合搜索、rerank、相关度阈值、引用来源。
- 文件处理是异步流程，前端需要清楚展示处理状态和失败原因。
- 知识库可导出、可通过 API 管理。

参考：https://docs.openwebui.com/features/workspace/knowledge/  
参考：https://docs.openwebui.com/features/rag/

### LangSmith / RAG Evaluation

LangSmith 更偏向 RAG 可观测性和评测。可借鉴点：

- 将检索质量和生成质量分开评估。
- 基于测试集、生产查询和用户反馈做持续评估。
- 关注答案相关性、答案准确性、检索质量、context precision、context recall、faithfulness、延迟和成本等指标。

参考：https://docs.langchain.com/langsmith/evaluate-rag-tutorial  
参考：https://docs.langchain.com/langsmith/evaluation

## 当前后端能力梳理

RAG API 统一前缀：`/api/v1/rag`。

### 文档接入

- `POST /documents`：直接创建文本型文档。
- `POST /documents/upload`：单文件上传，使用 multipart/form-data。
- `POST /documents/batch-import`：批量导入服务器目录。

批量导入依赖 `RAG_IMPORT_ROOTS`，默认允许容器内 `/mnt/rag-import`。当前支持文本类扩展名：`.md`、`.txt`、`.json`、`.html`、`.htm`。

### 文档管理

- `GET /documents`：文档列表。
- `GET /documents/{doc_id}`：文档详情。
- `PUT /documents/{doc_id}`：更新文档。
- `DELETE /documents/{doc_id}`：软删除或硬删除。
- `POST /documents/{doc_id}/restore`：恢复文档。
- `GET /documents/{doc_id}/history`：版本历史。

文档响应包含文件元数据：`file_md5`、`file_name`、`file_size`、`mime_type`、`storage_path`、`source_path`。

### 检索与问答

- `POST /search`：检索 chunk，支持 `top_k`、`enable_expansion`、`enable_hyde`、`enable_rerank`、`search_type`。
- `POST /ask`：RAG 问答，返回答案、来源和基础 metadata。
- `POST /feedback`：提交质量反馈。

### 监控

- `GET /index/status`：总文档数、chunk 数、pending/failed/indexing 数、平均 chunk 大小、文档类型分布。
- `GET /index/queue`：索引队列列表，可按状态过滤。
- `GET /metrics`：RAG 指标查询。
- `GET /quality`：质量指标，包括平均评分、有用率、点赞率、反馈数。

## 当前接口缺口与风险

这些不是前端阻塞项，但建议在开发前或开发中补齐：

- `GET /documents` 当前 API 使用 `page/page_size` 调 `DocumentManager.list_documents()`，但 manager 层参数是 `limit/offset`，需要修正接口对齐，否则文档列表页可能报错。
- `POST /feedback` 内部把 `tenant_id` 写死为 `default`，应改为从请求体或查询参数传入。
- 缺少 `GET /documents/{doc_id}/chunks`，文档详情页无法直接查看某个文档的 chunk、token_count、chunk_index 和内容预览。
- 缺少 `POST /documents/{doc_id}/reindex`，无法从前端手动触发重建索引。
- 缺少索引任务操作接口，例如 retry/cancel。监控页只能看，不能处理失败任务。
- 缺少只读配置接口，例如 `GET /config`，前端无法展示当前 embedding 模型、向量维度、chunk 参数、允许导入根目录、支持文件类型。
- 单文件上传没有查重提示；批量导入已有 MD5 去重，上传页建议补一个 duplicate warning 或让后端统一去重策略。
- 当前文件解析只支持文本类文件。若后续要支持 PDF/DOCX/CSV，需要先扩展 `DocumentStorage`。

## 页面信息架构

最新产品决策：前端改为 ChatGPT 风格的简洁工作台。左侧保留会话列表能力，并新增一级主导航；聊天主区去掉 Agent 选择器，不展示也不传递 agent，由后端 supervisor 自动路由。RAG 管理作为左侧主导航中的新菜单，和聊天页共享同一个 `tenantId`。租户和用户 ID 都保留，但只放在设置弹窗里，不常驻在聊天主界面。

建议新增 `RagConsole.vue`，在 `App.vue` 中增加应用级菜单：

- `聊天`：ChatGPT 风格聊天主界面。
- `RAG 管理`：新管理工作台。

左侧栏结构建议：

1. 顶部主导航：`聊天` / `RAG 管理`。
2. 聊天菜单下展示新建对话、历史会话、重命名、删除。
3. RAG 管理菜单下不展示聊天会话，改为显示 RAG 二级导航或让主内容区显示 tabs。
4. 底部只保留设置按钮，点击打开设置弹窗。

设置弹窗字段：

- `tenantId`：聊天和 RAG 管理共享。
- `userId`：聊天请求使用；RAG 管理暂不强依赖，但保留上下文一致性。
- `streamMode`：聊天输出方式开关。

聊天主区简化要求：

- 移除 `AgentSelector`。
- 移除 agent badge 和 agent prompt 依赖。
- 输入框 placeholder 固定为通用文案，例如 `输入消息...`。
- 请求 payload 不再携带前端选择的 agent；如现有后端 payload 字段仍要求 agent，则前端临时传空值或固定兼容值，但 UI 不展示，后续应让后端完全由 supervisor 自动路由。
- Header 只保留当前会话标题、在线状态和必要操作。

RAG 管理工作台采用左侧二级导航或顶部 tabs：

1. `总览`
2. `文档接入`
3. `文档管理`
4. `检索调试`
5. `索引监控`
6. `质量反馈`
7. `配置`

当前前端没有路由，首期可用组件内 tab 状态实现；后续如果页面变多，再引入 Vue Router。

## 功能设计

### 1. 总览

目标：打开页面即可看到知识库健康状态。

展示：

- 总文档数。
- 总 chunk 数。
- 待索引任务数。
- 失败任务数。
- 正在索引文档数。
- 平均 chunk 大小。
- 文档类型分布。
- 最近失败任务列表。

接口：

- `GET /index/status?tenant_id=...`
- `GET /index/queue?tenant_id=...&status=failed&limit=10`

交互：

- 手动刷新。
- 自动刷新开关，默认 5 秒轮询，仅在当前 tab 可见时轮询。
- 点击失败任务跳到 `索引监控` tab。

### 2. 文档接入

包含两个子区域：单文件上传、服务器目录批量导入。

#### 单文件上传

字段：

- `tenant_id`：默认复用当前全局租户。
- `file`：文件选择器。
- `doc_type`：technical/business/api。
- `source_type`：默认由文件扩展名推断，可手动覆盖。
- `title`、`description`。
- `language`：默认 zh。
- `tags`：逗号或标签输入。
- `metadata`：JSON 编辑文本框。

接口：

- `POST /documents/upload`

上传结果：

- 成功后展示 doc_id、status、file_md5、file_size、storage_path。
- 提供跳转到文档详情和查看索引队列的入口。

#### 服务器目录批量导入

字段：

- `host_dir`：容器内允许导入路径，例如 `/mnt/rag-import/project-docs`。
- `tenant_id`。
- `doc_type`。
- `source_type`。
- `recursive`。
- `include_patterns`：默认 `*.md,*.txt,*.json,*.html,*.htm`。
- `exclude_patterns`：默认提示 `.git`、`node_modules`、`dist`、`__pycache__` 会被排除。
- `dry_run`：默认开启，先扫描不写库。
- `tags`、`metadata`、`language`。

接口：

- `POST /documents/batch-import`

结果表：

- 文件名。
- MD5。
- 源路径。
- 存储路径。
- 状态：`would_import`、`imported`、`skipped`、`failed`。
- 原因：`duplicate_in_batch`、`duplicate_in_database`、错误信息。
- doc_id。

交互：

- 首次点击建议执行 dry-run。
- dry-run 结果确认后，用户关闭 dry-run 再导入。
- 支持按状态筛选结果。

安全提示：

- 只允许导入 `RAG_IMPORT_ROOTS` 下路径，前端只展示这个约束，不尝试绕过。
- 对 `source_path/storage_path` 这类服务器路径做等宽展示，避免误读。

### 3. 文档管理

目标：管理已入库文档和元数据。

列表字段：

- 标题。
- 类型。
- 状态。
- 版本。
- 是否最新。
- 文件名。
- 文件大小。
- MD5。
- 标签。
- 创建/更新时间。

筛选：

- tenant。
- doc_type。
- status。
- source_type。
- 标签。
- 文件名/标题关键词。
- MD5。

当前后端只支持 tenant/doc_type/page/page_size，其他筛选作为后续接口增强。

详情抽屉：

- 基本信息。
- 文件元数据。
- tags / metadata。
- raw_content 预览。
- 版本历史。
- 索引状态。
- chunk 列表。

需要补充接口：

- `GET /documents/{doc_id}/chunks`
- `GET /documents` 返回分页总数和更多筛选条件。

操作：

- 编辑标题、描述、metadata、tags、内容。
- 删除/恢复。
- 查看历史版本。
- 重新索引。

需要补充接口：

- `POST /documents/{doc_id}/reindex`

### 4. 检索调试

目标：像 RAGFlow Retrieval Test 一样，给管理员直接验证检索质量。

输入区：

- query/question。
- tenant。
- top_k。
- search_type：semantic/keyword/balanced/exact_match。
- 开关：query expansion、HyDE、rerank、multi-step。

两个模式：

- `检索测试`：调用 `/search`，展示 chunk 级命中。
- `问答测试`：调用 `/ask`，展示答案和来源。

检索结果展示：

- 排名。
- final_score。
- chunk 内容高亮。
- doc_id / chunk_id。
- source：title、file_name、chunk_index、storage_path。
- query_expansions。
- hypothetical_doc。

问答结果展示：

- answer。
- sources。
- iterations。
- num_retrieved。
- no_results 状态。

质量反馈：

- 对一次问答提交 rating、thumb_up、is_helpful、feedback_text。
- 后端需修正 feedback tenant。

### 5. 索引监控

目标：监控异步索引队列，定位失败任务。

展示：

- 队列状态 tabs：all/pending/processing/completed/failed。
- 任务字段：id、doc_id、operation、status、priority、retry_count、error_message、created_at、started_at。
- 指标区复用 `/index/status`。

交互：

- 自动轮询。
- 按状态筛选。
- 复制 error_message。
- 点击 doc_id 跳到文档详情。

建议后端增强：

- retry failed task。
- cancel pending task。
- reindex document。
- 返回 completed_at。

### 6. 质量反馈与指标

展示：

- 平均评分。
- 有用率。
- 点赞率。
- 反馈总数。
- 指标时间范围：24h/7d/30d。
- metrics 明细表。

接口：

- `GET /quality?tenant_id=...&days=...`
- `GET /metrics?tenant_id=...&metric_name=...&time_range=...`

后续增强：

- 反馈列表。
- 从生产查询生成评测集。
- 离线评测：固定问题集、期望来源、期望答案、召回率、MRR、faithfulness。

### 7. 配置

首期只读展示：

- embedding provider/base_url/model。
- vector dimension。
- chunk size/overlap。
- rerank provider/model。
- query expansion/HyDE/rerank 默认开关。
- RAG_IMPORT_ROOTS。
- 支持文件类型。

需要补充接口：

- `GET /api/v1/rag/config`

后续可做配置编辑，但不建议首期直接开放写配置，因为会影响索引一致性，尤其是 embedding 模型和向量维度变更。

## 前端组件拆分

建议新增：

- `frontend/src/components/rag/RagConsole.vue`
- `frontend/src/components/rag/RagDashboard.vue`
- `frontend/src/components/rag/RagIngestion.vue`
- `frontend/src/components/rag/SingleUploadPanel.vue`
- `frontend/src/components/rag/BatchImportPanel.vue`
- `frontend/src/components/rag/RagDocumentsTable.vue`
- `frontend/src/components/rag/RagDocumentDetail.vue`
- `frontend/src/components/rag/RagRetrievalLab.vue`
- `frontend/src/components/rag/RagIndexMonitor.vue`
- `frontend/src/components/rag/RagQualityPanel.vue`
- `frontend/src/components/rag/RagConfigPanel.vue`

建议新增 API 封装：

- `frontend/src/utils/ragApi.js`

核心方法：

- `uploadDocument(formData)`
- `batchImportDocuments(payload)`
- `listDocuments(params)`
- `getDocument(docId)`
- `updateDocument(docId, payload)`
- `deleteDocument(docId, hardDelete)`
- `restoreDocument(docId, version)`
- `getDocumentHistory(docId)`
- `searchRag(payload)`
- `askRag(payload)`
- `getIndexStatus(tenantId)`
- `getIndexQueue(params)`
- `getMetrics(params)`
- `getQuality(params)`
- `submitFeedback(payload)`

## UI 风格建议

该页面是管理控制台，应偏工具型、信息密度高、少装饰：

- 页面主体使用全屏工作台，不沿用当前聊天页居中的大卡片容器。
- 表格优先，状态用小标签和颜色区分。
- 上传区、导入区可以使用紧凑表单。
- 索引状态用小型 KPI 条，不做营销式大 hero。
- 检索结果用左右分栏：左侧参数，右侧结果；chunk 内容要支持折叠。
- 所有长路径、MD5、UUID 使用等宽字体并支持复制。
- 错误信息保留原文，便于排障。

## 数据状态与错误处理

所有请求都需要以下状态：

- loading。
- success。
- empty。
- error。
- stale polling。

错误展示：

- 400：展示后端 detail，例如导入路径不在允许根目录内。
- 500：展示请求摘要和错误 detail。
- 上传/导入失败：保留逐文件失败结果，不因单文件失败丢掉整批结果。

轮询策略：

- 总览和索引监控 tab 可轮询。
- 默认 5 秒，页面不可见或 tab 离开时停止。
- 手动刷新始终可用。

## 开发阶段建议

### Phase 0：后端小修

- 修复 `GET /documents` 参数对齐问题。
- 修复 feedback tenant。
- 增加 `GET /config`。
- 增加 `GET /documents/{doc_id}/chunks`。

### Phase 1：前端入口和 API 封装

- 在 `App.vue` 增加左侧主导航：`聊天 / RAG 管理`。
- 重构左侧栏：聊天模式保留会话列表；RAG 模式展示 RAG 工作台入口；设置改为弹窗。
- 简化聊天主区：移除 `AgentSelector`，不展示 agent，不由前端选择 agent。
- 新建 `ragApi.js`。
- 新建 `RagConsole.vue` 和基础 tabs。

### Phase 2：文档接入

- 实现单文件上传。
- 实现目录批量导入 dry-run 和正式导入。
- 实现导入结果表。

### Phase 3：文档管理

- 文档列表。
- 文档详情。
- 更新、删除、恢复。
- 版本历史。

### Phase 4：检索调试

- `/search` 检索测试。
- `/ask` 问答测试。
- 来源展示。
- 提交反馈。

### Phase 5：索引监控和质量面板

- 索引状态 KPI。
- 队列表。
- quality 和 metrics 面板。
- 后续接入 retry/reindex。

## 验收标准

首期验收：

- 左侧主导航可在 `聊天` 和 `RAG 管理` 间切换。
- 聊天页保留新建对话、历史会话、重命名、删除。
- 聊天页不再展示 Agent 选择器，不再让用户选择 agent。
- 聊天请求由后端 supervisor 路由，前端不暴露 agent 概念。
- 租户和用户 ID 在设置弹窗中维护，并被聊天和 RAG 管理共享。
- 可以从页面上传一个 `.md/.txt/.json/.html` 文件，并在文档列表看到它。
- 可以输入 `/mnt/rag-import` 下目录，先 dry-run，再正式批量导入。
- 批量导入能展示 imported/skipped/failed/would_import 的逐文件结果。
- 可以查看索引总览和队列，失败任务能看到错误信息。
- 可以输入查询执行检索测试，并看到 chunk、score、source。
- 可以执行问答测试，并看到 answer 和 sources。
- 所有接口错误都有可读提示。

后续增强验收：

- 可以查看单文档 chunk 列表。
- 可以手动 reindex 文档。
- 可以 retry 失败索引任务。
- 可以看到配置只读面板。
- 可以从真实反馈构建评测集并跟踪检索质量趋势。

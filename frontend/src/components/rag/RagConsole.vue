<template>
  <div class="rag-console">
    <header class="rag-header">
      <div>
        <h2>RAG 管理</h2>
        <p>租户：{{ tenantId }}</p>
      </div>
      <button class="secondary-btn" type="button" @click="refreshActive">刷新</button>
    </header>

    <nav class="rag-tabs" aria-label="RAG 管理菜单">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </nav>

    <div v-if="error" class="error-banner">
      <span>{{ error }}</span>
      <button type="button" @click="error = ''">关闭</button>
    </div>

    <section v-if="activeTab === 'dashboard'" class="tab-panel">
      <div class="stat-grid">
        <div v-for="item in statCards" :key="item.label" class="stat-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
      <div class="panel-grid">
        <div class="panel">
          <h3>文档类型分布</h3>
          <table class="data-table compact">
            <tbody>
              <tr v-for="(count, type) in indexStatus.doc_type_distribution || {}" :key="type">
                <td>{{ type }}</td>
                <td>{{ count }}</td>
              </tr>
              <tr v-if="!Object.keys(indexStatus.doc_type_distribution || {}).length">
                <td colspan="2">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="panel">
          <h3>最近失败任务</h3>
          <table class="data-table compact">
            <tbody>
              <tr v-for="task in failedTasks" :key="task.id">
                <td class="mono">{{ shortId(task.doc_id) }}</td>
                <td>{{ task.operation }}</td>
                <td class="error-text">{{ task.error_message || '-' }}</td>
              </tr>
              <tr v-if="failedTasks.length === 0">
                <td colspan="3">暂无失败任务</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'ingestion'" class="tab-panel split-panel">
      <div class="panel">
        <h3>单文件上传</h3>
        <form class="form-grid" @submit.prevent="handleUpload">
          <label>
            <span>文件</span>
            <input type="file" @change="uploadForm.file = $event.target.files[0] || null">
          </label>
          <label>
            <span>文档类型</span>
            <select v-model="uploadForm.doc_type">
              <option value="technical">technical</option>
              <option value="business">business</option>
              <option value="api">api</option>
            </select>
          </label>
          <label>
            <span>标题</span>
            <input v-model="uploadForm.title" type="text" placeholder="默认使用文件名">
          </label>
          <label>
            <span>标签</span>
            <input v-model="uploadForm.tags" type="text" placeholder="逗号分隔">
          </label>
          <label class="full">
            <span>Metadata JSON</span>
            <textarea v-model="uploadForm.metadata" rows="3" placeholder='{"source":"manual"}'></textarea>
          </label>
          <button class="primary-btn" type="submit" :disabled="loading">上传并入库</button>
        </form>

        <pre v-if="uploadResult" class="result-box">{{ formatJson(uploadResult) }}</pre>
      </div>

      <div class="panel">
        <h3>服务器目录批量导入</h3>
        <form class="form-grid" @submit.prevent="handleBatchImport">
          <label class="full">
            <span>目录</span>
            <input v-model="batchForm.host_dir" type="text" placeholder="/mnt/rag-import/project-docs">
          </label>
          <label>
            <span>文档类型</span>
            <select v-model="batchForm.doc_type">
              <option value="technical">technical</option>
              <option value="business">business</option>
              <option value="api">api</option>
            </select>
          </label>
          <label>
            <span>包含模式</span>
            <input v-model="batchForm.include_patterns" type="text" placeholder="*.md,*.txt">
          </label>
          <label>
            <span>排除模式</span>
            <input v-model="batchForm.exclude_patterns" type="text" placeholder="*.tmp,archive/**">
          </label>
          <label class="inline-check">
            <input v-model="batchForm.recursive" type="checkbox">
            <span>递归扫描</span>
          </label>
          <label class="inline-check">
            <input v-model="batchForm.dry_run" type="checkbox">
            <span>Dry run</span>
          </label>
          <button class="primary-btn" type="submit" :disabled="loading">执行导入</button>
        </form>

        <div v-if="batchResult" class="import-result">
          <div class="summary-line">
            扫描 {{ batchResult.scanned }}，导入 {{ batchResult.imported }}，跳过 {{ batchResult.skipped }}，失败 {{ batchResult.failed }}
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>文件</th>
                <th>状态</th>
                <th>原因</th>
                <th>Doc</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in batchResult.results" :key="`${item.file_md5}-${item.source_path}`">
                <td>
                  <div>{{ item.file_name }}</div>
                  <small class="mono">{{ item.source_path }}</small>
                </td>
                <td><span :class="['status-pill', item.status]">{{ item.status }}</span></td>
                <td>{{ item.reason || '-' }}</td>
                <td class="mono">{{ shortId(item.doc_id) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'documents'" class="tab-panel">
      <div class="toolbar">
        <select v-model="documentFilter.doc_type" @change="loadDocuments">
          <option value="">全部类型</option>
          <option value="technical">technical</option>
          <option value="business">business</option>
          <option value="api">api</option>
        </select>
        <button class="secondary-btn" type="button" @click="loadDocuments">刷新文档</button>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>标题</th>
            <th>类型</th>
            <th>状态</th>
            <th>文件</th>
            <th>版本</th>
            <th>更新</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in documents" :key="doc.id">
            <td>
              <strong>{{ doc.title }}</strong>
              <small class="mono">{{ doc.id }}</small>
            </td>
            <td>{{ doc.doc_type }}</td>
            <td><span :class="['status-pill', doc.status]">{{ doc.status }}</span></td>
            <td>
              <span>{{ doc.file_name || '-' }}</span>
              <small class="mono">{{ doc.file_md5 || '' }}</small>
            </td>
            <td>v{{ doc.version }}</td>
            <td>{{ formatDate(doc.updated_at) }}</td>
            <td class="actions">
              <button type="button" @click="selectDocument(doc)">详情</button>
              <button type="button" @click="handleReindex(doc)">重建索引</button>
              <button type="button" @click="handleDelete(doc)">删除</button>
            </td>
          </tr>
          <tr v-if="documents.length === 0">
            <td colspan="7">暂无文档</td>
          </tr>
        </tbody>
      </table>

      <aside v-if="selectedDocument" class="detail-panel">
        <header>
          <h3>{{ selectedDocument.title }}</h3>
          <button type="button" @click="selectedDocument = null">×</button>
        </header>
        <dl>
          <div><dt>ID</dt><dd class="mono">{{ selectedDocument.id }}</dd></div>
          <div><dt>文件名</dt><dd>{{ selectedDocument.file_name || '-' }}</dd></div>
          <div><dt>存储路径</dt><dd class="mono">{{ selectedDocument.storage_path || '-' }}</dd></div>
          <div><dt>源路径</dt><dd class="mono">{{ selectedDocument.source_path || '-' }}</dd></div>
        </dl>
        <h4>版本历史</h4>
        <pre class="result-box">{{ formatJson(documentHistory) }}</pre>
        <h4>Chunks</h4>
        <div class="chunk-list">
          <article v-for="chunk in documentChunks" :key="chunk.id">
            <strong>#{{ chunk.chunk_index }}</strong>
            <p>{{ chunk.content }}</p>
          </article>
          <p v-if="documentChunks.length === 0">暂无 chunk 数据</p>
        </div>
      </aside>
    </section>

    <section v-else-if="activeTab === 'retrieval'" class="tab-panel split-panel">
      <div class="panel">
        <h3>检索测试</h3>
        <form class="form-grid" @submit.prevent="handleSearch">
          <label class="full">
            <span>查询</span>
            <textarea v-model="searchForm.query" rows="4"></textarea>
          </label>
          <label>
            <span>Top K</span>
            <input v-model.number="searchForm.top_k" type="number" min="1" max="100">
          </label>
          <label>
            <span>检索类型</span>
            <select v-model="searchForm.search_type">
              <option value="balanced">balanced</option>
              <option value="semantic">semantic</option>
              <option value="keyword">keyword</option>
              <option value="exact_match">exact_match</option>
            </select>
          </label>
          <label class="inline-check"><input v-model="searchForm.enable_expansion" type="checkbox"><span>扩展</span></label>
          <label class="inline-check"><input v-model="searchForm.enable_hyde" type="checkbox"><span>HyDE</span></label>
          <label class="inline-check"><input v-model="searchForm.enable_rerank" type="checkbox"><span>Rerank</span></label>
          <button class="primary-btn" type="submit">检索</button>
        </form>
        <div class="result-list">
          <article v-for="item in searchResult?.results || []" :key="item.chunk_id">
            <header>
              <strong>{{ item.source?.title || item.metadata?.title || item.doc_id }}</strong>
              <span>{{ scoreText(item.score) }}</span>
            </header>
            <p>{{ item.content }}</p>
            <small class="mono">{{ item.source?.file_name || item.doc_id }} / {{ item.chunk_id }}</small>
          </article>
        </div>
      </div>

      <div class="panel">
        <h3>问答测试</h3>
        <form class="form-grid" @submit.prevent="handleAsk">
          <label class="full">
            <span>问题</span>
            <textarea v-model="askForm.question" rows="4"></textarea>
          </label>
          <label>
            <span>Top K</span>
            <input v-model.number="askForm.top_k" type="number" min="1" max="50">
          </label>
          <label class="inline-check">
            <input v-model="askForm.enable_multi_step" type="checkbox">
            <span>多步推理</span>
          </label>
          <button class="primary-btn" type="submit">问答</button>
        </form>
        <article v-if="askResult" class="answer-box">
          <strong>{{ askResult.status }}</strong>
          <p>{{ askResult.answer }}</p>
          <pre class="result-box">{{ formatJson(askResult.sources || []) }}</pre>
        </article>
      </div>
    </section>

    <section v-else-if="activeTab === 'monitor'" class="tab-panel">
      <div class="toolbar">
        <select v-model="queueFilter.status" @change="loadQueue">
          <option value="">全部状态</option>
          <option value="pending">pending</option>
          <option value="processing">processing</option>
          <option value="completed">completed</option>
          <option value="failed">failed</option>
        </select>
        <button class="secondary-btn" type="button" @click="loadQueue">刷新队列</button>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>任务</th>
            <th>文档</th>
            <th>操作</th>
            <th>状态</th>
            <th>重试</th>
            <th>错误</th>
            <th>创建</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in queueTasks" :key="task.id">
            <td class="mono">{{ shortId(task.id) }}</td>
            <td class="mono">{{ shortId(task.doc_id) }}</td>
            <td>{{ task.operation }}</td>
            <td><span :class="['status-pill', task.status]">{{ task.status }}</span></td>
            <td>{{ task.retry_count }}</td>
            <td class="error-text">{{ task.error_message || '-' }}</td>
            <td>{{ formatDate(task.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-else-if="activeTab === 'quality'" class="tab-panel">
      <div class="stat-grid">
        <div class="stat-card"><span>平均评分</span><strong>{{ quality.avg_rating ?? '-' }}</strong></div>
        <div class="stat-card"><span>有用率</span><strong>{{ percent(quality.helpful_rate) }}</strong></div>
        <div class="stat-card"><span>点赞率</span><strong>{{ percent(quality.thumb_up_rate) }}</strong></div>
        <div class="stat-card"><span>反馈数</span><strong>{{ quality.total_feedbacks || 0 }}</strong></div>
      </div>
      <pre class="result-box">{{ formatJson(metrics) }}</pre>
    </section>

    <section v-else class="tab-panel">
      <div class="panel">
        <h3>运行配置</h3>
        <pre class="result-box">{{ formatJson(config) }}</pre>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  askRag,
  batchImportDocuments,
  deleteDocument,
  getDocumentChunks,
  getDocumentHistory,
  getIndexQueue,
  getIndexStatus,
  getMetrics,
  getQuality,
  getRagConfig,
  listDocuments,
  reindexDocument,
  searchRag,
  uploadDocument
} from '../../utils/ragApi.js'

const props = defineProps({
  tenantId: { type: String, default: 'huabei' }
})

const tabs = [
  { key: 'dashboard', label: '总览' },
  { key: 'ingestion', label: '文档接入' },
  { key: 'documents', label: '文档管理' },
  { key: 'retrieval', label: '检索调试' },
  { key: 'monitor', label: '索引监控' },
  { key: 'quality', label: '质量反馈' },
  { key: 'config', label: '配置' }
]

const activeTab = ref('dashboard')
const loading = ref(false)
const error = ref('')
const indexStatus = ref({})
const failedTasks = ref([])
const queueTasks = ref([])
const documents = ref([])
const selectedDocument = ref(null)
const documentHistory = ref([])
const documentChunks = ref([])
const uploadResult = ref(null)
const batchResult = ref(null)
const searchResult = ref(null)
const askResult = ref(null)
const quality = ref({})
const metrics = ref([])
const config = ref({})

const uploadForm = reactive({
  file: null,
  doc_type: 'technical',
  title: '',
  tags: '',
  metadata: ''
})

const batchForm = reactive({
  host_dir: '/mnt/rag-import',
  doc_type: 'technical',
  recursive: true,
  dry_run: true,
  include_patterns: '*.md,*.txt,*.json,*.html,*.htm',
  exclude_patterns: ''
})

const documentFilter = reactive({ doc_type: '' })
const queueFilter = reactive({ status: '' })

const searchForm = reactive({
  query: '',
  top_k: 10,
  search_type: 'balanced',
  enable_expansion: true,
  enable_hyde: true,
  enable_rerank: true
})

const askForm = reactive({
  question: '',
  top_k: 5,
  enable_multi_step: true
})

const statCards = computed(() => [
  { label: '文档', value: indexStatus.value.total_documents || 0 },
  { label: 'Chunks', value: indexStatus.value.total_chunks || 0 },
  { label: '待索引', value: indexStatus.value.pending_index || 0 },
  { label: '失败', value: indexStatus.value.failed_index || 0 },
  { label: '索引中', value: indexStatus.value.indexing_docs || 0 },
  { label: '平均 Chunk', value: indexStatus.value.avg_chunk_size || 0 }
])

onMounted(() => {
  refreshActive()
})

watch(activeTab, () => refreshActive())
watch(() => props.tenantId, () => refreshActive())

async function withLoading(task) {
  loading.value = true
  error.value = ''
  try {
    return await task()
  } catch (err) {
    error.value = err.message || String(err)
    throw err
  } finally {
    loading.value = false
  }
}

function splitPatterns(value) {
  return value.split(',').map(item => item.trim()).filter(Boolean)
}

async function refreshActive() {
  if (activeTab.value === 'dashboard') {
    await loadDashboard()
  } else if (activeTab.value === 'documents') {
    await loadDocuments()
  } else if (activeTab.value === 'monitor') {
    await loadQueue()
  } else if (activeTab.value === 'quality') {
    await loadQuality()
  } else if (activeTab.value === 'config') {
    await loadConfig()
  }
}

async function loadDashboard() {
  await withLoading(async () => {
    indexStatus.value = await getIndexStatus(props.tenantId)
    const failed = await getIndexQueue({ tenant_id: props.tenantId, status: 'failed', limit: 10 })
    failedTasks.value = failed.tasks || []
  })
}

async function loadDocuments() {
  await withLoading(async () => {
    const result = await listDocuments({
      tenant_id: props.tenantId,
      doc_type: documentFilter.doc_type,
      page: 1,
      page_size: 50
    })
    documents.value = result.items || result || []
  })
}

async function loadQueue() {
  await withLoading(async () => {
    const result = await getIndexQueue({
      tenant_id: props.tenantId,
      status: queueFilter.status,
      limit: 100
    })
    queueTasks.value = result.tasks || []
  })
}

async function loadQuality() {
  await withLoading(async () => {
    quality.value = await getQuality({ tenant_id: props.tenantId, days: 7 })
    const result = await getMetrics({ tenant_id: props.tenantId, time_range: '24h' })
    metrics.value = result.metrics || []
  })
}

async function loadConfig() {
  await withLoading(async () => {
    config.value = await getRagConfig()
  })
}

async function handleUpload() {
  if (!uploadForm.file) {
    error.value = '请选择文件'
    return
  }
  await withLoading(async () => {
    const form = new FormData()
    form.append('file', uploadForm.file)
    form.append('tenant_id', props.tenantId)
    form.append('doc_type', uploadForm.doc_type)
    if (uploadForm.title) form.append('title', uploadForm.title)
    if (uploadForm.tags) form.append('tags', uploadForm.tags)
    if (uploadForm.metadata) form.append('metadata', uploadForm.metadata)
    uploadResult.value = await uploadDocument(form)
  })
}

async function handleBatchImport() {
  await withLoading(async () => {
    batchResult.value = await batchImportDocuments({
      host_dir: batchForm.host_dir,
      tenant_id: props.tenantId,
      doc_type: batchForm.doc_type,
      recursive: batchForm.recursive,
      dry_run: batchForm.dry_run,
      include_patterns: splitPatterns(batchForm.include_patterns),
      exclude_patterns: splitPatterns(batchForm.exclude_patterns)
    })
  })
}

async function selectDocument(doc) {
  selectedDocument.value = doc
  await withLoading(async () => {
    const [history, chunks] = await Promise.all([
      getDocumentHistory(doc.id),
      getDocumentChunks(doc.id, { tenant_id: props.tenantId, limit: 100 })
    ])
    documentHistory.value = history.history || []
    documentChunks.value = chunks.items || []
  })
}

async function handleReindex(doc) {
  await withLoading(async () => {
    await reindexDocument(doc.id, props.tenantId)
    await loadQueue()
    activeTab.value = 'monitor'
  })
}

async function handleDelete(doc) {
  if (!confirm(`确定删除 "${doc.title}" 吗？`)) return
  await withLoading(async () => {
    await deleteDocument(doc.id, false)
    await loadDocuments()
  })
}

async function handleSearch() {
  await withLoading(async () => {
    searchResult.value = await searchRag({
      ...searchForm,
      tenant_id: props.tenantId
    })
  })
}

async function handleAsk() {
  await withLoading(async () => {
    askResult.value = await askRag({
      ...askForm,
      tenant_id: props.tenantId
    })
  })
}

function formatJson(value) {
  return JSON.stringify(value, null, 2)
}

function shortId(value) {
  if (!value) return '-'
  return String(value).slice(0, 8)
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function scoreText(value) {
  if (value === undefined || value === null) return '-'
  return `${(Number(value) * 100).toFixed(1)}%`
}

function percent(value) {
  if (value === undefined || value === null) return '-'
  return `${(Number(value) * 100).toFixed(1)}%`
}
</script>

<style scoped>
.rag-console {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f9fafb;
}

.rag-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 24px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}

.rag-header h2 {
  margin: 0;
  font-size: 20px;
}

.rag-header p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.rag-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 24px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
  overflow-x: auto;
}

.rag-tabs button {
  min-height: 34px;
  padding: 0 12px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #4b5563;
  cursor: pointer;
  white-space: nowrap;
}

.rag-tabs button.active {
  background: #111827;
  color: #fff;
}

.tab-panel {
  min-height: 0;
  flex: 1;
  overflow: auto;
  padding: 18px 24px 28px;
}

.split-panel {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(320px, 1fr);
  gap: 16px;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.panel,
.stat-card,
.detail-panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.panel {
  padding: 16px;
}

.panel h3,
.detail-panel h3 {
  margin: 0 0 14px;
  font-size: 16px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  padding: 14px;
}

.stat-card span {
  display: block;
  color: #6b7280;
  font-size: 12px;
}

.stat-card strong {
  display: block;
  margin-top: 6px;
  font-size: 24px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label {
  display: grid;
  gap: 6px;
}

.form-grid label span {
  color: #374151;
  font-size: 12px;
  font-weight: 700;
}

.form-grid .full {
  grid-column: 1 / -1;
}

.form-grid input,
.form-grid select,
.form-grid textarea,
.toolbar select {
  width: 100%;
  min-height: 36px;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 7px;
  background: #fff;
  font: inherit;
}

.inline-check {
  display: flex !important;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 8px !important;
}

.inline-check input {
  width: auto;
  min-height: auto;
}

.primary-btn,
.secondary-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 7px;
  cursor: pointer;
  font-weight: 700;
}

.primary-btn {
  border: 0;
  background: #111827;
  color: #fff;
}

.secondary-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #111827;
}

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
  font-size: 13px;
}

.data-table th {
  color: #6b7280;
  font-size: 12px;
  font-weight: 700;
}

.data-table small {
  display: block;
  margin-top: 4px;
  color: #6b7280;
}

.compact td {
  padding: 8px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.actions button {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
}

.status-pill {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  background: #e5e7eb;
  color: #374151;
  font-size: 12px;
  font-weight: 700;
}

.status-pill.pending,
.status-pill.would_import {
  background: #fef3c7;
  color: #92400e;
}

.status-pill.imported,
.status-pill.ready,
.status-pill.completed {
  background: #dcfce7;
  color: #166534;
}

.status-pill.failed {
  background: #fee2e2;
  color: #991b1b;
}

.status-pill.skipped {
  background: #e0e7ff;
  color: #3730a3;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  word-break: break-all;
}

.error-text {
  color: #991b1b;
}

.error-banner {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 24px;
  border-bottom: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
  font-size: 13px;
}

.error-banner button {
  border: 0;
  background: transparent;
  color: #991b1b;
  cursor: pointer;
}

.result-box {
  max-height: 320px;
  overflow: auto;
  margin-top: 12px;
  padding: 12px;
  border-radius: 7px;
  background: #111827;
  color: #f9fafb;
  font-size: 12px;
  white-space: pre-wrap;
}

.summary-line {
  margin: 12px 0;
  color: #374151;
  font-size: 13px;
  font-weight: 700;
}

.detail-panel {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 30;
  width: min(620px, 100vw);
  height: 100vh;
  overflow: auto;
  padding: 18px;
  box-shadow: -18px 0 42px rgba(15, 23, 42, 0.18);
}

.detail-panel header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.detail-panel header button {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 6px;
  background: #f3f4f6;
  cursor: pointer;
  font-size: 22px;
}

.detail-panel dl {
  display: grid;
  gap: 10px;
}

.detail-panel dt {
  color: #6b7280;
  font-size: 12px;
  font-weight: 700;
}

.detail-panel dd {
  margin: 3px 0 0;
}

.chunk-list {
  display: grid;
  gap: 10px;
}

.chunk-list article,
.result-list article,
.answer-box {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.result-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.result-list header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.result-list p,
.chunk-list p,
.answer-box p {
  color: #374151;
  line-height: 1.6;
}

@media (max-width: 1100px) {
  .split-panel,
  .panel-grid {
    grid-template-columns: 1fr;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>

<template>
  <details class="sources">
    <summary>参考 {{ sources.length }} 条来源</summary>
    <div class="sources-list">
      <button
        v-for="(source, index) in sources"
        :key="source.chunk_id || `${source.doc_id || 'doc'}-${source.chunk_index ?? index}`"
        class="source-item"
        type="button"
        @click="selectedSource = source"
      >
        <span class="source-main">
          <span class="title">{{ sourceTitle(source) }}</span>
          <span class="chunk">{{ chunkLabel(source) }}</span>
        </span>
        <span class="score" :title="scoreTooltip(source)">
          ★ {{ scorePercent(source.score) }}
        </span>
      </button>
    </div>
  </details>

  <teleport to="body">
    <div
      v-if="selectedSource"
      class="source-modal-backdrop"
      @click.self="selectedSource = null"
    >
      <section class="source-modal" role="dialog" aria-modal="true" aria-labelledby="source-detail-title">
        <header class="source-modal-header">
          <h3 id="source-detail-title">{{ sourceTitle(selectedSource) }}</h3>
          <button type="button" class="close-button" aria-label="关闭" @click="selectedSource = null">×</button>
        </header>

        <dl class="source-detail-list">
          <div>
            <dt>文档 ID</dt>
            <dd>{{ selectedSource.doc_id || '-' }}</dd>
          </div>
          <div>
            <dt>切块 ID</dt>
            <dd>{{ selectedSource.chunk_id || '-' }}</dd>
          </div>
          <div>
            <dt>切块序号</dt>
            <dd>{{ selectedSource.chunk_index ?? '-' }}</dd>
          </div>
          <div>
            <dt>文档版本</dt>
            <dd>{{ selectedSource.doc_version ?? '-' }}</dd>
          </div>
          <div>
            <dt>来源文件</dt>
            <dd>{{ selectedSource.file_name || selectedSource.source || '-' }}</dd>
          </div>
          <div v-if="selectedSource.source_path">
            <dt>宿主机路径</dt>
            <dd>{{ selectedSource.source_path }}</dd>
          </div>
          <div v-if="selectedSource.storage_path">
            <dt>归档路径</dt>
            <dd>{{ selectedSource.storage_path }}</dd>
          </div>
          <div v-if="selectedSource.file_md5">
            <dt>MD5</dt>
            <dd>{{ selectedSource.file_md5 }}</dd>
          </div>
          <div>
            <dt>相关度</dt>
            <dd>{{ scorePercent(selectedSource.score) }}</dd>
          </div>
        </dl>
      </section>
    </div>
  </teleport>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  sources: { type: Array, default: () => [] }
})

const selectedSource = ref(null)

function sourceTitle(source) {
  return source?.title || source?.file_name || source?.source || '未知文档'
}

function chunkLabel(source) {
  if (!source) return 'Chunk -'
  return source.chunk_index === undefined || source.chunk_index === null
    ? 'Chunk -'
    : `Chunk #${source.chunk_index}`
}

function scorePercent(score) {
  return `${((Number(score) || 0) * 100).toFixed(1)}%`
}

function fixed(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return '-'
  }
  return Number(value).toFixed(4)
}

function scoreTooltip(source) {
  const details = source?.score_details || {}
  const vectorWeight = details.vector_weight
  const bm25Weight = details.bm25_weight
  const searchType = details.search_type || 'balanced'

  return [
    `最终分: ${fixed(source?.score)}`,
    `向量分: ${fixed(source?.vector_score ?? details.vector_score)}`,
    `关键词分: ${fixed(source?.bm25_score ?? details.bm25_score)}`,
    `检索类型: ${searchType}`,
    vectorWeight !== undefined && bm25Weight !== undefined
      ? `公式: ${fixed(vectorWeight)} × 向量分 + ${fixed(bm25Weight)} × 关键词分`
      : '公式: 后端返回的最终相关度分数'
  ].join('\n')
}
</script>

<style scoped>
.sources {
  margin-top: 10px;
}

.sources summary {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  user-select: none;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.source-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  min-height: 64px;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: #f3f4f6;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.source-item:hover {
  border-color: #c7d2fe;
  background: #eef2ff;
}

.source-main {
  min-width: 0;
}

.title {
  display: block;
  overflow: hidden;
  color: #374151;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chunk {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 11px;
}

.score {
  flex: 0 0 auto;
  color: #059669;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.source-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(17, 24, 39, 0.45);
}

.source-modal {
  width: min(640px, 100%);
  max-height: min(80vh, 720px);
  overflow: auto;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.24);
}

.source-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 12px;
  border-bottom: 1px solid #e5e7eb;
}

.source-modal-header h3 {
  margin: 0;
  color: #111827;
  font-size: 16px;
  line-height: 1.4;
}

.close-button {
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
}

.close-button:hover {
  background: #f3f4f6;
  color: #111827;
}

.source-detail-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 16px 20px 20px;
}

.source-detail-list div {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.source-detail-list dt {
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
}

.source-detail-list dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  color: #111827;
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 640px) {
  .source-modal-backdrop {
    align-items: flex-end;
    padding: 12px;
  }

  .source-detail-list div {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>

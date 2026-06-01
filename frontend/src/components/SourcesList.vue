<template>
  <details class="sources">
    <summary>📚 参考 {{ sources.length }} 条来源</summary>
    <div class="sources-list">
      <div v-for="(source, index) in sources" :key="index" class="source-item">
        <div class="title">
          {{ source.title || source.source || '未知来源' }}
          <span class="score">★ {{ ((source.score || 0) * 100).toFixed(1) }}%</span>
        </div>
        <div v-if="source.chunk_index !== undefined" class="chunk">
          Chunk #{{ source.chunk_index }}
        </div>
      </div>
    </div>
  </details>
</template>

<script setup>
defineProps({
  sources: { type: Array, default: () => [] }
})
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
}

.sources-list {
  margin-top: 8px;
}

.source-item {
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 6px;
  margin-bottom: 6px;
  font-size: 12px;
}

.source-item .title {
  font-weight: 600;
  color: #374151;
}

.source-item .score {
  float: right;
  color: #10b981;
}

.source-item .chunk {
  color: #6b7280;
  font-size: 11px;
  margin-top: 4px;
  clear: both;
}
</style>

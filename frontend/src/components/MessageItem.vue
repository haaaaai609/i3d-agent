<template>
  <div :class="['message', message.type]">
    <div v-if="message.type === 'assistant'" class="message-header">
      <span>I3D Assistant</span>
    </div>

    <div class="message-content">
      <div class="message-text" v-html="formattedContent"></div>

      <ThoughtProcess v-if="message.thoughtProcess?.length > 0" :steps="message.thoughtProcess" />
      <SourcesList v-if="message.sources?.length > 0" :sources="message.sources" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ThoughtProcess from './ThoughtProcess.vue'
import SourcesList from './SourcesList.vue'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const formattedContent = computed(() => {
  return renderMarkdown(props.message.content || '')
})

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderInline(value) {
  let text = escapeHtml(value)
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  return text
}

function renderMarkdown(markdown) {
  const lines = String(markdown).replace(/\r\n/g, '\n').split('\n')
  const html = []
  let inCode = false
  let codeLang = ''
  let codeLines = []
  let listType = null

  function closeList() {
    if (listType) {
      html.push(`</${listType}>`)
      listType = null
    }
  }

  function closeCode() {
    html.push(`<pre><code${codeLang ? ` class="language-${escapeHtml(codeLang)}"` : ''}>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
    codeLines = []
    codeLang = ''
    inCode = false
  }

  for (const line of lines) {
    const fence = line.match(/^```(\w+)?\s*$/)
    if (fence) {
      if (inCode) {
        closeCode()
      } else {
        closeList()
        inCode = true
        codeLang = fence[1] || ''
      }
      continue
    }

    if (inCode) {
      codeLines.push(line)
      continue
    }

    if (!line.trim()) {
      closeList()
      continue
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      closeList()
      const level = heading[1].length
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`)
      continue
    }

    const unordered = line.match(/^\s*[-*+]\s+(.+)$/)
    if (unordered) {
      if (listType !== 'ul') {
        closeList()
        listType = 'ul'
        html.push('<ul>')
      }
      html.push(`<li>${renderInline(unordered[1])}</li>`)
      continue
    }

    const ordered = line.match(/^\s*\d+\.\s+(.+)$/)
    if (ordered) {
      if (listType !== 'ol') {
        closeList()
        listType = 'ol'
        html.push('<ol>')
      }
      html.push(`<li>${renderInline(ordered[1])}</li>`)
      continue
    }

    closeList()
    html.push(`<p>${renderInline(line)}</p>`)
  }

  if (inCode) closeCode()
  closeList()
  return html.join('')
}
</script>

<style scoped>
.message {
  margin: 0 auto 22px;
  max-width: 860px;
}

.message.user {
  display: flex;
  justify-content: flex-end;
}

.message-content {
  max-width: 78%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message.user .message-content {
  background: #667eea;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  max-width: 100%;
  background: #fff;
  color: #1f2937;
  border: none;
  padding-left: 0;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #374151;
  font-weight: 600;
}

.message-text {
  line-height: 1.6;
}

.message-text :deep(p) {
  margin: 0 0 10px;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4),
.message-text :deep(h5),
.message-text :deep(h6) {
  margin: 14px 0 8px;
  line-height: 1.35;
  font-weight: 700;
}

.message-text :deep(h1) { font-size: 22px; }
.message-text :deep(h2) { font-size: 19px; }
.message-text :deep(h3) { font-size: 16px; }
.message-text :deep(h4),
.message-text :deep(h5),
.message-text :deep(h6) { font-size: 14px; }

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 8px 0 10px 20px;
  padding: 0;
}

.message-text :deep(li) {
  margin: 4px 0;
}

.message-text :deep(strong) {
  font-weight: 700;
}

.message-text :deep(pre) {
  background: #1f2937;
  color: #f9fafb;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 10px 0;
  font-size: 13px;
}

.message-text :deep(code) {
  background: #e5e7eb;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.message-text :deep(pre code) {
  background: transparent;
  padding: 0;
  border-radius: 0;
}

.message.user .message-text :deep(code) {
  background: rgba(255, 255, 255, 0.2);
}
</style>

<template>
  <div :class="['message', message.type]">
    <div v-if="message.type === 'assistant'" class="message-header">
      <span>I3D Assistant</span>
      <span :class="['agent-badge', (message.agentType || 'supervisor').toLowerCase()]">
        {{ message.agentType || 'supervisor' }}
      </span>
      <span>{{ new Date().toLocaleTimeString() }}</span>
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
  let text = props.message.content || ''

  // Format code blocks
  text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')

  // Format inline code
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')

  // Format line breaks
  text = text.replace(/\n/g, '<br>')

  return text
})
</script>

<style scoped>
.message {
  margin-bottom: 20px;
}

.message.user {
  display: flex;
  justify-content: flex-end;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message.user .message-content {
  background: #667eea;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: white;
  color: #1f2937;
  border: 1px solid #e5e7eb;
  border-bottom-left-radius: 4px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #6b7280;
}

.agent-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.agent-badge.search { background: #dbeafe; color: #1e40af; }
.agent-badge.rag { background: #fef3c7; color: #92400e; }
.agent-badge.process { background: #e0e7ff; color: #3730a3; }
.agent-badge.supervisor { background: #f3e8ff; color: #6b21a8; }

.message-text {
  line-height: 1.6;
}

.message-text pre {
  background: #1f2937;
  color: #f9fafb;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 10px 0;
  font-size: 13px;
}

.message-text code {
  background: #e5e7eb;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.message.user .message-text code {
  background: rgba(255, 255, 255, 0.2);
}
</style>

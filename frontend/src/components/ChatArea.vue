<template>
  <div class="chat-area">
    <div class="chat-header">
      <div class="header-left">
        <h2>{{ sessionTitle }}</h2>
      </div>

      <div :class="['status', { offline: !isOnline }]">
        {{ isOnline ? '在线' : '离线' }}
      </div>
    </div>

    <MessageList
      :messages="messages"
      :is-typing="isTyping"
      @quick-action="handleQuickAction"
    />

    <InputArea
      placeholder="输入消息..."
      :disabled="isTyping"
      @send="handleSend"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import MessageList from './MessageList.vue'
import InputArea from './InputArea.vue'
import { checkHealth } from '../utils/api.js'

const props = defineProps({
  sessionTitle: { type: String, default: '新对话' },
  tenantId: { type: String, default: 'huabei' },
  userId: { type: String, default: 'demo_user' },
  messages: { type: Array, default: () => [] },
  isTyping: { type: Boolean, default: false }
})

const emit = defineEmits(['sendMessage'])

const isOnline = ref(true)

onMounted(async () => {
  const health = await checkHealth()
  isOnline.value = health !== null
})

function handleQuickAction(action) {
  emit('sendMessage', action)
}

function handleSend(data) {
  emit('sendMessage', data)
}
</script>

<style scoped>
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fff;
}

.chat-header {
  padding: 14px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 58px;
}

.header-left {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
  flex: 1;
  min-width: 0;
}

.chat-header h2 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 520px;
  flex-shrink: 0;
}

.status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #10b981;
}

.status::before {
  content: "";
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status.offline {
  color: #ef4444;
}

.status.offline::before {
  background: #ef4444;
  animation: none;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>

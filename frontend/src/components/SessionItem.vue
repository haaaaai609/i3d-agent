<template>
  <div
    class="session-item"
    :class="{ active: isActive, pinned: session.isPinned }"
    @click="$emit('click', session.sessionId)"
  >
    <div class="session-main">
      <span class="session-icon">{{ getAgentIcon(session.agentType) }}</span>
      <span class="session-title">{{ session.title }}</span>
      <span v-if="session.isPinned" class="pin-icon">📌</span>
    </div>

    <div v-if="showActions" class="session-actions">
      <button class="action-btn" @click.stop="$emit('rename')" title="重命名">
        ✏️
      </button>
      <button class="action-btn" @click.stop="$emit('togglePin')" title="固定/取消固定">
        {{ session.isPinned ? '📍' : '📌' }}
      </button>
      <button class="action-btn delete-btn" @click.stop="$emit('delete')" title="删除">
        🗑️
      </button>
    </div>
  </div>
</template>

<script setup>
import { AGENTS } from '../composables/useAgents.js'

const props = defineProps({
  session: { type: Object, required: true },
  isActive: { type: Boolean, default: false },
  showActions: { type: Boolean, default: false }
})

defineEmits(['click', 'rename', 'togglePin', 'delete'])

function getAgentIcon(agentType) {
  return AGENTS[agentType]?.icon || '💬'
}
</script>

<style scoped>
.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.session-item.active {
  background: rgba(102, 126, 234, 0.3);
}

.session-item.pinned {
  border-left: 2px solid #fbbf24;
}

.session-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  overflow: hidden;
}

.session-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.session-title {
  flex: 1;
  font-size: 14px;
  color: white;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pin-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.session-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.action-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.3);
}
</style>

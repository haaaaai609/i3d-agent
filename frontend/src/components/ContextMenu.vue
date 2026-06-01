<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="context-menu"
      :style="{ left: x + 'px', top: y + 'px' }"
      @click.stop
    >
      <div class="menu-item" @click="$emit('rename')">
        <span class="menu-icon">✏️</span>
        <span>重命名</span>
      </div>
      <div class="menu-item" @click="$emit('togglePin')">
        <span class="menu-icon">{{ isPinned ? '📍' : '📌' }}</span>
        <span>{{ isPinned ? '取消固定' : '固定' }}</span>
      </div>
      <div class="menu-divider"></div>
      <div class="menu-item danger" @click="$emit('delete')">
        <span class="menu-icon">🗑️</span>
        <span>删除会话</span>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  isPinned: { type: Boolean, default: false }
})

defineEmits(['rename', 'togglePin', 'delete'])

function handleClickOutside() {
  // Parent component should handle closing
}

function handleEscape(event) {
  if (event.key === 'Escape') {
    // Parent component should handle closing
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleEscape)
})
</script>

<style scoped>
.context-menu {
  position: fixed;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  z-index: 1000;
  min-width: 160px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.menu-item:hover {
  background: #f3f4f6;
}

.menu-item.danger:hover {
  background: #fef2f2;
  color: #ef4444;
}

.menu-icon {
  font-size: 16px;
}

.menu-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 0;
}
</style>

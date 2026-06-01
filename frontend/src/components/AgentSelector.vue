<template>
  <div class="agent-selector">
    <button
      class="agent-selector-button"
      @click="isOpen = !isOpen"
      :class="{ open: isOpen }"
    >
      <span class="agent-icon">{{ currentAgentConfig.icon }}</span>
      <span class="agent-label">{{ currentAgentConfig.title }}</span>
      <span class="dropdown-arrow">{{ isOpen ? '▲' : '▼' }}</span>
    </button>

    <div v-if="isOpen" class="agent-dropdown">
      <div
        v-for="(config, key) in AGENTS"
        :key="key"
        class="agent-option"
        :class="{ selected: key === currentAgent }"
        @click="selectAgent(key)"
      >
        <span class="agent-icon">{{ config.icon }}</span>
        <span class="agent-label">{{ config.title }}</span>
        <span class="agent-badge">{{ config.badge }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { AGENTS } from '../composables/useAgents.js'

const props = defineProps({
  currentAgent: { type: String, default: 'general' }
})

const emit = defineEmits(['agent-changed'])

const isOpen = ref(false)

const currentAgentConfig = computed(() => AGENTS[props.currentAgent])

function selectAgent(agent) {
  emit('agent-changed', agent)
  isOpen.value = false
}

// 点击外部关闭下拉菜单
function handleClickOutside(event) {
  if (!event.target.closest('.agent-selector')) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.agent-selector {
  position: relative;
  width: 280px;
  min-width: 280px;
  flex-shrink: 0;
}

.agent-selector-button {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  white-space: nowrap;
  width: 280px;
  min-width: 280px;
  flex-shrink: 0;
}

.agent-selector-button:hover {
  border-color: #667eea;
  background: #f9fafb;
}

.agent-selector-button.open {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.agent-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.agent-label {
  flex: 1;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dropdown-arrow {
  font-size: 10px;
  color: #9ca3af;
  flex-shrink: 0;
}

.agent-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  width: 280px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  z-index: 1000;
  max-height: 400px;
  overflow-y: auto;
}

.agent-dropdown::-webkit-scrollbar {
  width: 6px;
}

.agent-dropdown::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.agent-dropdown::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.agent-dropdown::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}

.agent-option {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.agent-option:hover {
  background: #f3f4f6;
}

.agent-option.selected {
  background: #eff6ff;
  color: #2563eb;
}

.agent-option .agent-icon {
  flex-shrink: 0;
}

.agent-option .agent-label {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-badge {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 12px;
  background: #e5e7eb;
  color: #6b7280;
  flex-shrink: 0;
}

.agent-option.selected .agent-badge {
  background: #dbeafe;
  color: #2563eb;
}
</style>

<template>
  <div class="session-sidebar">
    <!-- 新建会话按钮 -->
    <button class="new-chat-btn" @click="$emit('newChat')">
      <span class="plus-icon">+</span>
      <span>新建对话</span>
    </button>

    <!-- 会话列表 -->
    <div class="session-list">
      <div v-if="sessions.length === 0" class="empty-state">
        <p>暂无会话</p>
      </div>

      <SessionItem
        v-for="session in sessions"
        :key="session.sessionId"
        :session="session"
        :is-active="session.sessionId === activeSessionId"
        :show-actions="true"
        @click="$emit('switchSession', $event)"
        @rename="$emit('renameSession', session.sessionId)"
        @togglePin="$emit('togglePin', session.sessionId)"
        @delete="$emit('deleteSession', session.sessionId)"
      />
    </div>

    <!-- 设置折叠区 -->
    <details class="settings-section">
      <summary class="settings-header">设置</summary>
      <div class="settings-content">
        <div class="setting-item">
          <label>租户</label>
          <select :value="tenantId" @change="$emit('tenantChanged', $event.target.value)">
            <option value="huabei">华贝 (huabei)</option>
            <option value="shenfa">申发 (shenfa)</option>
            <option value="meidi">美的 (meidi)</option>
            <option value="dongjiang">东江 (dongjiang)</option>
          </select>
        </div>
        <div class="setting-item">
          <label>用户 ID</label>
          <input
            type="text"
            :value="userId"
            @input="$emit('userIdChanged', $event.target.value)"
            placeholder="输入用户ID"
          >
        </div>
      </div>
    </details>
  </div>
</template>

<script setup>
import SessionItem from './SessionItem.vue'

defineProps({
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: String, default: null },
  tenantId: { type: String, default: 'huabei' },
  userId: { type: String, default: 'demo_user' }
})

defineEmits([
  'newChat',
  'switchSession',
  'renameSession',
  'togglePin',
  'deleteSession',
  'tenantChanged',
  'userIdChanged'
])
</script>

<style scoped>
.session-sidebar {
  width: 280px;
  background: #1a1a2e;
  color: white;
  display: flex;
  flex-direction: column;
  padding: 16px;
  height: 100%;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  margin-bottom: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.new-chat-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: #667eea;
}

.plus-icon {
  font-size: 18px;
  font-weight: 300;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 16px;
}

.session-list::-webkit-scrollbar {
  width: 4px;
}

.session-list::-webkit-scrollbar-track {
  background: transparent;
}

.session-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
}

.settings-section {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.settings-header {
  padding: 12px 0;
  cursor: pointer;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  user-select: none;
}

.settings-header:hover {
  color: rgba(255, 255, 255, 0.9);
}

.settings-content {
  padding: 12px 0;
  padding-left: 0;
}

.setting-item {
  margin-bottom: 12px;
}

.setting-item label {
  display: block;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 4px;
}

.setting-item select,
.setting-item input {
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 13px;
}

.setting-item select option {
  background: #1a1a2e;
}
</style>

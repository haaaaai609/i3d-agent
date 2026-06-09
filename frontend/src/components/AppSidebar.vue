<template>
  <aside class="app-sidebar">
    <div class="brand">
      <div class="brand-mark">I3D</div>
      <div>
        <h1>Agent System</h1>
        <p>{{ tenantId }}</p>
      </div>
    </div>

    <nav class="primary-nav" aria-label="主菜单">
      <button
        type="button"
        :class="['nav-item', { active: activeView === 'chat' }]"
        @click="$emit('viewChanged', 'chat')"
      >
        <span>对话</span>
      </button>
      <button
        type="button"
        :class="['nav-item', { active: activeView === 'rag' }]"
        @click="$emit('viewChanged', 'rag')"
      >
        <span>RAG 管理</span>
      </button>
    </nav>

    <section v-if="activeView === 'chat'" class="sidebar-section">
      <button class="new-chat-btn" type="button" @click="$emit('newChat')">
        <span class="plus-icon">+</span>
        <span>新建对话</span>
      </button>

      <div class="section-label">历史会话</div>
      <div class="session-list">
        <div v-if="sessions.length === 0" class="empty-state">暂无会话</div>
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
    </section>

    <section v-else class="sidebar-section rag-menu">
      <div class="section-label">知识库工作台</div>
      <p>文档接入、索引监控、检索调试和质量反馈。</p>
    </section>

    <button class="settings-btn" type="button" @click="$emit('openSettings')">
      <span>设置</span>
      <small>{{ userId }}</small>
    </button>
  </aside>
</template>

<script setup>
import SessionItem from './SessionItem.vue'

defineProps({
  activeView: { type: String, default: 'chat' },
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: String, default: null },
  tenantId: { type: String, default: 'huabei' },
  userId: { type: String, default: 'demo_user' }
})

defineEmits([
  'viewChanged',
  'newChat',
  'switchSession',
  'renameSession',
  'togglePin',
  'deleteSession',
  'openSettings'
])
</script>

<style scoped>
.app-sidebar {
  width: 292px;
  height: 100%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e5e7eb;
  background: #f7f7f8;
  color: #111827;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 12px;
}

.brand-mark {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.brand h1 {
  margin: 0;
  font-size: 15px;
  line-height: 1.2;
}

.brand p {
  margin: 2px 0 0;
  color: #6b7280;
  font-size: 12px;
}

.primary-nav {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 8px 12px 14px;
}

.nav-item {
  min-height: 36px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #374151;
  cursor: pointer;
  font-size: 14px;
}

.nav-item:hover {
  background: #ececf1;
}

.nav-item.active {
  border-color: #d1d5db;
  background: #fff;
  color: #111827;
  font-weight: 700;
}

.sidebar-section {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 12px 12px;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  min-height: 40px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.new-chat-btn:hover {
  background: #f3f4f6;
}

.plus-icon {
  font-size: 18px;
  line-height: 1;
}

.section-label {
  margin: 16px 4px 8px;
  color: #6b7280;
  font-size: 12px;
  font-weight: 700;
}

.session-list {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
}

.empty-state {
  padding: 28px 12px;
  color: #9ca3af;
  text-align: center;
  font-size: 13px;
}

.rag-menu p {
  margin: 0 4px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.settings-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 12px;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  cursor: pointer;
  font-size: 14px;
  text-align: left;
}

.settings-btn:hover {
  background: #f3f4f6;
}

.settings-btn small {
  min-width: 0;
  overflow: hidden;
  color: #6b7280;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

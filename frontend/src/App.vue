<template>
  <div class="app-shell">
    <AppSidebar
      :active-view="activeView"
      :sessions="sessions"
      :active-session-id="activeSessionId"
      :tenant-id="tenantId"
      :user-id="userId"
      @view-changed="activeView = $event"
      @new-chat="handleNewChat"
      @switch-session="handleSwitchSession"
      @rename-session="handleRenameSession"
      @toggle-pin="handleTogglePin"
      @delete-session="handleDeleteSession"
      @open-settings="isSettingsOpen = true"
    />

    <main class="main-panel">
      <ChatArea
        v-if="activeView === 'chat'"
        :session-title="currentSession?.title || '新对话'"
        :tenant-id="tenantId"
        :user-id="userId"
        :messages="messages"
        :is-typing="isTyping"
        @send-message="handleSendMessage"
      />
      <RagConsole
        v-else
        :tenant-id="tenantId"
      />
    </main>

    <SettingsModal
      :open="isSettingsOpen"
      :tenant-id="tenantId"
      :user-id="userId"
      :stream-mode="streamMode"
      @close="isSettingsOpen = false"
      @tenant-changed="handleTenantChanged"
      @user-id-changed="handleUserIdChanged"
      @stream-mode-changed="streamMode = $event"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppSidebar from './components/AppSidebar.vue'
import SettingsModal from './components/SettingsModal.vue'
import ChatArea from './components/ChatArea.vue'
import RagConsole from './components/rag/RagConsole.vue'
import { useSessions } from './composables/useSessions.js'
import { useChat } from './composables/useChat.js'

const tenantId = ref('huabei')
const userId = ref('demo_user')
const streamMode = ref(true)
const activeView = ref('chat')
const isSettingsOpen = ref(false)

// 会话管理
const {
  sessions,
  activeSessionId,
  currentSession,
  loadSessions,
  createSession,
  switchSession,
  deleteSession,
  renameSession,
  updateSessionTitle,
  togglePinSession,
  updateSessionMeta
} = useSessions()

// 聊天消息（传入 activeSessionId）
const { messages, isTyping, sendMessage, addMessage } = useChat(activeSessionId)

// 初始化
onMounted(() => {
  loadSessions()
})

// 监听会话切换
function handleSwitchSession(sessionId) {
  if (switchSession(sessionId)) {
    // 会话已切换，useChat 会自动加载缓存消息
  }
}

// 新建会话
function handleNewChat() {
  createSession()
  activeView.value = 'chat'
}

// 重命名会话
function handleRenameSession(sessionId) {
  const newTitle = prompt('请输入新的会话名称：')
  if (newTitle) {
    renameSession(sessionId, newTitle)
  }
}

// 固定/取消固定会话
function handleTogglePin(sessionId) {
  togglePinSession(sessionId)
}

// 删除会话
function handleDeleteSession(sessionId) {
  const session = sessions.value.find(s => s.sessionId === sessionId)
  if (session) {
    if (confirm(`确定要删除会话 "${session.title}" 吗？`)) {
      deleteSession(sessionId)
    }
  }
}

// 租户变更
function handleTenantChanged(tenant) {
  tenantId.value = tenant
}

// 用户 ID 变更
function handleUserIdChanged(user) {
  userId.value = user
}

// 发送消息
async function handleSendMessage(data) {
  if (!activeSessionId.value) return

  const messageContent = typeof data === 'string' ? data : data.message

  // 更新会话标题（如果是首条消息）
  const session = currentSession.value
  if (session && session.messageCount === 0 && messageContent) {
    updateSessionTitle(activeSessionId.value, messageContent)
  }

  // 发送消息
  await sendMessage(messageContent, userId.value, tenantId.value, streamMode.value)

  // 更新会话元信息
  updateSessionMeta(activeSessionId.value, {
    messageCount: (session?.messageCount || 0) + 1
  })
}

// 键盘快捷键
function handleKeydown(event) {
  // Ctrl/Cmd + N: 新建会话
  if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
    event.preventDefault()
    handleNewChat()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.app-shell {
  width: 100%;
  height: 100vh;
  display: flex;
  overflow: hidden;
  background: #fff;
}

.main-panel {
  min-width: 0;
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>

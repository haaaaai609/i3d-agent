# Frontend Session Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现前端会话记忆功能，包括多会话管理、持久化存储、消息缓存和 UI 重构

**Architecture:** 使用 localStorage 持久化会话列表和消息缓存（最近20条），通过 Nanoid 生成唯一 session_id，与后端 Redis 记忆系统通过 session_id 隔离。UI 采用类似 ChatGPT 的侧边栏会话列表设计。

**Tech Stack:** Vue 3 Composition API, Nanoid, localStorage, Redis (后端)

---

## File Structure

```
/frontend/src/
├── composables/
│   ├── useSessions.js          # 新建：会话管理逻辑
│   ├── useMessages.js          # 修改：支持 sessionId 和缓存
│   └── usePreferences.js       # 新建：用户偏好管理
├── components/
│   ├── Sidebar.vue             # 修改：改为会话侧边栏
│   ├── SessionSidebar.vue      # 新建：会话列表容器
│   ├── SessionItem.vue         # 新建：单个会话项
│   ├── AgentSelector.vue       # 新建：Agent 下拉选择器
│   ├── ContextMenu.vue         # 新建：右键菜单
│   └── ChatArea.vue            # 修改：添加 AgentSelector
├── utils/
│   └── storage.js              # 新建：localStorage 工具
└── App.vue                     # 修改：调整布局和状态管理
```

---

## Task 1: 安装 Nanoid 依赖

**Files:**
- Modify: `/data/yzh/i3d-agent-system/frontend/package.json`

- [ ] **Step 1: 更新 package.json 添加 nanoid 依赖**

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "nanoid": "^5.0.0"
  }
}
```

- [ ] **Step 2: 安装依赖**

```bash
cd /data/yzh/i3d-agent-system/frontend
npm install
```

Expected: `added 1 package`

- [ ] **Step 3: 验证安装**

```bash
grep -A 2 '"dependencies"' package.json
```

Expected: 输出包含 `"nanoid": "^5.0.0"`

---

## Task 2: 创建 localStorage 工具模块

**Files:**
- Create: `/data/yzh/i3d-agent-system/frontend/src/utils/storage.js`

- [ ] **Step 1: 创建 storage.js 工具模块**

```javascript
const STORAGE_KEYS = {
  SESSIONS: 'i3d_sessions',
  ACTIVE_SESSION: 'i3d_active_session',
  MESSAGES_PREFIX: 'i3d_messages_',
  PREFERENCES: 'i3d_preferences',
  FAVORITES: 'i3d_favorites'
}

const MAX_CACHED_MESSAGES = 20

export class StorageManager {
  /**
   * 获取会话列表
   */
  getSessions() {
    const data = localStorage.getItem(STORAGE_KEYS.SESSIONS)
    return data ? JSON.parse(data) : []
  }

  /**
   * 保存会话列表
   */
  saveSessions(sessions) {
    localStorage.setItem(STORAGE_KEYS.SESSIONS, JSON.stringify(sessions))
  }

  /**
   * 获取当前激活会话 ID
   */
  getActiveSessionId() {
    return localStorage.getItem(STORAGE_KEYS.ACTIVE_SESSION)
  }

  /**
   * 设置当前激活会话 ID
   */
  setActiveSessionId(sessionId) {
    localStorage.setItem(STORAGE_KEYS.ACTIVE_SESSION, sessionId)
  }

  /**
   * 获取会话的缓存消息
   */
  getSessionMessages(sessionId) {
    const key = STORAGE_KEYS.MESSAGES_PREFIX + sessionId
    const data = localStorage.getItem(key)
    return data ? JSON.parse(data) : []
  }

  /**
   * 保存会话的缓存消息（只保留最近 N 条）
   */
  saveSessionMessages(sessionId, messages) {
    const key = STORAGE_KEYS.MESSAGES_PREFIX + sessionId
    const toCache = messages.slice(-MAX_CACHED_MESSAGES)
    localStorage.setItem(key, JSON.stringify(toCache))
  }

  /**
   * 删除会话的缓存消息
   */
  deleteSessionMessages(sessionId) {
    const key = STORAGE_KEYS.MESSAGES_PREFIX + sessionId
    localStorage.removeItem(key)
  }

  /**
   * 获取用户偏好
   */
  getPreferences() {
    const data = localStorage.getItem(STORAGE_KEYS.PREFERENCES)
    const defaults = {
      defaultTenant: 'huabei',
      defaultAgent: 'general',
      theme: 'light',
      language: 'zh-CN',
      pinnedSessions: []
    }
    return data ? { ...defaults, ...JSON.parse(data) } : defaults
  }

  /**
   * 保存用户偏好
   */
  savePreferences(preferences) {
    localStorage.setItem(STORAGE_KEYS.PREFERENCES, JSON.stringify(preferences))
  }

  /**
   * 获取收藏列表
   */
  getFavorites() {
    const data = localStorage.getItem(STORAGE_KEYS.FAVORITES)
    return data ? JSON.parse(data) : []
  }

  /**
   * 保存收藏列表
   */
  saveFavorites(favorites) {
    localStorage.setItem(STORAGE_KEYS.FAVORITES, JSON.stringify(favorites))
  }

  /**
   * 检查存储空间是否足够
   */
  checkStorageAvailable() {
    try {
      const testKey = '__storage_test__'
      localStorage.setItem(testKey, 'test')
      localStorage.removeItem(testKey)
      return true
    } catch (e) {
      return false
    }
  }

  /**
   * 获取存储使用情况（估算）
   */
  getStorageUsage() {
    let total = 0
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith('i3d_')) {
        total += localStorage.getItem(key).length
      }
    }
    return {
      used: total,
      percentage: (total / (5 * 1024 * 1024)) * 100  // 假设 5MB 限制
    }
  }
}

export const storage = new StorageManager()
export { STORAGE_KEYS, MAX_CACHED_MESSAGES }
```

---

## Task 3: 创建 useSessions composable

**Files:**
- Create: `/data/yzh/i3d-agent-system/frontend/src/composables/useSessions.js`

- [ ] **Step 1: 创建 useSessions.js**

```javascript
import { ref, computed, watch } from 'vue'
import { nanoid } from 'nanoid'
import { storage } from '../utils/storage.js'

export function useSessions() {
  const sessions = ref([])
  const activeSessionId = ref(null)

  // 加载会话列表
  function loadSessions() {
    sessions.value = storage.getSessions()
    const savedActiveId = storage.getActiveSessionId()

    // 如果保存的激活会话存在，使用它；否则创建新会话
    if (savedActiveId && sessions.value.find(s => s.sessionId === savedActiveId)) {
      activeSessionId.value = savedActiveId
    } else if (sessions.value.length > 0) {
      activeSessionId.value = sessions.value[0].sessionId
      storage.setActiveSessionId(activeSessionId.value)
    } else {
      createSession()
    }
  }

  // 保存会话列表
  function saveSessions() {
    storage.saveSessions(sessions.value)
  }

  // 创建新会话
  function createSession(agentType = 'general') {
    const sessionId = nanoid()
    const newSession = {
      sessionId,
      title: '新对话',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      agentType,
      messageCount: 0,
      isPinned: false
    }

    sessions.value.unshift(newSession)
    activeSessionId.value = sessionId
    saveSessions()
    storage.setActiveSessionId(sessionId)

    return sessionId
  }

  // 切换会话
  function switchSession(sessionId) {
    if (sessionId !== activeSessionId.value) {
      activeSessionId.value = sessionId
      storage.setActiveSessionId(sessionId)
      return true
    }
    return false
  }

  // 删除会话
  function deleteSession(sessionId) {
    const index = sessions.value.findIndex(s => s.sessionId === sessionId)
    if (index !== -1) {
      sessions.value.splice(index, 1)

      // 清除消息缓存
      storage.deleteSessionMessages(sessionId)

      // 如果删除的是当前会话，切换到第一个或创建新会话
      if (sessionId === activeSessionId.value) {
        if (sessions.value.length > 0) {
          activeSessionId.value = sessions.value[0].sessionId
        } else {
          createSession()
        }
        storage.setActiveSessionId(activeSessionId.value)
      }

      saveSessions()
    }
  }

  // 重命名会话
  function renameSession(sessionId, newTitle) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session && newTitle.trim()) {
      session.title = newTitle.trim()
      session.updatedAt = Date.now()
      saveSessions()
    }
  }

  // 更新会话标题（使用首条消息）
  function updateSessionTitle(sessionId, firstMessage) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session && session.title === '新对话') {
      // 取前 20 个字符作为标题
      session.title = firstMessage.slice(0, 20) + (firstMessage.length > 20 ? '...' : '')
      session.updatedAt = Date.now()
      saveSessions()
    }
  }

  // 固定/取消固定会话
  function togglePinSession(sessionId) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session) {
      session.isPinned = !session.isPinned
      session.updatedAt = Date.now()
      saveSessions()
    }
  }

  // 更新会话元信息（发送消息后调用）
  function updateSessionMeta(sessionId, updates) {
    const session = sessions.value.find(s => s.sessionId === sessionId)
    if (session) {
      Object.assign(session, updates)
      session.updatedAt = Date.now()
      saveSessions()
    }
  }

  // 排序后的会话列表
  const sortedSessions = computed(() => {
    return [...sessions.value].sort((a, b) => {
      if (a.isPinned && !b.isPinned) return -1
      if (!a.isPinned && b.isPinned) return 1
      return b.updatedAt - a.updatedAt
    })
  })

  // 获取当前会话
  const currentSession = computed(() => {
    return sessions.value.find(s => s.sessionId === activeSessionId.value)
  })

  return {
    sessions: sortedSessions,
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
  }
}
```

---

## Task 4: 创建 usePreferences composable

**Files:**
- Create: `/data/yzh/i3d-agent-system/frontend/src/composables/usePreferences.js`

- [ ] **Step 1: 创建 usePreferences.js**

```javascript
import { ref, watch } from 'vue'
import { storage } from '../utils/storage.js'

export function usePreferences() {
  const preferences = ref(storage.getPreferences())

  // 加载偏好
  function loadPreferences() {
    preferences.value = storage.getPreferences()
  }

  // 保存偏好
  function savePreferences() {
    storage.savePreferences(preferences.value)
  }

  // 更新单个偏好
  function setPreference(key, value) {
    preferences.value[key] = value
    savePreferences()
  }

  // 添加/移除固定会话
  function togglePinnedSession(sessionId) {
    const pinned = preferences.value.pinnedSessions || []
    const index = pinned.indexOf(sessionId)
    if (index === -1) {
      pinned.push(sessionId)
    } else {
      pinned.splice(index, 1)
    }
    preferences.value.pinnedSessions = pinned
    savePreferences()
  }

  // 检查会话是否被固定
  function isSessionPinned(sessionId) {
    return (preferences.value.pinnedSessions || []).includes(sessionId)
  }

  // 监听变化自动保存
  watch(preferences, savePreferences, { deep: true })

  return {
    preferences,
    loadPreferences,
    setPreference,
    togglePinnedSession,
    isSessionPinned
  }
}
```

---

## Task 5: 更新 useMessages composable 支持 sessionId

**Files:**
- Modify: `/data/yzh/i3d-agent-system/frontend/src/composables/useChat.js`

- [ ] **Step 1: 完全替换 useChat.js 为新版本**

```javascript
import { ref, watch } from 'vue'
import { sendChatMessage, streamChatMessage } from '../utils/api.js'
import { storage, MAX_CACHED_MESSAGES } from '../utils/storage.js'

export function useChat(sessionId) {
  const messages = ref([])
  const isTyping = ref(false)

  // 从 localStorage 加载缓存的消息
  function loadCachedMessages() {
    if (!sessionId.value) {
      messages.value = []
      return
    }
    messages.value = storage.getSessionMessages(sessionId.value)
  }

  // 保存消息到缓存（只保留最近20条）
  function saveCachedMessages() {
    if (!sessionId.value) return
    storage.saveSessionMessages(sessionId.value, messages.value)
  }

  // 监听 sessionId 变化，自动加载缓存
  watch(sessionId, (newId) => {
    if (newId) {
      loadCachedMessages()
    }
  }, { immediate: true })

  // 监听 messages 变化，自动保存缓存
  watch(messages, () => {
    saveCachedMessages()
  }, { deep: true })

  function addMessage(type, content, metadata = {}) {
    messages.value.push({
      id: Date.now() + Math.random(),
      type,
      content,
      timestamp: Date.now(),
      ...metadata
    })
  }

  async function sendMessage(message, userId, tenantId, streamMode = true) {
    if (!sessionId.value) {
      console.error('No active session')
      return
    }

    // Add user message
    const userContent = message
    addMessage('user', userContent)

    isTyping.value = true

    try {
      const payload = {
        message: message,
        user_id: userId,
        tenant_id: tenantId,
        session_id: sessionId.value
      }

      if (streamMode) {
        let fullContent = ''
        let assistantMessageId = null

        await streamChatMessage(
          payload,
          (content) => {
            fullContent += content
            // Update or create assistant message
            if (assistantMessageId) {
              const msg = messages.value.find(m => m.id === assistantMessageId)
              if (msg) msg.content = fullContent
            } else {
              assistantMessageId = Date.now() + Math.random()
              messages.value.push({
                id: assistantMessageId,
                type: 'assistant',
                content: fullContent,
                agentType: 'supervisor',
                timestamp: Date.now()
              })
            }
          },
          (data) => {
            if (!fullContent) fullContent = '处理完成'
            // Add sources if available
            if (data.sources && data.sources.length > 0 && assistantMessageId) {
              const msg = messages.value.find(m => m.id === assistantMessageId)
              if (msg) msg.sources = data.sources
            }
          },
          (error) => {
            addMessage('assistant', `❌ 错误: ${error}`, { agentType: 'supervisor' })
          }
        )
      } else {
        const data = await sendChatMessage(payload)
        addMessage('assistant', data.response || '处理完成', {
          agentType: data.metadata?.agent || 'supervisor',
          sources: data.sources || [],
          thoughtProcess: data.thought_process || []
        })
      }
    } catch (error) {
      addMessage('assistant', `❌ 错误: ${error.message}`, { agentType: 'supervisor' })
    } finally {
      isTyping.value = false
    }
  }

  return {
    messages,
    isTyping,
    addMessage,
    sendMessage,
    loadCachedMessages
  }
}
```

---

## Task 6: 创建 AgentSelector 组件

**Files:**
- Create: `/data/yzh/i3d-agent-system/frontend/src/components/AgentSelector.vue`

- [ ] **Step 1: 创建 AgentSelector.vue**

```vue
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
}

.agent-selector-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
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
}

.agent-label {
  flex: 1;
  font-weight: 500;
}

.dropdown-arrow {
  font-size: 10px;
  color: #9ca3af;
}

.agent-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 100;
}

.agent-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.agent-option:hover {
  background: #f9fafb;
}

.agent-option.selected {
  background: #eff6ff;
}

.agent-option .agent-label {
  flex: 1;
  font-size: 14px;
}

.agent-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #e5e7eb;
  color: #6b7280;
}
</style>
```

---

## Task 7: 创建 SessionItem 组件

**Files:**
- Create: `/data/yzh/i3d-agent-system/frontend/src/components/SessionItem.vue`

- [ ] **Step 1: 创建 SessionItem.vue**

```vue
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
import { computed } from 'vue'
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
```

---

## Task 8: 创建 SessionSidebar 组件

**Files:**
- Create: `/data/yzh/i3d-agent-system/frontend/src/components/SessionSidebar.vue`

- [ ] **Step 1: 创建 SessionSidebar.vue**

```vue
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
```

---

## Task 9: 创建 ContextMenu 组件

**Files:**
- Create: `/data/yzh/i3d-agent-system/frontend/src/components/ContextMenu.vue`

- [ ] **Step 1: 创建 ContextMenu.vue**

```vue
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
```

---

## Task 10: 更新 ChatArea 组件添加 AgentSelector

**Files:**
- Modify: `/data/yzh/i3d-agent-system/frontend/src/components/ChatArea.vue`

- [ ] **Step 1: 完全替换 ChatArea.vue**

```vue
<template>
  <div class="chat-area">
    <div class="chat-header">
      <div class="header-left">
        <h2>{{ sessionTitle }}</h2>
        <AgentSelector
          :current-agent="currentAgent"
          @agent-changed="$emit('agentChanged', $event)"
        />
      </div>

      <div style="display: flex; align-items: center; gap: 15px;">
        <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
          <input
            type="checkbox"
            :checked="streamMode"
            @change="$emit('streamModeToggle')"
            style="cursor: pointer;"
          >
          <span>流式输出</span>
        </label>
        <div :class="['status', { offline: !isOnline }]">
          {{ isOnline ? '在线' : '离线' }}
        </div>
      </div>
    </div>

    <MessageList
      :messages="messages"
      :is-typing="isTyping"
      @quick-action="handleQuickAction"
    />

    <InputArea
      :placeholder="getInputPlaceholder()"
      :disabled="isTyping"
      @send="handleSend"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { AGENTS } from '../composables/useAgents.js'
import AgentSelector from './AgentSelector.vue'
import MessageList from './MessageList.vue'
import InputArea from './InputArea.vue'
import { checkHealth } from '../utils/api.js'

const props = defineProps({
  sessionTitle: { type: String, default: '新对话' },
  currentAgent: { type: String, default: 'general' },
  tenantId: { type: String, default: 'huabei' },
  userId: { type: String, default: 'demo_user' },
  streamMode: { type: Boolean, default: true },
  messages: { type: Array, default: () => [] },
  isTyping: { type: Boolean, default: false }
})

const emit = defineEmits(['agentChanged', 'streamModeToggle', 'sendMessage'])

const isOnline = ref(true)

const agentConfig = computed(() => AGENTS[props.currentAgent])

onMounted(async () => {
  const health = await checkHealth()
  isOnline.value = health !== null
})

function getInputPlaceholder() {
  return agentConfig.value?.prompt || '输入消息...'
}

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
}

.chat-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chat-header h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
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
```

---

## Task 11: 更新 App.vue 集成会话管理

**Files:**
- Modify: `/data/yzh/i3d-agent-system/frontend/src/App.vue`

- [ ] **Step 1: 完全替换 App.vue**

```vue
<template>
  <div class="container">
    <SessionSidebar
      :sessions="sessions"
      :active-session-id="activeSessionId"
      :tenant-id="tenantId"
      :user-id="userId"
      @new-chat="handleNewChat"
      @switch-session="handleSwitchSession"
      @rename-session="handleRenameSession"
      @toggle-pin="handleTogglePin"
      @delete-session="handleDeleteSession"
      @tenant-changed="handleTenantChanged"
      @user-id-changed="handleUserIdChanged"
    />
    <ChatArea
      :session-title="currentSession?.title || '新对话'"
      :current-agent="currentAgent"
      :tenant-id="tenantId"
      :user-id="userId"
      :stream-mode="streamMode"
      :messages="messages"
      :is-typing="isTyping"
      @agent-changed="handleAgentChanged"
      @stream-mode-toggle="streamMode = !streamMode"
      @send-message="handleSendMessage"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import SessionSidebar from './components/SessionSidebar.vue'
import ChatArea from './components/ChatArea.vue'
import { useSessions } from './composables/useSessions.js'
import { useChat } from './composables/useChat.js'

const tenantId = ref('huabei')
const userId = ref('demo_user')
const streamMode = ref(true)
const currentAgent = ref('general')

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
  createSession(currentAgent.value)
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

// 切换 Agent
function handleAgentChanged(agent) {
  currentAgent.value = agent
  if (currentSession.value) {
    updateSessionMeta(currentSession.value.sessionId, { agentType: agent })
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
.container {
  width: 95%;
  max-width: 1200px;
  height: 90vh;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  display: flex;
  overflow: hidden;
  margin: 5vh auto;
}
</style>
```

---

## Task 12: 更新 Docker 构建测试

**Files:**
- Test: Docker build

- [ ] **Step 1: 构建前端 Docker 镜像**

```bash
cd /data/yzh/i3d-agent-system
docker compose build i3d-agent-frontend
```

Expected: 构建成功，无错误

- [ ] **Step 2: 启动所有服务**

```bash
docker compose up -d
```

Expected: 所有服务启动成功

- [ ] **Step 3: 验证前端运行**

访问: http://localhost:8080

Expected:
- 页面加载
- 显示会话侧边栏
- "新建对话"按钮可点击
- 设置折叠区可展开

---

## Success Criteria

完成以下检查点即视为完成：

1. ✅ 会话列表显示在左侧边栏
2. ✅ 点击"新建对话"创建新会话（session_id 为 Nanoid）
3. ✅ 点击会话项可切换会话
4. ✅ 右键菜单支持重命名、固定、删除
5. ✅ Agent 选择器在聊天区域顶部
6. ✅ 发送消息后会话元信息更新
7. ✅ 首条消息自动成为会话标题
8. ✅ 刷新页面后会话列表恢复
9. ✅ 消息缓存正常工作（最近20条）
10. ✅ 设置折叠区正常工作
11. ✅ Docker 构建成功

---

**End of Implementation Plan**

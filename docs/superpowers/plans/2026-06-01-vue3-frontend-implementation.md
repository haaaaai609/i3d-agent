# Vue 3 Frontend Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the I3D Agent System frontend using Vue 3 + Vite + Composition API while preserving all existing functionality from the single HTML file.

**Architecture:** Single-page application with reactive state management using Vue 3 composables. Components communicate via props and emits. API calls use native fetch with SSE streaming support. Styles ported from existing HTML.

**Tech Stack:** Vue 3.4+, Vite 5.0+, Composition API, plain CSS

---

## File Structure

```
/frontend/
├── index.html                  # Entry HTML (minimal, loads main.js)
├── package.json                # Dependencies and scripts
├── vite.config.js              # Vite configuration with proxy
├── public/                     # Static assets
└── src/
    ├── main.js                 # App entry point
    ├── App.vue                 # Root component (layout)
    ├── components/
    │   ├── Sidebar.vue         # Agent selection & settings
    │   ├── ChatArea.vue        # Main chat container
    │   ├── MessageList.vue     # Scrollable messages
    │   ├── MessageItem.vue     # Single message
    │   ├── InputArea.vue       # Message input
    │   ├── WelcomeScreen.vue   # Welcome with quick actions
    │   ├── SourcesList.vue     # Sources display
    │   └── ThoughtProcess.vue  # Thought steps display
    ├── composables/
    │   ├── useChat.js          # Chat logic & API
    │   └── useAgents.js        # Agent selection
    ├── styles/
    │   └── main.css            # Ported CSS
    └── utils/
        └── api.js              # API wrapper
```

---

## Task 1: Project Initialization

**Files:**
- Create: `/frontend/package.json`
- Create: `/frontend/vite.config.js`
- Create: `/frontend/index.html`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "i3d-agent-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

- [ ] **Step 2: Create vite.config.js**

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})
```

- [ ] **Step 3: Create index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>I3D Agent System - 智能助手</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

- [ ] **Step 4: Create directory structure**

Run:
```bash
mkdir -p /frontend/src/components
mkdir -p /frontend/src/composables
mkdir -p /frontend/src/styles
mkdir -p /frontend/src/utils
mkdir -p /frontend/public
```

- [ ] **Step 5: Install dependencies**

Run:
```bash
cd /frontend
npm install
```

Expected: `node_modules` created, no errors

---

## Task 2: Main Entry Point

**Files:**
- Create: `/frontend/src/main.js`
- Create: `/frontend/src/App.vue`

- [ ] **Step 1: Create main.js**

```js
import { createApp } from 'vue'
import App from './App.vue'
import './styles/main.css'

createApp(App).mount('#app')
```

- [ ] **Step 2: Create App.vue root component**

```vue
<template>
  <div class="container">
    <Sidebar
      :current-agent="currentAgent"
      :tenant-id="tenantId"
      :user-id="userId"
      @agent-selected="handleAgentSelected"
      @tenant-changed="handleTenantChanged"
      @user-changed="handleUserChanged"
    />
    <ChatArea
      :current-agent="currentAgent"
      :tenant-id="tenantId"
      :user-id="userId"
      :stream-mode="streamMode"
      @stream-mode-toggle="streamMode = !streamMode"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatArea from './components/ChatArea.vue'

const currentAgent = ref('general')
const tenantId = ref('huabei')
const userId = ref('demo_user')
const streamMode = ref(true)

const handleAgentSelected = (agent) => {
  currentAgent.value = agent
}

const handleTenantChanged = (tenant) => {
  tenantId.value = tenant
}

const handleUserChanged = (user) => {
  userId.value = user
}
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

## Task 3: useAgents Composable

**Files:**
- Create: `/frontend/src/composables/useAgents.js`

- [ ] **Step 1: Create useAgents.js composable**

```js
import { ref } from 'vue'

export const AGENTS = {
  general: { title: '通用对话', icon: '💬', badge: '默认', prompt: '' },
  search: { title: '3D 模型搜索', icon: '🔍', badge: 'Search', prompt: '搜索：' },
  '2d-search': { title: '2D 图片搜索', icon: '🖼️', badge: 'Search', prompt: '请上传 2D 图片进行搜索，或描述：' },
  rag: { title: '技术文档查询', icon: '📚', badge: 'RAG', prompt: '文档查询：' },
  api: { title: 'API 参考', icon: '🔧', badge: 'RAG', prompt: 'API 查询：' },
  deploy: { title: '部署指南', icon: '🚀', badge: 'RAG', prompt: '部署问题：' },
  troubleshoot: { title: '故障排查', icon: '🔧', badge: 'RAG', prompt: '故障排查：' },
  process: { title: '任务状态查询', icon: '⚙️', badge: 'Process', prompt: '查询任务状态：' },
  history: { title: '处理历史', icon: '📋', badge: 'Process', prompt: '查询处理历史：' }
}

export function useAgents(initialAgent = 'general') {
  const currentAgent = ref(initialAgent)

  function selectAgent(agent) {
    if (AGENTS[agent]) {
      currentAgent.value = agent
    }
  }

  function getCurrentAgentConfig() {
    return AGENTS[currentAgent.value]
  }

  return {
    AGENTS,
    currentAgent,
    selectAgent,
    getCurrentAgentConfig
  }
}
```

---

## Task 4: API Utility

**Files:**
- Create: `/frontend/src/utils/api.js`

- [ ] **Step 1: Create API wrapper utility**

```js
const API_BASE = window.location.origin

export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin'
    })
    return response.ok ? await response.json() : null
  } catch (error) {
    console.warn('API health check failed:', error)
    return null
  }
}

export async function sendChatMessage(payload) {
  const response = await fetch(`${API_BASE}/api/v1/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': payload.tenant_id
    },
    body: JSON.stringify(payload)
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  return response.json()
}

export async function streamChatMessage(payload, onContent, onDone, onError) {
  const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': payload.tenant_id
    },
    body: JSON.stringify(payload)
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))

          if (data.type === 'content') {
            onContent(data.content)
          } else if (data.type === 'done') {
            onDone(data)
          } else if (data.type === 'error') {
            onError(data.error)
          }
        } catch (e) {
          console.error('Error parsing SSE data:', e)
        }
      }
    }
  }
}
```

---

## Task 5: useChat Composable

**Files:**
- Create: `/frontend/src/composables/useChat.js`

- [ ] **Step 1: Create useChat.js composable**

```js
import { ref } from 'vue'
import { sendChatMessage, streamChatMessage } from '../utils/api.js'

export function useChat() {
  const messages = ref([])
  const isTyping = ref(false)
  const sessionId = ref(null)
  const attachedFile = ref(null)

  function addMessage(type, content, metadata = {}) {
    messages.value.push({
      id: Date.now() + Math.random(),
      type,
      content,
      ...metadata
    })
  }

  async function sendMessage(message, userId, tenantId, streamMode = true) {
    const currentSessionId = sessionId.value || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    // Add user message
    const userContent = message + (attachedFile.value ? ` [文件: ${attachedFile.value.name}]` : '')
    addMessage('user', userContent)

    isTyping.value = true

    try {
      const payload = {
        message: message || `处理上传的文件: ${attachedFile.value?.name || ''}`,
        user_id: userId,
        tenant_id: tenantId,
        session_id: currentSessionId
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
                agentType: 'supervisor'
              })
            }
          },
          (data) => {
            if (!fullContent) fullContent = '处理完成'
            sessionId.value = data.session_id
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
        sessionId.value = data.session_id
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
      // Clear attached file
      attachedFile.value = null
    }
  }

  function setFile(file) {
    attachedFile.value = file
  }

  function clearFile() {
    attachedFile.value = null
  }

  return {
    messages,
    isTyping,
    sessionId,
    attachedFile,
    addMessage,
    sendMessage,
    setFile,
    clearFile
  }
}
```

---

## Task 6: Sidebar Component

**Files:**
- Create: `/frontend/src/components/Sidebar.vue`

- [ ] **Step 1: Create Sidebar.vue component**

```vue
<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h1>I3D Agent System</h1>
      <p>智能多代理助手</p>
    </div>

    <div class="agent-section">
      <h3>Agent 功能</h3>
      <button
        v-for="(config, key) in AGENTS"
        :key="key"
        :class="['agent-btn', { active: currentAgent === key }]"
        @click="$emit('agent-selected', key)"
      >
        <span class="icon">{{ config.icon }}</span>
        <span class="label">{{ config.title }}</span>
        <span class="badge">{{ config.badge }}</span>
      </button>
    </div>

    <div class="settings">
      <div class="setting-item">
        <label>租户</label>
        <select :value="tenantId" @change="$emit('tenant-changed', $event.target.value)">
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
          @input="$emit('user-changed', $event.target.value)"
          placeholder="输入用户ID"
        >
      </div>
    </div>
  </div>
</template>

<script setup>
import { AGENTS } from '../composables/useAgents.js'

defineProps({
  currentAgent: { type: String, default: 'general' },
  tenantId: { type: String, default: 'huabei' },
  userId: { type: String, default: 'demo_user' }
})

defineEmits(['agent-selected', 'tenant-changed', 'user-changed'])
</script>

<style scoped>
.sidebar {
  width: 280px;
  background: #1a1a2e;
  color: white;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.sidebar-header {
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 20px;
}

.sidebar-header h1 {
  font-size: 20px;
  font-weight: 600;
}

.sidebar-header p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 5px;
}

.agent-section {
  flex: 1;
}

.agent-section h3 {
  font-size: 12px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 15px;
}

.agent-btn {
  width: 100%;
  padding: 12px 16px;
  margin-bottom: 8px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  text-align: left;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.agent-btn.active {
  background: #667eea;
}

.agent-btn .icon {
  font-size: 18px;
}

.agent-btn .label {
  flex: 1;
}

.agent-btn .badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.2);
}

.settings {
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
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

## Task 7: ChatArea Component

**Files:**
- Create: `/frontend/src/components/ChatArea.vue`

- [ ] **Step 1: Create ChatArea.vue component**

```vue
<template>
  <div class="chat-area">
    <div class="chat-header">
      <h2>{{ agentConfig?.title || '通用对话' }}</h2>
      <div style="display: flex; align-items: center; gap: 15px;">
        <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
          <input
            type="checkbox"
            :checked="streamMode"
            @change="$emit('stream-mode-toggle')"
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
      :placeholder="agentConfig?.prompt || '输入消息...'"
      :disabled="isTyping"
      @send="handleSend"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { AGENTS } from '../composables/useAgents.js'
import MessageList from './MessageList.vue'
import InputArea from './InputArea.vue'
import { checkHealth } from '../utils/api.js'

const props = defineProps({
  currentAgent: { type: String, default: 'general' },
  tenantId: { type: String, default: 'huabei' },
  userId: { type: String, default: 'demo_user' },
  streamMode: { type: Boolean, default: true }
})

const emit = defineEmits(['stream-mode-toggle', 'send-message'])

const isOnline = ref(true)
const messages = ref([])
const isTyping = ref(false)

const agentConfig = computed(() => AGENTS[props.currentAgent])

onMounted(async () => {
  const health = await checkHealth()
  isOnline.value = health !== null
})

function handleQuickAction(action) {
  emit('send-message', action)
}

function handleSend(data) {
  emit('send-message', data)
}
</script>

<style scoped>
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header h2 {
  font-size: 18px;
  font-weight: 600;
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

## Task 8: InputArea Component

**Files:**
- Create: `/frontend/src/components/InputArea.vue`

- [ ] **Step 1: Create InputArea.vue component**

```vue
<template>
  <div class="input-area">
    <div v-if="attachedFile" class="file-preview">
      <span class="name">📎 {{ attachedFile.name }}</span>
      <span class="remove" @click="removeFile">✕</span>
    </div>
    <div class="input-wrapper">
      <div class="input-box">
        <textarea
          ref="textareaRef"
          :value="inputText"
          :placeholder="placeholder"
          :disabled="disabled"
          @input="inputText = $event.target.value"
          @keydown="handleKeydown"
          class="message-input"
        ></textarea>
        <button class="attach-btn" @click="triggerFileInput" title="上传文件">📎</button>
        <input
          ref="fileInputRef"
          type="file"
          style="display: none"
          @change="handleFileSelect"
        >
      </div>
      <button class="send-btn" @click="send" :disabled="disabled || !inputText.trim()">
    ➤
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'

const props = defineProps({
  placeholder: { type: String, default: '输入消息...' },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['send'])

const inputText = ref('')
const attachedFile = ref(null)
const textareaRef = ref(null)
const fileInputRef = ref(null)

onMounted(() => {
  textareaRef.value?.focus()
})

function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

function send() {
  if (!inputText.value.trim() && !attachedFile.value) return

  emit('send', {
    message: inputText.value,
    file: attachedFile.value
  })

  inputText.value = ''
  attachedFile.value = null
  nextTick(() => textareaRef.value?.focus())
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    attachedFile.value = file
  }
}

function removeFile() {
  attachedFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}
</script>

<style scoped>
.input-area {
  padding: 20px;
  background: white;
  border-top: 1px solid #e5e7eb;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-box {
  flex: 1;
  position: relative;
}

.message-input {
  width: 100%;
  min-height: 50px;
  max-height: 150px;
  padding: 12px 50px 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  resize: none;
  font-size: 14px;
  font-family: inherit;
}

.message-input:focus {
  outline: none;
  border-color: #667eea;
}

.attach-btn {
  position: absolute;
  right: 12px;
  bottom: 12px;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 18px;
  color: #9ca3af;
  transition: color 0.3s;
}

.attach-btn:hover {
  color: #667eea;
}

.send-btn {
  width: 50px;
  height: 50px;
  border: none;
  border-radius: 12px;
  background: #667eea;
  color: white;
  font-size: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.send-btn:hover:not(:disabled) {
  background: #5568d3;
  transform: scale(1.05);
}

.send-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  transform: none;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}

.file-preview .name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-preview .remove {
  cursor: pointer;
  color: #ef4444;
}
</style>
```

---

## Task 9: MessageList Component

**Files:**
- Create: `/frontend/src/components/MessageList.vue`

- [ ] **Step 1: Create MessageList.vue component**

```vue
<template>
  <div class="messages" ref="messagesRef">
    <WelcomeScreen v-if="messages.length === 0" @quick-action="$emit('quick-action', $event)" />

    <TransitionGroup name="message">
      <MessageItem
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />
    </TransitionGroup>

    <div v-if="isTyping" class="message assistant">
      <div class="message-content">
        <div class="typing">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import WelcomeScreen from './WelcomeScreen.vue'
import MessageItem from './MessageItem.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isTyping: { type: Boolean, default: false }
})

defineEmits(['quick-action'])

const messagesRef = ref(null)

watch(() => [...props.messages, props.isTyping], () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}, { deep: true })
</script>

<style scoped>
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f9fafb;
}

.messages::-webkit-scrollbar {
  width: 6px;
}

.messages::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.messages::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.message-enter-active {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.typing {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
}

.typing-dot {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-10px); }
}
</style>
```

---

## Task 10: MessageItem Component

**Files:**
- Create: `/frontend/src/components/MessageItem.vue`

- [ ] **Step 1: Create MessageItem.vue component**

```vue
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
```

---

## Task 11: WelcomeScreen Component

**Files:**
- Create: `/frontend/src/components/WelcomeScreen.vue`

- [ ] **Step 1: Create WelcomeScreen.vue component**

```vue
<template>
  <div class="welcome">
    <h2>欢迎使用 I3D Agent System</h2>
    <p>智能多代理助手，支持 3D 模型搜索、技术文档查询、任务处理等功能</p>
    <div class="quick-actions">
      <div class="quick-action" @click="$emit('quick-action', '帮我搜索一个螺栓零件，材质为不锈钢')">
        <div class="icon">🔍</div>
        <div class="label">搜索相似零件</div>
      </div>
      <div class="quick-action" @click="$emit('quick-action', '如何部署 3D 搜索服务？')">
        <div class="icon">📚</div>
        <div class="label">查询技术文档</div>
      </div>
      <div class="quick-action" @click="$emit('quick-action', '查询最近的文件处理任务状态')">
        <div class="icon">⚙️</div>
        <div class="label">查看任务状态</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['quick-action'])
</script>

<style scoped>
.welcome {
  text-align: center;
  padding: 40px;
}

.welcome h2 {
  font-size: 24px;
  color: #1f2937;
  margin-bottom: 10px;
}

.welcome p {
  color: #6b7280;
  margin-bottom: 30px;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  max-width: 600px;
  margin: 0 auto;
}

.quick-action {
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
}

.quick-action:hover {
  border-color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.quick-action .icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.quick-action .label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}
</style>
```

---

## Task 12: ThoughtProcess Component

**Files:**
- Create: `/frontend/src/components/ThoughtProcess.vue`

- [ ] **Step 1: Create ThoughtProcess.vue component**

```vue
<template>
  <details class="thought-process" open>
    <summary>🧠 思考过程</summary>
    <div class="thought-steps">
      <div v-for="(step, index) in steps" :key="index" class="thought-step">
        • {{ step }}
      </div>
    </div>
  </details>
</template>

<script setup>
defineProps({
  steps: { type: Array, default: () => [] }
})
</script>

<style scoped>
.thought-process {
  margin-top: 10px;
  padding: 10px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  font-size: 12px;
}

.thought-process summary {
  cursor: pointer;
  font-weight: 600;
  color: #166534;
}

.thought-steps {
  margin-top: 8px;
  padding-left: 15px;
}

.thought-step {
  margin: 4px 0;
  color: #15803d;
}
</style>
```

---

## Task 13: SourcesList Component

**Files:**
- Create: `/frontend/src/components/SourcesList.vue`

- [ ] **Step 1: Create SourcesList.vue component**

```vue
<template>
  <details class="sources">
    <summary>📚 参考 {{ sources.length }} 条来源</summary>
    <div class="sources-list">
      <div v-for="(source, index) in sources" :key="index" class="source-item">
        <div class="title">
          {{ source.title || source.source || '未知来源' }}
          <span class="score">★ {{ ((source.score || 0) * 100).toFixed(1) }}%</span>
        </div>
        <div v-if="source.chunk_index !== undefined" class="chunk">
          Chunk #{{ source.chunk_index }}
        </div>
      </div>
    </div>
  </details>
</template>

<script setup>
defineProps({
  sources: { type: Array, default: () => [] }
})
</script>

<style scoped>
.sources {
  margin-top: 10px;
}

.sources summary {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
}

.sources-list {
  margin-top: 8px;
}

.source-item {
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 6px;
  margin-bottom: 6px;
  font-size: 12px;
}

.source-item .title {
  font-weight: 600;
  color: #374151;
}

.source-item .score {
  float: right;
  color: #10b981;
}

.source-item .chunk {
  color: #6b7280;
  font-size: 11px;
  margin-top: 4px;
  clear: both;
}
</style>
```

---

## Task 14: Main CSS Styles

**Files:**
- Create: `/frontend/src/styles/main.css`

- [ ] **Step 1: Create main.css with global styles**

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

#app {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* Reset buttons */
button {
  font-family: inherit;
}

/* Focus styles for accessibility */
input:focus,
textarea:focus,
select:focus,
button:focus {
  outline: 2px solid #667eea;
  outline-offset: 1px;
}
```

---

## Task 15: Connect App Components

**Files:**
- Modify: `/frontend/src/App.vue`
- Modify: `/frontend/src/components/ChatArea.vue`

- [ ] **Step 1: Update App.vue to wire up chat functionality**

```vue
<template>
  <div class="container">
    <Sidebar
      :current-agent="currentAgent"
      :tenant-id="tenantId"
      :user-id="userId"
      @agent-selected="handleAgentSelected"
      @tenant-changed="handleTenantChanged"
      @user-changed="handleUserChanged"
    />
    <ChatArea
      ref="chatAreaRef"
      :current-agent="currentAgent"
      :tenant-id="tenantId"
      :user-id="userId"
      :stream-mode="streamMode"
      @stream-mode-toggle="streamMode = !streamMode"
      @send-message="handleSendMessage"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatArea from './components/ChatArea.vue'
import { useChat } from './composables/useChat.js'

const currentAgent = ref('general')
const tenantId = ref('huabei')
const userId = ref('demo_user')
const streamMode = ref(true)
const chatAreaRef = ref(null)

const { messages, isTyping, sendMessage } = useChat()

function handleAgentSelected(agent) {
  currentAgent.value = agent
}

function handleTenantChanged(tenant) {
  tenantId.value = tenant
}

function handleUserChanged(user) {
  userId.value = user
}

async function handleSendMessage(data) {
  if (typeof data === 'string') {
    await sendMessage(data, userId.value, tenantId.value, streamMode.value)
  } else {
    await sendMessage(data.message, userId.value, tenantId.value, streamMode.value)
  }
}

// Expose messages to ChatArea
defineExpose({ messages, isTyping })
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

- [ ] **Step 2: Update ChatArea.vue to receive messages from parent**

Add to `<script setup>` in ChatArea.vue:
```js
const props = defineProps({
  currentAgent: { type: String, default: 'general' },
  tenantId: { type: String, default: 'huabei' },
  userId: { type: String, default: 'demo_user' },
  streamMode: { type: Boolean, default: true },
  // Add these new props
  messages: { type: Array, default: () => [] },
  isTyping: { type: Boolean, default: false }
})
```

Remove the local `messages` and `isTyping` refs, replace with props:
```js
// Remove these lines:
// const messages = ref([])
// const isTyping = ref(false)

// Update MessageList binding to use props:
<MessageList
  :messages="messages"
  :is-typing="isTyping"
  @quick-action="handleQuickAction"
/>
```

---

## Task 16: Build and Test

**Files:**
- Run: Build command
- Run: Dev server

- [ ] **Step 1: Start development server**

Run:
```bash
cd /frontend
npm run dev
```

Expected output:
```
VITE v5.x.x ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

- [ ] **Step 2: Verify application loads**

Open browser to `http://localhost:5173`

Expected:
- Sidebar with 9 agent buttons visible
- Chat area with welcome screen
- 3 quick action cards clickable
- Tenant dropdown shows 4 options
- User ID input shows "demo_user"

- [ ] **Step 3: Test chat functionality**

1. Click a quick action or type a message
2. Press Enter or click send
3. Verify user message appears
4. Verify typing indicator shows
5. Verify assistant response appears

- [ ] **Step 4: Test agent switching**

1. Click different agent buttons
2. Verify header title changes
3. Verify input placeholder changes

- [ ] **Step 5: Test settings**

1. Change tenant selection
2. Change user ID
3. Verify values persist

- [ ] **Step 6: Build for production**

Run:
```bash
cd /frontend
npm run build
```

Expected:
```
building for production...
✓ 45 modules transformed.
dist/index.html                  0.45 kB
dist/assets/*.css                 xx kB
dist/assets/*.js                  xx kB
```

- [ ] **Step 7: Verify build output**

Run:
```bash
ls -la /frontend/dist/
```

Expected files:
- `index.html`
- `assets/` directory with CSS and JS files

---

## Task 17: Integration Verification with Backend

**Files:**
- Test: Backend integration

- [ ] **Step 1: Ensure backend is running**

Run:
```bash
cd /data/yzh/i3d-agent-system
uvicorn i3d_agent.api.main:app --reload --port 8000
```

Expected: `Application startup complete`

- [ ] **Step 2: Test health check**

In browser console, run:
```js
fetch('/health').then(r => r.json()).then(console.log)
```

Expected: JSON response with health status

- [ ] **Step 3: Test streaming chat**

1. Open the Vue app at `http://localhost:5173`
2. Type a message and send
3. Verify streaming response appears character by character
4. Verify no console errors

- [ ] **Step 4: Verify all functionality works**

Checklist:
- [ ] All 9 agents selectable
- [ ] Tenant selection works
- [ ] User ID input works
- [ ] Stream mode toggle works
- [ ] Messages display correctly
- [ ] Sources show when available
- [ ] Thought process shows when available
- [ ] Code blocks format correctly
- [ ] Welcome screen disappears after first message
- [ ] Typing indicator shows
- [ ] Status shows online/offline correctly

---

## Success Criteria

Upon completion, the following must be true:

1. ✅ Vue 3 application runs at `/frontend` with `npm run dev`
2. ✅ All 17 original features preserved and functional
3. ✅ Production build succeeds with `npm run build`
4. ✅ SSE streaming chat works with backend
5. ✅ No console errors during normal operation
6. ✅ Responsive layout matches original design
7. ✅ All agent types selectable and functional
8. ✅ Tenant and user settings respected

---

**End of Implementation Plan**

---

## 2026-06-09 Revision: ChatGPT-Style Chat + RAG Management Menu

**Status:** This revision supersedes any earlier plan steps that require visible agent selection, agent switching tests, or a permanent tenant/user settings section in the sidebar.

**Updated Goal:** Redesign the existing Vue frontend into a cleaner ChatGPT-style workspace while adding RAG management as a first-level menu item.

**Product decisions:**

- Keep the left conversation sidebar for chat: new chat, history, rename, delete, and pin remain available.
- Remove the visible Agent selector from the chat UI.
- Do not expose agent selection to users. Routing is handled by the backend supervisor.
- Add a first-level left navigation with `聊天` and `RAG 管理`.
- Keep `tenantId` and `userId`, but move both into a settings modal.
- Share the same `tenantId` between chat and RAG management.
- Keep streaming mode, but move it into the settings modal unless a compact header toggle is still needed for debugging.

### Revised File Structure

```
/frontend/src/
├── App.vue
├── components/
│   ├── AppSidebar.vue                 # First-level nav + contextual sidebar content
│   ├── SettingsModal.vue              # Tenant/user/stream settings
│   ├── ChatArea.vue                   # Simplified chat shell
│   ├── MessageList.vue
│   ├── MessageItem.vue
│   ├── InputArea.vue
│   ├── SessionItem.vue
│   ├── SourcesList.vue
│   ├── ThoughtProcess.vue
│   └── rag/
│       ├── RagConsole.vue
│       ├── RagDashboard.vue
│       ├── RagIngestion.vue
│       ├── SingleUploadPanel.vue
│       ├── BatchImportPanel.vue
│       ├── RagDocumentsTable.vue
│       ├── RagDocumentDetail.vue
│       ├── RagRetrievalLab.vue
│       ├── RagIndexMonitor.vue
│       ├── RagQualityPanel.vue
│       └── RagConfigPanel.vue
├── composables/
│   ├── useChat.js
│   ├── useSessions.js
│   └── usePreferences.js
└── utils/
    ├── api.js
    └── ragApi.js
```

`AgentSelector.vue` and `useAgents.js` should be removed from the active UI path. They may be deleted after confirming no imports remain.

### Task R1: Root Layout And Navigation

**Files:**
- Modify: `/frontend/src/App.vue`
- Create: `/frontend/src/components/AppSidebar.vue`
- Create: `/frontend/src/components/SettingsModal.vue`

- [ ] Add `activeView` state with values `chat` and `rag`.
- [ ] Replace the current single `.container` card layout with a full-height app shell.
- [ ] Add first-level navigation in the left sidebar: `聊天`, `RAG 管理`.
- [ ] When `activeView === "chat"`, show session controls and session list in the left sidebar.
- [ ] When `activeView === "rag"`, hide the session list and show a compact RAG section label or RAG secondary nav.
- [ ] Move tenant/user/stream settings out of `SessionSidebar.vue` into `SettingsModal.vue`.
- [ ] Keep `tenantId`, `userId`, and `streamMode` in `App.vue` so both views share the same state.

### Task R2: Simplify Chat UI

**Files:**
- Modify: `/frontend/src/components/ChatArea.vue`
- Modify: `/frontend/src/composables/useChat.js`
- Modify: `/frontend/src/utils/api.js`
- Remove or orphan after verification: `/frontend/src/components/AgentSelector.vue`
- Remove or orphan after verification: `/frontend/src/composables/useAgents.js`

- [ ] Remove `AgentSelector` import and component usage from `ChatArea.vue`.
- [ ] Remove `currentAgent` prop and `agentChanged` emit from `ChatArea.vue`.
- [ ] Use a fixed input placeholder: `输入消息...`.
- [ ] Keep the current session title in the header.
- [ ] Keep online/offline status.
- [ ] Remove visible agent badge/title/prompt behavior from the chat page.
- [ ] Ensure chat send payload no longer depends on user-selected agent.
- [ ] If backend still requires an agent field temporarily, set it in the API compatibility layer without exposing it in UI.
- [ ] Preserve streaming and non-streaming message behavior.

### Task R3: Sidebar Session Behavior

**Files:**
- Modify or replace: `/frontend/src/components/SessionSidebar.vue`
- Modify: `/frontend/src/components/SessionItem.vue`

- [ ] Preserve new chat.
- [ ] Preserve session history list.
- [ ] Preserve switch session.
- [ ] Preserve rename session.
- [ ] Preserve delete session.
- [ ] Preserve pin/unpin if already working.
- [ ] Remove inline tenant and user settings from the sidebar.
- [ ] Add a settings button that opens `SettingsModal.vue`.

### Task R4: RAG Management View Entry

**Files:**
- Create: `/frontend/src/components/rag/RagConsole.vue`
- Create: `/frontend/src/utils/ragApi.js`
- Modify: `/frontend/src/App.vue`

- [ ] Render `RagConsole` when `activeView === "rag"`.
- [ ] Pass shared `tenantId` into `RagConsole`.
- [ ] Create `ragApi.js` wrappers for existing RAG endpoints.
- [ ] Add tabs inside `RagConsole`: 总览, 文档接入, 文档管理, 检索调试, 索引监控, 质量反馈, 配置.
- [ ] Keep RAG management visually distinct from chat: dense tables, compact forms, full-height workspace.

### Task R5: RAG Ingestion

**Files:**
- Create: `/frontend/src/components/rag/RagIngestion.vue`
- Create: `/frontend/src/components/rag/SingleUploadPanel.vue`
- Create: `/frontend/src/components/rag/BatchImportPanel.vue`

- [ ] Implement single-file upload via `POST /api/v1/rag/documents/upload`.
- [ ] Implement server-directory dry-run via `POST /api/v1/rag/documents/batch-import` with `dry_run=true`.
- [ ] Implement confirmed batch import with `dry_run=false`.
- [ ] Display per-file result status: imported, skipped, failed, would_import.
- [ ] Display file MD5, source path, storage path, doc_id, and failure reason.
- [ ] Use shared `tenantId` by default and do not duplicate tenant selectors inside every form unless needed.

### Task R6: RAG Monitoring And Debugging

**Files:**
- Create: `/frontend/src/components/rag/RagDashboard.vue`
- Create: `/frontend/src/components/rag/RagIndexMonitor.vue`
- Create: `/frontend/src/components/rag/RagRetrievalLab.vue`
- Create: `/frontend/src/components/rag/RagQualityPanel.vue`

- [ ] Implement index status cards from `GET /api/v1/rag/index/status`.
- [ ] Implement index queue table from `GET /api/v1/rag/index/queue`.
- [ ] Add manual refresh and optional 5s polling while the monitor tab is active.
- [ ] Implement retrieval testing via `POST /api/v1/rag/search`.
- [ ] Implement ask testing via `POST /api/v1/rag/ask`.
- [ ] Display source metadata and chunk scores clearly.
- [ ] Implement quality metrics via `GET /api/v1/rag/quality`.

### Task R7: Backend Compatibility Checklist

These backend issues must be fixed before the RAG management frontend can be considered complete:

- [ ] `GET /api/v1/rag/documents` must map `page/page_size` to `limit/offset` or update `DocumentManager.list_documents`.
- [ ] `POST /api/v1/rag/feedback` must accept/use `tenant_id` instead of hardcoding `default`.
- [ ] Add `GET /api/v1/rag/config` for current RAG settings.
- [ ] Add `GET /api/v1/rag/documents/{doc_id}/chunks` for document detail inspection.
- [ ] Add `POST /api/v1/rag/documents/{doc_id}/reindex` or equivalent queue task creation.

### Revised Verification

- [ ] `npm run build` succeeds.
- [ ] Chat page has no visible agent selector.
- [ ] Chat page still supports new chat, session history, rename, delete, and send message.
- [ ] Chat payload does not depend on user-selected agent.
- [ ] Settings modal updates tenant, user ID, and stream mode.
- [ ] Switching to `RAG 管理` does not lose chat session state.
- [ ] RAG management uses the same tenant shown in settings.
- [ ] Single-file upload works for supported text files.
- [ ] Batch import dry-run and confirmed import both render per-file results.
- [ ] Index status and queue render and refresh.
- [ ] Retrieval test and ask test render sources.

### Revised Success Criteria

Upon completion, the following must be true:

1. Vue app uses a full-height workspace shell with first-level `聊天 / RAG 管理` navigation.
2. Chat UI is simplified and ChatGPT-like: no visible agent selector, no agent prompt selector, no decorative agent controls.
3. Backend supervisor owns routing; the frontend does not expose agent selection.
4. Tenant and user settings are centralized in a settings modal.
5. RAG management is reachable as a new menu and supports upload, batch import, index monitoring, and retrieval debugging.
6. Production build succeeds without console errors in normal use.

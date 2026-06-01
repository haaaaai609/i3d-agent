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

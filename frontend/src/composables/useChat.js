import { ref, watch } from 'vue'
import { sendChatMessage, streamChatMessage } from '../utils/api.js'
import { storage, MAX_CACHED_MESSAGES } from '../utils/storage.js'

export function useChat(sessionId) {
  const messages = ref([])
  const isTyping = ref(false)
  const attachedFile = ref(null)

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
    const userContent = message + (attachedFile.value ? ` [文件: ${attachedFile.value.name}]` : '')
    addMessage('user', userContent)

    isTyping.value = true

    try {
      const payload = {
        message: message || `处理上传的文件: ${attachedFile.value?.name || ''}`,
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
    attachedFile,
    addMessage,
    sendMessage,
    loadCachedMessages,
    setFile,
    clearFile
  }
}

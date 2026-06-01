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

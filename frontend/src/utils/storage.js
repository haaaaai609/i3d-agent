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

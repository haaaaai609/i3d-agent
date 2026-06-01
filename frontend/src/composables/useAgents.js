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

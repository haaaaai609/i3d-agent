const API_BASE = window.location.origin
const RAG_BASE = `${API_BASE}/api/v1/rag`

async function request(path, options = {}) {
  const response = await fetch(`${RAG_BASE}${path}`, options)
  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const detail = typeof data === 'object' ? data.detail || JSON.stringify(data) : data
    throw new Error(detail || `HTTP ${response.status}: ${response.statusText}`)
  }

  return data
}

function query(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, value)
    }
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

export function getRagConfig() {
  return request('/config')
}

export function uploadDocument(formData) {
  return request('/documents/upload', {
    method: 'POST',
    body: formData
  })
}

export function batchImportDocuments(payload) {
  return request('/documents/batch-import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export function listDocuments(params) {
  return request(`/documents${query(params)}`)
}

export function getDocument(docId) {
  return request(`/documents/${encodeURIComponent(docId)}`)
}

export function getDocumentHistory(docId) {
  return request(`/documents/${encodeURIComponent(docId)}/history`)
}

export function getDocumentChunks(docId, params) {
  return request(`/documents/${encodeURIComponent(docId)}/chunks${query(params)}`)
}

export function deleteDocument(docId, hardDelete = false) {
  return request(`/documents/${encodeURIComponent(docId)}${query({ hard_delete: hardDelete })}`, {
    method: 'DELETE'
  })
}

export function restoreDocument(docId, version) {
  return request(`/documents/${encodeURIComponent(docId)}/restore${query({ version })}`, {
    method: 'POST'
  })
}

export function reindexDocument(docId, tenantId) {
  return request(`/documents/${encodeURIComponent(docId)}/reindex${query({ tenant_id: tenantId })}`, {
    method: 'POST'
  })
}

export function searchRag(payload) {
  return request('/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export function askRag(payload) {
  return request('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export function getIndexStatus(tenantId) {
  return request(`/index/status${query({ tenant_id: tenantId })}`)
}

export function getIndexQueue(params) {
  return request(`/index/queue${query(params)}`)
}

export function getMetrics(params) {
  return request(`/metrics${query(params)}`)
}

export function getQuality(params) {
  return request(`/quality${query(params)}`)
}

export function submitFeedback(payload) {
  return request('/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

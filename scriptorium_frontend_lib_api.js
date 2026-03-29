import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

const client = axios.create({
  baseURL: API_BASE,
  timeout: 120000,  // 2 min for LLM
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    console.error('[API Error]', msg)
    return Promise.reject(new Error(msg))
  }
)

// ── Documents ──────────────────────────────────────────────────────────────

export async function uploadDocument(file, onProgress) {
  const form = new FormData()
  form.append('file', file)

  const res = await client.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
  return res.data
}

export async function getDocumentStatus(docId) {
  const res = await client.get(`/documents/${docId}/status`)
  return res.data
}

export async function listDocuments() {
  const res = await client.get('/documents/')
  return res.data
}

export async function deleteDocument(docId) {
  const res = await client.delete(`/documents/${docId}`)
  return res.data
}

export async function getAutoInsights(docIds, focus = null) {
  const res = await client.post('/documents/insights', {
    doc_ids: docIds,
    focus,
  })
  return res.data
}

// ── Chat ──────────────────────────────────────────────────────────────────

export async function sendQuery(params) {
  const res = await client.post('/chat/query', {
    query: params.query,
    doc_ids: params.docIds,
    conversation_history: params.history || [],
    mode: params.mode || 'conversational',
    highlight_text: params.highlightText || null,
    explain_level: params.explainLevel || 'expert',
    session_id: params.sessionId,
  })
  return res.data
}

export async function compareDocuments(docIds, aspect) {
  const res = await client.post('/chat/compare', {
    doc_ids: docIds,
    aspect,
  })
  return res.data
}

// ── Health ────────────────────────────────────────────────────────────────

export async function checkHealth() {
  const res = await client.get('/health')
  return res.data
}

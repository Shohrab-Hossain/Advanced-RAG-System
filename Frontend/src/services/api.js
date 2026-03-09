/**
 * API Service
 * -----------
 * All HTTP calls to the Flask backend.
 * query() is handled differently — it returns an EventSource,
 * not a promise, because the response is an SSE stream.
 */

import axios from 'axios'

// Vue CLI exposes env vars with the VUE_APP_ prefix (set in .env)
const BASE = process.env.VUE_APP_API_URL || ''

const http = axios.create({ baseURL: BASE })

// ── REST calls ────────────────────────────────────────────────────────────────

export async function uploadFile(file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post('/api/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100))
      }
    },
  })
  return data
}

export async function getDocuments() {
  const { data } = await http.get('/api/documents')
  return data
}

export async function clearDocuments() {
  const { data } = await http.delete('/api/clear')
  return data
}

export async function healthCheck() {
  const { data } = await http.get('/api/health')
  return data
}

export async function getProviders() {
  const { data } = await http.get('/api/providers')
  return data
}

export async function getKnowledgeBases() {
  const { data } = await http.get('/api/knowledge-bases')
  return data
}

export async function deleteKnowledgeBase(fileHash) {
  const { data } = await http.delete(`/api/knowledge-bases/${fileHash}`)
  return data
}

// ── SSE streaming query ───────────────────────────────────────────────────────

/**
 * Send a query and get back an EventSource-like controller.
 * Uses fetch + ReadableStream so we can POST with a body.
 *
 * @param {string} query
 * @param {string} provider  "openai" | "ollama"
 * @param {{ onEvent: (type, data) => void, onDone: (result) => void, onError: (err) => void }} callbacks
 * @returns {{ abort: () => void }}
 */
export function streamQuery(query, provider = 'openai', { onEvent, onDone, onError }) {
  const controller = new AbortController()

  fetch(`${BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, provider }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ message: res.statusText }))
        onError(err.error || err.message || 'Request failed')
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()   // last (possibly incomplete) line stays in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const payload = JSON.parse(line.slice(6))
            const { type, data } = payload

            if (type === 'done') {
              onDone(data)
            } else if (type === 'stream_end') {
              // no-op
            } else if (type === 'error') {
              onError(data?.message || 'Unknown pipeline error')
            } else {
              onEvent(type, data)
            }
          } catch {
            // malformed line — ignore
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err.message || 'Network error')
    })

  return { abort: () => controller.abort() }
}

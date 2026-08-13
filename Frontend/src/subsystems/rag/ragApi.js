/**
 * RAG API
 * -------
 * HTTP calls for the query capability.
 * streamQuery() is handled differently — it returns a controller,
 * not a promise, because the response is an SSE stream.
 */

import axios from 'axios'

// Vue CLI exposes env vars with the VUE_APP_ prefix (set in .env)
const BASE = process.env.VUE_APP_API_URL || ''

const http = axios.create({ baseURL: BASE })

// ── REST calls ────────────────────────────────────────────────────────────────

export async function healthCheck() {
  const { data } = await http.get('/api/health')
  return data
}

export async function getProviders() {
  const { data } = await http.get('/api/providers')
  return data
}

// ── SSE streaming query ───────────────────────────────────────────────────────

/**
 * Send a query and get back an EventSource-like controller.
 * Uses fetch + ReadableStream so we can POST with a body.
 *
 * @param {string} query
 * @param {string} provider  "openai" | "ollama"
 * @param {string|null} model  Ollama model override (null → backend uses env default)
 * @param {{ onEvent: (type, data) => void, onDone: (result) => void, onError: (err) => void }} callbacks
 * @returns {{ abort: () => void }}
 */
export function streamQuery(query, provider = 'openai', model = null, { onEvent, onDone, onError }) {
  const controller = new AbortController()
  const body = { query, provider }
  if (model) body.model = model

  fetch(`${BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
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

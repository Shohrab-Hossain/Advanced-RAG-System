/**
 * Knowledge Base API
 * ------------------
 * HTTP calls for ingestion and index management — upload, index stats,
 * and the knowledge-base registry.
 */

import axios from 'axios'

// Vue CLI exposes env vars with the VUE_APP_ prefix (set in .env)
const BASE = process.env.VUE_APP_API_URL || ''

const http = axios.create({ baseURL: BASE })

// ── Upload ────────────────────────────────────────────────────────────────────

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

// ── Index ─────────────────────────────────────────────────────────────────────

export async function getDocuments() {
  const { data } = await http.get('/api/documents')
  return data
}

export async function clearDocuments() {
  const { data } = await http.delete('/api/clear')
  return data
}

// ── Knowledge bases ───────────────────────────────────────────────────────────

export async function getKnowledgeBases() {
  const { data } = await http.get('/api/knowledge-bases')
  return data
}

export async function deleteKnowledgeBase(fileHash) {
  const { data } = await http.delete(`/api/knowledge-bases/${fileHash}`)
  return data
}

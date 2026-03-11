/**
 * Pinia Store — RAG State
 * ------------------------
 * Central state for the entire UI:
 *   - Document index stats
 *   - Current query lifecycle (idle → running → done | error)
 *   - Pipeline stage statuses (drives PipelineTracker)
 *   - Final answer + sources
 */

import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { streamQuery, uploadFile, getDocuments, clearDocuments, getProviders, getKnowledgeBases, deleteKnowledgeBase } from '../services/api'

// Pipeline stage definitions (order matters — used for display)
export const STAGES = [
  { id: 'planner',        label: 'Self-RAG Planner',       icon: '🧠', desc: 'Decides if retrieval is needed' },
  { id: 'retrieval',      label: 'Hybrid Retrieval',        icon: '🔍', desc: 'Vector + BM25 + GraphRAG' },
  { id: 'external_tools', label: 'External Tools',          icon: '🌐', desc: 'Web search for live data' },
  { id: 'aggregator',     label: 'Evidence Aggregator',     icon: '📚', desc: 'Merge & deduplicate sources' },
  { id: 'reranker',       label: 'Cross-Encoder Reranker',  icon: '🎯', desc: 'Score & rank by relevance' },
  { id: 'compressor',     label: 'Context Compressor',      icon: '✂️',  desc: 'Summarize to fit LLM window' },
  { id: 'reasoning',      label: 'Reasoning Agent',         icon: '💡', desc: 'Generate cited answer' },
  { id: 'reflection',     label: 'Self-Reflection Agent',   icon: '🔮', desc: 'Verify grounding & citations' },
]

const _initialStages = () =>
  Object.fromEntries(STAGES.map((s) => [s.id, { status: 'idle', message: '', details: null }]))

export const useRagStore = defineStore('rag', () => {
  // ── LLM provider ────────────────────────────────────────────────────────────
  const llmProvider = ref('openai')  // "openai" | "ollama"
  const ollamaModel = ref('')        // user-selected Ollama model (empty until fetched)
  const openaiModel = ref('')        // user-selected OpenAI model (empty = use server default)
  const availableProviders = ref({   // populated by fetchProviders()
    openai: { available: false, model: '' },
    ollama: { available: false, model: '', models: [] },
  })

  // ── Document index ──────────────────────────────────────────────────────────
  const indexStats = ref({ vector_count: 0, bm25_count: 0, graph: {} })
  const knowledgeBases = ref([])
  const uploading = ref(false)
  const uploadProgress = ref(0)    // 0-100: file transfer
  const indexingProgress = ref(0)  // 0-100: server-side indexing phase
  const isIndexing = ref(false)
  const uploadQueueCurrent = ref(0)   // which file in a batch (1-based)
  const uploadQueueTotal = ref(0)     // total files in current batch
  // keep track of the last upload result so it can be cleared by other actions
  const uploadResult = ref(null)

  // ── Query state ─────────────────────────────────────────────────────────────
  const query = ref('')
  const isRunning = ref(false)
  const stageStatuses = reactive(_initialStages())
  const events = ref([])          // raw event log for debugging
  const retryCount = ref(0)

  // ── Result ──────────────────────────────────────────────────────────────────
  const answer = ref('')
  const sources = ref([])
  const metadata = ref({})
  const error = ref('')
  const isHistoryResult = ref(false)  // true when result was loaded from history

  // ── Chat History ─────────────────────────────────────────────────────────────
  const HISTORY_KEY = 'rag-chat-history'
  function _loadHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch { return [] }
  }
  const chatHistory = ref(_loadHistory())
  function _persistHistory() {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(chatHistory.value.slice(0, 50)))
  }

  let _abortFn = null

  // ── Computed ─────────────────────────────────────────────────────────────────
  const hasResult = computed(() => !!answer.value)
  const hasDocuments = computed(() => indexStats.value.vector_count > 0)

  // ── Actions ──────────────────────────────────────────────────────────────────

  function resetPipeline() {
    Object.keys(stageStatuses).forEach((k) => {
      stageStatuses[k] = { status: 'idle', message: '', details: null }
    })
    events.value = []
    answer.value = ''
    sources.value = []
    metadata.value = {}
    error.value = ''
    retryCount.value = 0
    isHistoryResult.value = false
  }

  function _applyEvent(type, data) {
    events.value.push({ type, data, ts: Date.now() })

    const stage = data?.stage
    if (!stage || !(stage in stageStatuses)) return

    switch (type) {
      case 'stage_start':
        stageStatuses[stage].status = 'active'
        stageStatuses[stage].message = data.message || ''
        break
      case 'stage_complete':
      case 'retrieval_result':
        stageStatuses[stage].status = 'complete'
        stageStatuses[stage].message = data.message || ''
        stageStatuses[stage].details = data
        break
      case 'stage_skip':
        stageStatuses[stage].status = 'skipped'
        stageStatuses[stage].message = data.message || 'Skipped'
        break
      case 'stage_error':
        stageStatuses[stage].status = 'error'
        stageStatuses[stage].message = data.error || 'Error'
        break
      case 'retry':
        retryCount.value = (data.attempt || 1) - 1
        // Reset retrieval stages to idle so they re-animate
        ;['retrieval', 'external_tools', 'aggregator', 'reranker', 'compressor', 'reasoning', 'reflection']
          .forEach((s) => { stageStatuses[s] = { status: 'idle', message: '', details: null } })
        break
      case 'finalize':
        stageStatuses[stage].status = 'complete'
        stageStatuses[stage].message = data.message || 'Done'
        break
    }
  }

  async function runQuery(q) {
    if (!q.trim() || isRunning.value) return
    query.value = q.trim()
    isRunning.value = true
    resetPipeline()

    const model = llmProvider.value === 'ollama' ? ollamaModel.value
                : llmProvider.value === 'openai' ? openaiModel.value
                : null
    const { abort } = streamQuery(q, llmProvider.value, model || null, {
      onEvent: (type, data) => _applyEvent(type, data),
      onDone: (result) => {
        answer.value = result.answer || ''
        sources.value = result.sources || []
        metadata.value = result.metadata || {}
        isRunning.value = false
        isHistoryResult.value = false
        _abortFn = null
        // Save to history
        if (result.answer) {
          chatHistory.value.unshift({
            id: Date.now().toString(),
            query: query.value,
            answer: result.answer,
            sources: result.sources || [],
            metadata: result.metadata || {},
            stageStatuses: JSON.parse(JSON.stringify(stageStatuses)),
            retryCount: retryCount.value,
            timestamp: Date.now(),
          })
          _persistHistory()
        }
      },
      onError: (msg) => {
        error.value = msg
        isRunning.value = false
        _abortFn = null
      },
    })
    _abortFn = abort
  }

  function abortQuery() {
    _abortFn?.()
    isRunning.value = false
    error.value = 'Query cancelled'
  }

  function loadHistoryItem(item) {
    query.value = item.query
    answer.value = item.answer
    sources.value = item.sources || []
    metadata.value = item.metadata || {}
    error.value = ''
    isHistoryResult.value = true
    isRunning.value = false
    retryCount.value = item.retryCount || 0
    Object.keys(stageStatuses).forEach((k) => {
      if (item.stageStatuses?.[k]) {
        // Restore full saved state (status + message + details/chips)
        stageStatuses[k] = item.stageStatuses[k]
      } else {
        // Old history item — no stageStatuses snapshot; mark as complete so tracker isn't blank
        stageStatuses[k] = { status: 'complete', message: 'Pipeline completed', details: null }
      }
    })
  }

  function deleteHistoryItem(id) {
    chatHistory.value = chatHistory.value.filter((h) => h.id !== id)
    _persistHistory()
  }

  function clearChatHistory() {
    chatHistory.value = []
    _persistHistory()
  }

  async function uploadDocument(file, { queueCurrent = 1, queueTotal = 1 } = {}) {
    uploading.value = true
    uploadProgress.value = 0
    isIndexing.value = false
    indexingProgress.value = 0
    uploadQueueCurrent.value = queueCurrent
    uploadQueueTotal.value = queueTotal
    uploadResult.value = null
    try {
      // Phase 1: file transfer — XHR progress callback
      const result = await uploadFile(file, (pct) => { uploadProgress.value = pct })
      // Phase 2: indexing — start immediately, no gap
      isIndexing.value = true
      uploading.value = false
      await _animateIndexing()
      isIndexing.value = false
      indexingProgress.value = 100
      await refreshStats()
      await fetchKnowledgeBases()
      uploadResult.value = result
      return result
    } catch (err) {
      uploadResult.value = { error: err.response?.data?.error || err.message }
      throw err
    } finally {
      uploading.value = false
      isIndexing.value = false
    }
  }

  function _animateIndexing() {
    return new Promise((resolve) => {
      indexingProgress.value = 0
      const step = () => {
        // Ease toward 95 quickly, hold there until resolved
        if (indexingProgress.value < 95) {
          indexingProgress.value = Math.min(95, indexingProgress.value + 5)
          setTimeout(step, 80)
        } else {
          resolve()
        }
      }
      step()
    })
  }

  async function refreshStats() {
    try {
      indexStats.value = await getDocuments()
    } catch { /* ignore */ }
  }

  async function fetchKnowledgeBases() {
    try {
      const data = await getKnowledgeBases()
      knowledgeBases.value = data.knowledge_bases || []
    } catch { /* ignore */ }
  }

  async function removeKnowledgeBase(fileHash) {
    // clear any prior upload information so user can start fresh
    resetUploadResult()
    await deleteKnowledgeBase(fileHash)
    await fetchKnowledgeBases()
    await refreshStats()
  }

  async function clearIndex() {
    await clearDocuments()
    knowledgeBases.value = []
    await refreshStats()
    resetUploadResult()
  }

  function resetUploadResult() {
    uploadResult.value = null
  }

  async function fetchProviders() {
    try {
      const data = await getProviders()
      const map = {}
      for (const p of data.providers) map[p.id] = p
      availableProviders.value = map
      // Auto-select default provider from server
      if (data.default && map[data.default]?.available) {
        llmProvider.value = data.default
      } else if (map.openai?.available) {
        llmProvider.value = 'openai'
      } else if (map.ollama?.available) {
        llmProvider.value = 'ollama'
      }
      // Pre-select the server-default OpenAI model if user hasn't chosen yet
      if (!openaiModel.value && map.openai?.model) {
        openaiModel.value = map.openai.model
      }
    } catch { /* ignore — server might not be up yet */ }
  }

  function setOllamaModel(model) {
    ollamaModel.value = model
  }

  function setOpenaiModel(model) {
    openaiModel.value = model
  }

  return {
    // provider state
    llmProvider, ollamaModel, openaiModel, availableProviders,
    // document index
    query, isRunning, stageStatuses, events, retryCount,
    answer, sources, metadata, error, isHistoryResult,
    indexStats, knowledgeBases, uploading, uploadProgress, indexingProgress, isIndexing,
    uploadQueueCurrent, uploadQueueTotal, uploadResult,
    // chat history
    chatHistory,
    // computed
    hasResult, hasDocuments,
    // actions
    runQuery, abortQuery, uploadDocument, refreshStats, clearIndex, resetPipeline,
    fetchProviders, setOllamaModel, setOpenaiModel, fetchKnowledgeBases, removeKnowledgeBase,
    resetUploadResult, loadHistoryItem, deleteHistoryItem, clearChatHistory,
  }
})

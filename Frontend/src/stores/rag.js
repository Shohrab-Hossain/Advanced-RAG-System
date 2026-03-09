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
  const llmProvider = ref('openai')          // "openai" | "ollama"
  const ollamaModel = ref('llama3.2:latest') // currently selected Ollama model
  const availableProviders = ref({           // populated by fetchProviders()
    openai: { available: false, model: 'gpt-4o-mini' },
    ollama: { available: false, model: 'llama3.2:latest', models: [] },
  })

  // ── Document index ──────────────────────────────────────────────────────────
  const indexStats = ref({ vector_count: 0, bm25_count: 0, graph: {} })
  const knowledgeBases = ref([])
  const uploading = ref(false)
  const uploadProgress = ref(0)    // 0-100: file transfer
  const indexingProgress = ref(0)  // 0-100: server-side indexing phase
  const isIndexing = ref(false)

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

    const { abort } = streamQuery(q, llmProvider.value, {
      onEvent: (type, data) => _applyEvent(type, data),
      onDone: (result) => {
        answer.value = result.answer || ''
        sources.value = result.sources || []
        metadata.value = result.metadata || {}
        isRunning.value = false
        _abortFn = null
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

  async function uploadDocument(file) {
    uploading.value = true
    uploadProgress.value = 0
    isIndexing.value = false
    indexingProgress.value = 0
    try {
      // Phase 1: file transfer — XHR progress callback
      const result = await uploadFile(file, (pct) => { uploadProgress.value = pct })
      // Phase 2: indexing — animate 0→100 over ~2s while server processes
      uploading.value = false
      isIndexing.value = true
      await _animateIndexing()
      isIndexing.value = false
      indexingProgress.value = 100
      await refreshStats()
      await fetchKnowledgeBases()
      return result
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
    await deleteKnowledgeBase(fileHash)
    await fetchKnowledgeBases()
    await refreshStats()
  }

  async function clearIndex() {
    await clearDocuments()
    knowledgeBases.value = []
    await refreshStats()
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
    } catch { /* ignore — server might not be up yet */ }
  }

  function setOllamaModel(model) {
    ollamaModel.value = model
  }

  return {
    // provider state
    llmProvider, ollamaModel, availableProviders,
    // document index
    query, isRunning, stageStatuses, events, retryCount,
    answer, sources, metadata, error,
    indexStats, knowledgeBases, uploading, uploadProgress, indexingProgress, isIndexing,
    // computed
    hasResult, hasDocuments,
    // actions
    runQuery, abortQuery, uploadDocument, refreshStats, clearIndex, resetPipeline,
    fetchProviders, setOllamaModel, fetchKnowledgeBases, removeKnowledgeBase,
  }
})

/**
 * Pinia Store — RAG State
 * ------------------------
 * State for the query capability:
 *   - LLM provider selection
 *   - Current query lifecycle (idle → running → done | error)
 *   - Pipeline stage statuses (drives PipelineTracker)
 *   - Final answer + sources, and the persisted chat history
 */

import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { streamQuery, getProviders } from '../services/ragApi'

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
    // query state
    query, isRunning, stageStatuses, events, retryCount,
    answer, sources, metadata, error, isHistoryResult,
    // chat history
    chatHistory,
    // computed
    hasResult,
    // actions
    runQuery, abortQuery, resetPipeline,
    fetchProviders, setOllamaModel, setOpenaiModel,
    loadHistoryItem, deleteHistoryItem, clearChatHistory,
  }
})

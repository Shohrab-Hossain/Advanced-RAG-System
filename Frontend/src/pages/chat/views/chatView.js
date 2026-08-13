/**
 * Chat View — pure constants
 * ---------------------------
 * Static data for ChatView.vue. Pure — no store, no refs, no lifecycle.
 */

/**
 * The condensed pipeline shown in the pre-query empty state.
 * Deliberately shorter than STAGES in subsystems/rag/ragStore.js: that one drives
 * the live tracker and must match the `data.stage` values the backend EMITS, this
 * one is a teaser. Those emitted values are not the graph node names — five of the
 * eight differ (graph.py registers aggregate/rerank/compress/reason/reflect; the
 * frames carry aggregator/reranker/compressor/reasoning/reflection), so the emit()
 * call sites are the contract, never graph.py.
 */
export const PIPELINE_STEPS = [
  { icon: '🧠', label: 'Plan' },
  { icon: '🔍', label: 'Retrieve' },
  { icon: '🎯', label: 'Rerank' },
  { icon: '✂️', label: 'Compress' },
  { icon: '💡', label: 'Generate' },
  { icon: '🔮', label: 'Reflect' },
]

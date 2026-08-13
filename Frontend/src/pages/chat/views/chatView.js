/**
 * Chat View — pure constants
 * ---------------------------
 * Static data for ChatView.vue. Pure — no store, no refs, no lifecycle.
 */

/**
 * The condensed pipeline shown in the pre-query empty state.
 * Deliberately shorter than STAGES in subsystems/rag/ragStore.js: that one drives
 * the live tracker and must match the backend node ids, this one is a teaser.
 */
export const PIPELINE_STEPS = [
  { icon: '🧠', label: 'Plan' },
  { icon: '🔍', label: 'Retrieve' },
  { icon: '🎯', label: 'Rerank' },
  { icon: '✂️', label: 'Compress' },
  { icon: '💡', label: 'Generate' },
  { icon: '🔮', label: 'Reflect' },
]

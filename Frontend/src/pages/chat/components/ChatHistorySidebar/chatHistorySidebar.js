/**
 * Chat History Sidebar — pure helpers
 * ------------------------------------
 * Pure formatting for ChatHistorySidebar.vue — no store, no refs, no lifecycle.
 */

/** Relative age of a history entry: "Just now" · "12m ago" · "3h ago" · "Mar 4". */
export function formatTime(ts) {
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return diffMins + 'm ago'
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return diffHours + 'h ago'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

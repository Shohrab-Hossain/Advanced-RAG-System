/**
 * Knowledge Base View — pure helpers
 * -----------------------------------
 * Formatting and view-model builders for KnowledgeBaseView.vue.
 * Everything here is a pure function of its arguments — no store, no refs,
 * no lifecycle. Reactivity stays in the .vue.
 */

// ── Upload ────────────────────────────────────────────────────────────────────

// Mirrors Config.ALLOWED_EXTENSIONS in Backend/src/config.py — the route
// rejects anything else, so keep the two in step.
export const ACCEPT_ATTR = [
  '.pdf', '.docx', '.txt', '.md',
  '.json', '.csv', '.html', '.htm',
  '.js', '.jsx', '.ts', '.tsx', '.css', '.scss',
  '.py', '.java', '.c', '.cpp', '.cs', '.go', '.rb', '.php', '.rs',
  '.sh', '.bat', '.pl', '.swift', '.kt', '.scala', '.r', '.m', '.vb',
  '.lua', '.dart', '.sql',
].join(',')

// ── Formatting ────────────────────────────────────────────────────────────────

export function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function kbStats(kb) {
  return [
    { val: kb.vectors,  label: 'Vectors' },
    { val: kb.entities, label: 'Entities' },
    { val: kb.chunks,   label: 'Chunks' },
  ]
}

/** One presentational row per knowledge base — the list renders this, not the raw record. */
export function buildKbCards(knowledgeBases) {
  return knowledgeBases.map((kb) => ({
    id: kb.id,
    name: kb.name,
    uploadedLabel: formatDate(kb.uploaded_at),
    stats: kbStats(kb),
  }))
}

// ── Index stat cards ──────────────────────────────────────────────────────────

/** The three index-overview cards, built from a raw /api/documents payload. */
export function buildIndexStats(stats) {
  return [
    {
      icon: '🗃️', label: 'Vector Store', desc: 'ChromaDB dense embeddings', unit: 'vectors', badge: 'Vector',
      value: stats.vector_count ?? 0,
      iconBg: 'bg-emerald-100 dark:bg-emerald-500/15',
      cardBg: 'bg-emerald-50/60 dark:bg-emerald-500/[0.05] border-emerald-100 dark:border-emerald-500/15',
      pillBg: 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400',
      labelColor: 'text-emerald-800 dark:text-emerald-300',
      valueColor: 'text-emerald-600 dark:text-emerald-400',
      dividerColor: 'border-emerald-100 dark:border-emerald-500/15',
    },
    {
      icon: '📝', label: 'Keyword Store', desc: 'BM25 sparse retrieval', unit: 'docs', badge: 'BM25',
      value: stats.bm25_count ?? 0,
      iconBg: 'bg-sky-100 dark:bg-sky-500/15',
      cardBg: 'bg-sky-50/60 dark:bg-sky-500/[0.05] border-sky-100 dark:border-sky-500/15',
      pillBg: 'bg-sky-100 dark:bg-sky-500/20 text-sky-700 dark:text-sky-400',
      labelColor: 'text-sky-800 dark:text-sky-300',
      valueColor: 'text-sky-600 dark:text-sky-400',
      dividerColor: 'border-sky-100 dark:border-sky-500/15',
    },
    {
      icon: '🕸️', label: 'Graph Store', badge: 'Knowledge Graph',
      triple: [
        { val: stats.graph?.entities  ?? 0, label: 'entities'  },
        { val: stats.graph?.documents ?? 0, label: 'doc nodes' },
        { val: stats.graph?.edges     ?? 0, label: 'edges'     },
      ],
      iconBg: 'bg-teal-100 dark:bg-teal-500/15',
      cardBg: 'bg-teal-50/60 dark:bg-teal-500/[0.05] border-teal-100 dark:border-teal-500/15',
      pillBg: 'bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400',
      labelColor: 'text-teal-800 dark:text-teal-300',
      valueColor: 'text-teal-600 dark:text-teal-400',
      dividerColor: 'border-teal-100 dark:border-teal-500/15',
    },
  ]
}

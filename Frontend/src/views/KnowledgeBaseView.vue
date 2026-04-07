<template>
  <main class="max-w-6xl mx-auto px-6 sm:px-8 py-8 space-y-8">

    <!-- Page header -->
    <div class="flex items-start gap-4 pb-5 border-b border-stone-200 dark:border-white/[0.06]">
      <div class="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-500/10
                  flex items-center justify-center text-xl flex-shrink-0 mt-0.5">🗂️</div>
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-stone-900 dark:text-stone-100">Knowledge Base</h1>
        <p class="text-sm text-stone-500 dark:text-slate-400 mt-1 leading-relaxed max-w-2xl">
          Upload documents to build your knowledge base. Each file is chunked into overlapping passages,
          embedded into a vector store, indexed with BM25 for keyword search, and added to the knowledge
          graph for entity-aware retrieval.
        </p>
      </div>
    </div>

    <!-- Upload + Stats -->
    <div class="space-y-5">

      <!-- Upload panel -->
      <div class="card space-y-5">
        <div>
          <p class="section-label section-label-indigo mb-1">Upload Document</p>
          <p class="text-xs text-slate-400 dark:text-stone-500">
            PDF · DOCX · TXT · MD · JSON · CSV · HTML · Code files — up to 50 MB
          </p>
        </div>

        <!-- Drop zone -->
        <div
          class="relative border-2 border-dashed rounded-xl p-10 text-center
                 transition-all duration-150 cursor-pointer"
          :class="[
            isDragging
              ? 'border-emerald-400 dark:border-emerald-500 bg-emerald-50 dark:bg-emerald-500/[0.07]'
              : 'border-stone-200 dark:border-white/[0.08] hover:border-emerald-300 dark:hover:border-emerald-500/30 hover:bg-stone-50 dark:hover:bg-white/[0.02]',
            (store.uploading || store.isIndexing) ? 'pointer-events-none opacity-50' : '',
          ]"
          @dragenter.prevent="onDragEnter"
          @dragover.prevent
          @dragleave.prevent="onDragLeave"
          @drop.prevent="onDrop"
          @click="$refs.fileInput.click()"
        >
          <input ref="fileInput" type="file" multiple class="hidden"
                 :accept="accept" @change="onFileChange" />
          <div class="text-4xl mb-3">
            {{ isDragging && dragCount > 1 ? '📚' : '📄' }}
          </div>
          <p class="text-sm font-semibold text-stone-700 dark:text-slate-300">
            {{ isDragging && dragCount > 1
                ? `Drop ${dragCount} files`
                : 'Drop files here, or click to browse' }}
          </p>
          <p class="text-xs text-slate-400 dark:text-stone-500 mt-1.5">
            PDF · DOCX · TXT · MD · JSON · CSV · HTML · Code files — multiple files supported
          </p>
        </div>

        <!-- Unified progress: upload → processing → indexing (no gap) -->
        <div v-if="store.uploading || store.isIndexing" class="space-y-2">
          <div class="flex items-center justify-between text-xs text-stone-500 dark:text-slate-400">
            <span class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
              {{ progressLabel }}
              <span v-if="store.uploadQueueTotal > 1"
                class="ml-0.5 text-[10px] px-1.5 py-0.5 rounded font-mono
                       bg-stone-100 dark:bg-white/[0.06] text-slate-400 dark:text-stone-500">
                {{ store.uploadQueueCurrent }}/{{ store.uploadQueueTotal }}
              </span>
            </span>
            <span v-if="progressPct !== null" class="font-mono tabular-nums">{{ progressPct }}%</span>
          </div>
          <div class="h-1.5 bg-stone-100 dark:bg-white/[0.06] rounded-full overflow-hidden">
            <!-- Determinate bar (uploading / indexing) -->
            <div v-if="progressPct !== null"
              class="h-full bg-emerald-500 rounded-full transition-all duration-200"
              :style="{ width: progressPct + '%' }" />
            <!-- Indeterminate shimmer while server processes the file -->
            <div v-else class="h-full rounded-full bg-gradient-to-r from-emerald-500/30 via-emerald-500 to-emerald-500/30
                               animate-shimmer bg-[length:200%_100%]" />
          </div>
        </div>

        <!-- Status message -->
        <div v-if="store.uploadResult"
          class="text-xs rounded-xl px-4 py-3 flex items-start justify-between gap-2"
          :class="store.uploadResult.error
            ? 'bg-red-50 dark:bg-red-500/[0.07] text-red-700 dark:text-red-400 border border-red-200 dark:border-red-500/20'
            : 'bg-emerald-50 dark:bg-emerald-500/[0.07] text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20'"
        >
          <span v-if="store.uploadResult.error">✗ {{ store.uploadResult.error }}</span>
          <span v-else>
            ✓ Indexed <strong>{{ store.uploadResult.file_name }}</strong>
            — {{ store.uploadResult.chunks_indexed }} chunks added
          </span>
          <button @click="store.resetUploadResult()"
            class="shrink-0 opacity-50 hover:opacity-100 text-base leading-none transition-opacity">×</button>
        </div>
      </div>

      <!-- Index stats header -->
      <div class="flex items-center gap-3 pt-1">
        <p class="section-label section-label-muted whitespace-nowrap">Index Overview</p>
        <div class="h-px flex-1 bg-stone-200 dark:bg-white/[0.06]" />
      </div>

      <!-- Index stats — 3 horizontal cards (graph card slightly wider) -->
      <div class="grid grid-cols-1 sm:grid-cols-[1fr_1fr_1.4fr] gap-3">
        <div v-for="stat in indexStats" :key="stat.label"
          class="rounded-2xl border p-4 flex flex-col gap-3"
          :class="stat.cardBg">

          <!-- Icon + type badge -->
          <div class="flex items-start justify-between">
            <div class="w-9 h-9 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
              :class="stat.iconBg">{{ stat.icon }}</div>
            <span class="text-[9px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide"
              :class="stat.pillBg">{{ stat.badge }}</span>
          </div>

          <!-- Number section: single big number OR 3-column (graph card) -->
          <div v-if="!stat.triple">
            <p class="text-3xl font-extrabold tabular-nums leading-none" :class="stat.valueColor">{{ stat.value }}</p>
            <p class="text-[9px] font-medium uppercase tracking-widest mt-1 text-slate-400 dark:text-stone-500">{{ stat.unit }}</p>
          </div>
          <div v-else class="grid grid-cols-3">
            <div v-for="(m, i) in stat.triple" :key="m.label"
              :class="i === 0 ? 'text-left' : i === 1 ? 'text-center' : 'text-right'">
              <p class="text-3xl font-extrabold tabular-nums leading-none" :class="stat.valueColor">{{ m.val }}</p>
              <p class="text-[9px] font-medium uppercase tracking-widest mt-1 text-slate-400 dark:text-stone-500">{{ m.label }}</p>
            </div>
          </div>

          <!-- Footer: label + desc (no footer for graph card) -->
          <div class="border-t pt-2.5" :class="stat.dividerColor">
            <p class="text-[11px] font-semibold" :class="stat.labelColor">{{ stat.label }}</p>
            <p v-if="!stat.triple" class="text-[9px] text-slate-400 dark:text-stone-500 mt-0.5 leading-tight">{{ stat.desc }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Uploaded knowledge bases -->
    <div v-if="store.knowledgeBases.length" class="space-y-4 pt-2 border-t border-stone-200 dark:border-white/[0.06]">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-base font-semibold text-stone-900 dark:text-stone-100">
            Uploaded Files
            <span class="ml-2 text-sm font-normal text-slate-400 dark:text-stone-500">
              {{ store.knowledgeBases.length }} {{ store.knowledgeBases.length === 1 ? 'file' : 'files' }}
            </span>
          </h2>
          <p class="text-xs text-slate-400 dark:text-stone-500 mt-0.5">
            Each file is independently retrievable and can be removed without affecting others.
          </p>
        </div>
        <button @click="clearAll"
          class="text-xs font-medium text-slate-400 hover:text-red-500 dark:text-stone-500 dark:hover:text-red-400
                 transition-colors px-3 py-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-500/[0.08]">
          Clear all
        </button>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="kb in store.knowledgeBases" :key="kb.id"
          class="card group cursor-pointer
                 transition-all duration-200
                 hover:shadow-[0_4px_20px_rgba(16,185,129,0.12),0_2px_8px_rgba(0,0,0,0.08)]
                 dark:hover:shadow-[0_4px_24px_rgba(52,211,153,0.10),0_2px_8px_rgba(0,0,0,0.3)]
                 hover:border-emerald-200 dark:hover:border-emerald-500/25">

          <!-- Header -->
          <div class="flex items-start justify-between gap-2 mb-4">
            <div class="flex items-center gap-3 min-w-0">
              <FileTypeIcon :filename="kb.name" :size="28" />
              <div class="min-w-0">
                <p class="text-sm font-semibold text-stone-800 dark:text-stone-200 truncate" :title="kb.name">
                  {{ kb.name }}
                </p>
                <p class="text-[10px] text-slate-400 dark:text-stone-500 mt-0.5">
                  {{ formatDate(kb.uploaded_at) }}
                </p>
              </div>
            </div>
            <button @click="remove(kb.id)" title="Delete file"
              class="opacity-20 group-hover:opacity-100 text-slate-400 dark:text-stone-600
                     hover:text-red-500 dark:hover:text-red-400
                     cursor-pointer transition-all text-sm flex-shrink-0 mt-0.5
                     hover:scale-110 active:scale-95">✕</button>
          </div>

          <!-- Stats row -->
          <div class="grid grid-cols-3 gap-2 text-center">
            <div v-for="s in kbStats(kb)" :key="s.label"
              class="bg-stone-50 dark:bg-white/[0.03] rounded-lg py-2 px-1
                     border border-stone-100 dark:border-white/[0.05]">
              <div class="text-sm font-bold tabular-nums text-stone-700 dark:text-slate-300">{{ s.val }}</div>
              <div class="text-[9px] uppercase tracking-wide text-slate-400 dark:text-stone-500 mt-0.5">{{ s.label }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else
      class="flex flex-col items-center justify-center py-20 text-center">
      <div class="w-16 h-16 rounded-2xl
                  bg-gradient-to-br from-emerald-500/10 to-sky-500/10
                  border border-emerald-100 dark:border-emerald-500/15
                  flex items-center justify-center text-3xl mb-4">🗂️</div>
      <p class="text-stone-700 dark:text-slate-300 font-semibold text-sm">No documents yet</p>
      <p class="text-slate-400 dark:text-stone-500 text-xs mt-1.5 max-w-xs leading-relaxed">
        Upload a PDF, DOCX, TXT, Markdown, JSON, CSV, HTML, or code file above to begin building your knowledge base.
      </p>
    </div>

  </main>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRagStore } from '../stores/rag'
import { useUiStore } from '../stores/ui'
import FileTypeIcon from '../components/FileTypeIcon.vue'

const store = useRagStore()
const ui = useUiStore()
const isDragging = ref(false)
const dragCount = ref(0)

const accept = [
  '.pdf', '.docx', '.txt', '.md',
  '.json', '.csv', '.html', '.htm',
  '.js', '.jsx', '.ts', '.tsx', '.css', '.scss',
  '.py', '.java', '.c', '.cpp', '.cs', '.go', '.rb', '.php', '.rs',
  '.sh', '.bat', '.pl', '.swift', '.kt', '.scala', '.r', '.m', '.vb',
  '.lua', '.dart', '.sql',
].join(',')

onMounted(async () => {
  await Promise.all([store.refreshStats(), store.fetchKnowledgeBases()])
})

// ── Drag handlers ────────────────────────────────────────────────────────────

function onDragEnter(e) {
  isDragging.value = true
  dragCount.value = e.dataTransfer?.items?.length ?? 1
}
function onDragLeave() {
  isDragging.value = false
  dragCount.value = 0
}

// ── Progress label / pct ─────────────────────────────────────────────────────

const progressLabel = computed(() => {
  if (store.isIndexing) return 'Indexing chunks…'
  if (store.uploading && store.uploadProgress >= 100) return 'Processing on server…'
  return 'Uploading file…'
})

const progressPct = computed(() => {
  if (store.isIndexing) return store.indexingProgress
  if (store.uploading && store.uploadProgress < 100) return store.uploadProgress
  return null   // indeterminate shimmer during server-processing phase
})

// ── Upload helpers ────────────────────────────────────────────────────────────

async function handleFiles(files) {
  if (!files.length) return
  const total = files.length
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const duplicate = store.knowledgeBases.find(
      kb => kb.name.toLowerCase() === file.name.toLowerCase()
    )
    if (duplicate) {
      const ok = await ui.confirm(
        `"${file.name}" is already in the knowledge base. Re-upload to re-index it?`,
        { confirmText: 'Yes, re-index it', cancelText: 'No, keep existing' }
      )
      if (!ok) continue
      await store.removeKnowledgeBase(duplicate.id)
    }
    store.resetUploadResult()
    try {
      await store.uploadDocument(file, { queueCurrent: i + 1, queueTotal: total })
    } catch {}
  }
  setTimeout(() => store.resetUploadResult(), 6000)
}

function onFileChange(e) {
  const files = Array.from(e.target.files)
  e.target.value = ''   // reset so re-selecting same files triggers change
  handleFiles(files)
}

function onDrop(e) {
  isDragging.value = false
  dragCount.value = 0
  handleFiles(Array.from(e.dataTransfer.files))
}

// ── KB management ─────────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function kbStats(kb) {
  return [
    { val: kb.vectors,  label: 'Vectors' },
    { val: kb.entities, label: 'Entities' },
    { val: kb.chunks,   label: 'Chunks' },
  ]
}

const indexStats = computed(() => [
  {
    icon: '🗃️', label: 'Vector Store', desc: 'ChromaDB dense embeddings', unit: 'vectors', badge: 'Vector',
    value: store.indexStats.vector_count ?? 0,
    iconBg: 'bg-emerald-100 dark:bg-emerald-500/15',
    cardBg: 'bg-emerald-50/60 dark:bg-emerald-500/[0.05] border-emerald-100 dark:border-emerald-500/15',
    pillBg: 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400',
    labelColor: 'text-emerald-800 dark:text-emerald-300',
    valueColor: 'text-emerald-600 dark:text-emerald-400',
    dividerColor: 'border-emerald-100 dark:border-emerald-500/15',
  },
  {
    icon: '📝', label: 'Keyword Store', desc: 'BM25 sparse retrieval', unit: 'docs', badge: 'BM25',
    value: store.indexStats.bm25_count ?? 0,
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
      { val: store.indexStats.graph?.entities  ?? 0, label: 'entities'  },
      { val: store.indexStats.graph?.documents ?? 0, label: 'doc nodes' },
      { val: store.indexStats.graph?.edges     ?? 0, label: 'edges'     },
    ],
    iconBg: 'bg-teal-100 dark:bg-teal-500/15',
    cardBg: 'bg-teal-50/60 dark:bg-teal-500/[0.05] border-teal-100 dark:border-teal-500/15',
    pillBg: 'bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400',
    labelColor: 'text-teal-800 dark:text-teal-300',
    valueColor: 'text-teal-600 dark:text-teal-400',
    dividerColor: 'border-teal-100 dark:border-teal-500/15',
  },
])

async function remove(id) {
  if (await ui.confirm('Delete this file from the knowledge base?', {
    danger: true, confirmText: 'Yes, delete it', cancelText: 'No, keep it',
  })) await store.removeKnowledgeBase(id)
}
async function clearAll() {
  if (await ui.confirm('Remove all knowledge bases and clear the entire index?', {
    danger: true, confirmText: 'Yes, clear all', cancelText: 'No, keep them',
  })) await store.clearIndex()
}
</script>

<template>
  <main class="max-w-6xl mx-auto px-4 py-8 space-y-8">

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

    <!-- Top row: Upload + Stats -->
    <div class="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-6 items-start">

      <!-- Upload panel -->
      <div class="card space-y-5">
        <div>
          <p class="section-label section-label-indigo mb-1">Upload Document</p>
          <p class="text-xs text-slate-400 dark:text-stone-500">
            PDF, DOCX, TXT, Markdown — up to 50 MB
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
          @dragenter.prevent="isDragging = true"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
          @click="$refs.fileInput.click()"
        >
          <input ref="fileInput" type="file" class="hidden" accept=".pdf,.txt,.md,.docx" @change="onFileChange" />
          <div class="text-4xl mb-3">📄</div>
          <p class="text-sm font-semibold text-stone-700 dark:text-slate-300">
            Drop a file here, or click to browse
          </p>
          <p class="text-xs text-slate-400 dark:text-stone-500 mt-1.5">
            PDF · DOCX · TXT · Markdown
          </p>
        </div>

        <!-- Upload progress -->
        <div v-if="store.uploading" class="space-y-2">
          <div class="flex justify-between text-xs text-stone-500 dark:text-slate-400">
            <span class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Uploading file…
            </span>
            <span class="font-mono tabular-nums">{{ store.uploadProgress }}%</span>
          </div>
          <div class="h-1.5 bg-stone-100 dark:bg-white/[0.06] rounded-full overflow-hidden">
            <div class="h-full bg-emerald-500 transition-all duration-200 rounded-full"
                 :style="{ width: store.uploadProgress + '%' }" />
          </div>
        </div>

        <!-- Indexing progress -->
        <div v-if="store.isIndexing" class="space-y-2">
          <div class="flex justify-between text-xs text-stone-500 dark:text-slate-400">
            <span class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Indexing chunks…
            </span>
            <span class="font-mono tabular-nums">{{ store.indexingProgress }}%</span>
          </div>
          <div class="h-1.5 bg-stone-100 dark:bg-white/[0.06] rounded-full overflow-hidden">
            <div class="h-full bg-emerald-500 transition-all duration-100 rounded-full"
                 :style="{ width: store.indexingProgress + '%' }" />
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

      <!-- Index stats card -->
      <div class="card space-y-4">
        <p class="section-label section-label-muted">Index Stats</p>

        <div class="space-y-3">
          <div v-for="stat in indexStats" :key="stat.label"
            class="flex items-center gap-3 p-3 rounded-xl
                   bg-stone-50 dark:bg-white/[0.03]
                   border border-stone-100 dark:border-white/[0.05]">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center text-base flex-shrink-0"
              :class="stat.iconBg">{{ stat.icon }}</div>
            <div class="min-w-0 flex-1">
              <p class="text-[11px] font-semibold text-stone-700 dark:text-slate-300">{{ stat.label }}</p>
              <p class="text-[10px] text-slate-400 dark:text-stone-500">{{ stat.desc }}</p>
            </div>
            <span class="text-sm font-bold tabular-nums text-stone-800 dark:text-stone-200 flex-shrink-0">
              {{ stat.value }}
            </span>
          </div>
        </div>

        <p class="text-[10px] text-slate-400 dark:text-stone-500 leading-relaxed pt-1
                  border-t border-stone-100 dark:border-white/[0.05]">
          All indexes are queried in parallel. The Evidence Aggregator deduplicates and merges results
          before reranking.
        </p>
      </div>
    </div>

    <!-- Uploaded knowledge bases -->
    <div v-if="store.knowledgeBases.length" class="space-y-4">
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
          class="card group hover:shadow-[0_4px_12px_0_rgb(0,0,0,0.08)] transition-shadow duration-200">

          <!-- Header -->
          <div class="flex items-start justify-between gap-2 mb-4">
            <div class="flex items-center gap-3 min-w-0">
              <span class="text-2xl flex-shrink-0 leading-none">{{ fileIcon(kb.name) }}</span>
              <div class="min-w-0">
                <p class="text-sm font-semibold text-stone-800 dark:text-stone-200 truncate" :title="kb.name">
                  {{ kb.name }}
                </p>
                <p class="text-[10px] text-slate-400 dark:text-stone-500 mt-0.5">
                  {{ formatDate(kb.uploaded_at) }}
                </p>
              </div>
            </div>
            <button @click="remove(kb.id)"
              class="opacity-0 group-hover:opacity-100 text-slate-300 dark:text-stone-700
                     hover:text-red-500 dark:hover:text-red-400
                     transition-all text-sm flex-shrink-0 mt-0.5">✕</button>
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
        Upload a PDF, DOCX, TXT or Markdown file above to begin building your knowledge base.
      </p>
    </div>

  </main>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRagStore } from '../stores/rag'
import { useUiStore } from '../stores/ui'

const store = useRagStore()
const ui = useUiStore()
const isDragging = ref(false)

const EXT_ICONS = { pdf: '📕', docx: '📘', txt: '📄', md: '📝' }
function fileIcon(name) { return EXT_ICONS[name.split('.').pop().toLowerCase()] || '📄' }
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
    icon: '🗃️', label: 'Vector Store', desc: 'ChromaDB dense embeddings',
    value: store.indexStats.vector_count,
    iconBg: 'bg-emerald-50 dark:bg-emerald-500/10',
  },
  {
    icon: '📝', label: 'BM25 Index', desc: 'Keyword sparse search',
    value: store.indexStats.bm25_count,
    iconBg: 'bg-sky-50 dark:bg-sky-500/10',
  },
  {
    icon: '🕸️', label: 'Knowledge Graph', desc: `${store.indexStats.graph?.edges ?? 0} edges`,
    value: `${store.indexStats.graph?.nodes ?? 0} nodes`,
    iconBg: 'bg-teal-50 dark:bg-teal-500/10',
  },
])

async function handleFile(file) {
  if (!file) return
  store.resetUploadResult()
  try {
    await store.uploadDocument(file)
    setTimeout(() => store.resetUploadResult(), 6000)
  } catch {}
}

function onFileChange(e) { handleFile(e.target.files[0]) }
function onDrop(e) { isDragging.value = false; handleFile(e.dataTransfer.files[0]) }

async function remove(id) {
  if (await ui.confirm('Delete this knowledge base?')) await store.removeKnowledgeBase(id)
}
async function clearAll() {
  if (await ui.confirm('Remove all knowledge bases and clear the index?')) await store.clearIndex()
}
</script>

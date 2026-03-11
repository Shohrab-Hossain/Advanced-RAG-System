<template>
  <div class="relative max-w-7xl mx-auto px-6 sm:px-8 py-6">

    <!-- ── History overlay backdrop ─────────────────────────────── -->
    <transition name="backdrop">
      <div v-if="sidebarOpen"
        class="fixed inset-0 z-30 bg-black/20 dark:bg-black/40 backdrop-blur-[2px]"
        @click="sidebarOpen = false" />
    </transition>

    <!-- ── History Sidebar — aligned to content left edge ─────── -->
    <!-- Outer wrapper mirrors the page layout so left-0 = content start -->
    <div class="fixed top-14 inset-x-0 bottom-0 z-40 pointer-events-none">
      <div class="max-w-7xl mx-auto h-full relative">
    <transition name="sidebar">
      <aside v-if="sidebarOpen"
        class="absolute left-0 top-0 bottom-0 w-72 pointer-events-auto flex flex-col
               bg-white dark:bg-[#1C1917]
               border-r border-stone-200 dark:border-white/[0.07]
               shadow-[4px_0_24px_0_rgb(0,0,0,0.10)] dark:shadow-[4px_0_24px_0_rgb(0,0,0,0.4)]">

        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3
                    border-b border-stone-100 dark:border-white/[0.05] flex-shrink-0">
          <span class="section-label section-label-indigo">Chat History</span>
          <div class="flex items-center gap-3">
            <button v-if="store.chatHistory.length" @click="confirmClearAll"
              class="text-[10px] text-red-400 hover:text-red-600 dark:hover:text-red-400
                     transition-colors font-medium">
              Clear all
            </button>
            <button @click="sidebarOpen = false"
              class="text-slate-400 hover:text-stone-700 dark:text-stone-500 dark:hover:text-slate-300
                     transition-colors text-sm leading-none">
              ✕
            </button>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="!store.chatHistory.length"
          class="flex flex-col items-center justify-center flex-1 px-4 py-10 text-center">
          <span class="text-3xl mb-3 opacity-30">🕐</span>
          <p class="text-xs font-medium text-slate-400 dark:text-slate-600">No history yet</p>
          <p class="text-[11px] text-slate-300 dark:text-stone-700 mt-1">
            Your chats will appear here
          </p>
        </div>

        <!-- List -->
        <div v-else class="flex-1 overflow-y-auto p-2 space-y-0.5">
          <div v-for="item in store.chatHistory" :key="item.id"
            class="group relative flex items-start gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer
                   transition-all duration-150"
            :class="activeHistoryId === item.id
              ? 'bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30'
              : 'border border-transparent hover:bg-stone-50 dark:hover:bg-white/[0.04] hover:border-stone-200 dark:hover:border-white/[0.07]'"
            @click="loadHistory(item)">
            <span class="text-xs flex-shrink-0 mt-0.5 opacity-50">💬</span>
            <div class="flex-1 min-w-0">
              <p class="text-[11px] font-medium leading-snug line-clamp-2"
                 :class="activeHistoryId === item.id
                   ? 'text-emerald-700 dark:text-emerald-300'
                   : 'text-stone-700 dark:text-slate-300'">
                {{ item.query }}
              </p>
              <p class="text-[10px] text-slate-400 dark:text-slate-600 mt-1">
                {{ formatTime(item.timestamp) }}
              </p>
            </div>
            <button
              class="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity
                     text-slate-300 hover:text-red-500 dark:text-slate-600 dark:hover:text-red-400
                     text-xs leading-none mt-0.5 p-0.5"
              @click.stop="confirmDelete(item.id)" title="Delete">
              ✕
            </button>
          </div>
        </div>
      </aside>
    </transition>
      </div>
    </div>

    <!-- ── Main content ──────────────────────────────────────────── -->
    <div class="space-y-5">

      <!-- Header row -->
      <div class="flex items-center justify-between pb-4
                  border-b border-stone-200 dark:border-white/[0.06]">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-500/10
                      flex items-center justify-center text-lg flex-shrink-0">💬</div>
          <div>
            <h1 class="text-xl font-bold tracking-tight text-stone-900 dark:text-stone-100">Chat</h1>
            <p class="text-xs text-slate-400 dark:text-stone-500 mt-0.5 hidden sm:block">
              Ask anything — pipeline retrieves, reranks, and reflects on your knowledge base.
            </p>
          </div>
        </div>

        <!-- Toggle history button -->
        <button @click="sidebarOpen = !sidebarOpen"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium
                 transition-all duration-150 border"
          :class="sidebarOpen
            ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
            : 'bg-white dark:bg-white/[0.03] border-stone-200 dark:border-white/[0.07] text-stone-500 dark:text-slate-400 hover:text-stone-700 dark:hover:text-slate-300'">
          <span class="text-sm">🕐</span>
          <span class="hidden sm:inline">History</span>
          <span v-if="store.chatHistory.length"
            class="text-[10px] px-1.5 py-0.5 rounded-full
                   bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-mono">
            {{ store.chatHistory.length }}
          </span>
        </button>
      </div>

      <!-- No documents warning -->
      <div v-if="!store.hasDocuments && !store.isRunning"
        class="flex items-start gap-3 rounded-xl px-4 py-3
               bg-teal-50 dark:bg-teal-500/[0.08]
               border border-teal-200 dark:border-teal-500/20
               text-teal-800 dark:text-teal-300 text-sm">
        <span class="text-base flex-shrink-0 mt-0.5">⚠️</span>
        <span>
          No documents indexed yet.
          <RouterLink to="/knowledge-base"
            class="font-semibold underline underline-offset-2 hover:no-underline ml-0.5">
            Upload a document
          </RouterLink>
          to get started.
        </span>
      </div>

      <!-- 1. Query input -->
      <QueryInput />

      <!-- Empty state -->
      <div v-if="!store.isRunning && !store.hasResult && !store.error"
           class="flex flex-col items-center justify-center py-14 text-center">
        <div class="w-14 h-14 rounded-2xl
                    bg-gradient-to-br from-emerald-500/10 to-teal-500/10
                    border border-emerald-100 dark:border-emerald-500/15
                    flex items-center justify-center text-2xl mb-4">🔬</div>
        <p class="text-stone-700 dark:text-slate-300 font-semibold text-sm">
          Run the pipeline to see results
        </p>
        <p class="text-slate-400 dark:text-stone-500 text-xs mt-1.5 max-w-sm leading-relaxed">
          Self-RAG planning to hybrid retrieval to cross-encoder reranking to generation to self-reflection.
        </p>
        <div class="flex items-center gap-1.5 mt-5 flex-wrap justify-center">
          <span v-for="(step, i) in pipelineSteps" :key="step.label" class="flex items-center gap-1">
            <span class="flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg
                         bg-white dark:bg-[#1C1917]
                         border border-stone-200 dark:border-white/[0.07]
                         text-stone-500 dark:text-stone-500">
              <span>{{ step.icon }}</span>
              <span>{{ step.label }}</span>
            </span>
            <span v-if="i < pipelineSteps.length - 1"
              class="text-slate-300 dark:text-stone-700 text-[10px]">→</span>
          </span>
        </div>
      </div>

      <!-- 2. Answer + sources -->
      <ResultDisplay v-if="store.hasResult" />

      <!-- 3. Pipeline tracker -->
      <PipelineTracker v-if="store.isRunning || store.hasResult || store.error" />

      <!-- Pipeline metadata -->
      <details v-if="store.hasResult"
        class="group rounded-2xl border border-stone-200 dark:border-white/[0.07]
               bg-white dark:bg-[#1C1917]
               shadow-[0_1px_3px_0_rgb(0,0,0,0.07)] dark:shadow-none
               overflow-hidden">
        <summary class="flex items-center gap-2 px-5 py-3 cursor-pointer
                        hover:bg-stone-50 dark:hover:bg-white/[0.03] transition-colors select-none">
          <span class="section-label section-label-muted">Pipeline Metadata</span>
          <span class="ml-auto text-[10px] text-slate-400 dark:text-slate-600
                       group-open:rotate-180 transition-transform duration-200">▼</span>
        </summary>
        <div class="border-t border-stone-100 dark:border-white/[0.05] px-5 py-4">
          <pre class="text-[11px] font-mono text-slate-400 dark:text-stone-500
                      overflow-x-auto leading-relaxed whitespace-pre-wrap">{{ JSON.stringify(store.metadata, null, 2) }}</pre>
        </div>
      </details>

    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRagStore } from '../stores/rag'
import { useUiStore } from '../stores/ui'
import QueryInput from '../components/QueryInput.vue'
import PipelineTracker from '../components/PipelineTracker.vue'
import ResultDisplay from '../components/ResultDisplay.vue'

const store = useRagStore()
const ui = useUiStore()

const sidebarOpen = ref(false)
const activeHistoryId = ref(null)

const pipelineSteps = [
  { icon: '🧠', label: 'Plan' },
  { icon: '🔍', label: 'Retrieve' },
  { icon: '🎯', label: 'Rerank' },
  { icon: '✂️', label: 'Compress' },
  { icon: '💡', label: 'Generate' },
  { icon: '🔮', label: 'Reflect' },
]

function formatTime(ts) {
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

// When a new query completes and is saved, highlight it in the history list
watch(() => store.chatHistory[0]?.id, (newId) => {
  if (newId && !store.isHistoryResult) {
    activeHistoryId.value = newId
  }
})

function loadHistory(item) {
  activeHistoryId.value = item.id
  store.loadHistoryItem(item)
  sidebarOpen.value = false
}

async function confirmDelete(id) {
  const ok = await ui.confirm('Delete this chat from history?', {
    danger: true, confirmText: 'Yes, delete it', cancelText: 'No, keep it',
  })
  if (!ok) return
  store.deleteHistoryItem(id)
  if (activeHistoryId.value === id) activeHistoryId.value = null
}

async function confirmClearAll() {
  const ok = await ui.confirm('Delete all chat history? This cannot be undone.', {
    danger: true, confirmText: 'Yes, delete all', cancelText: 'No, keep them',
  })
  if (!ok) return
  store.clearChatHistory()
  activeHistoryId.value = null
}
</script>

<style scoped>
.sidebar-enter-active, .sidebar-leave-active { transition: transform 0.22s ease, opacity 0.22s ease; }
.sidebar-enter-from, .sidebar-leave-to { opacity: 0; transform: translateX(-100%); }

.backdrop-enter-active, .backdrop-leave-active { transition: opacity 0.2s ease; }
.backdrop-enter-from, .backdrop-leave-to { opacity: 0; }
</style>

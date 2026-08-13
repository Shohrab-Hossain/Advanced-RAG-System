<template>
  <div class="relative max-w-7xl mx-auto px-6 sm:px-8 py-6">

    <ChatHistorySidebar :open="sidebarOpen" @close="sidebarOpen = false" />

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
      <div v-if="!kb.hasDocuments && !store.isRunning"
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
          <span v-for="(step, i) in PIPELINE_STEPS" :key="step.label" class="flex items-center gap-1">
            <span class="flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg
                         bg-white dark:bg-[#1C1917]
                         border border-stone-200 dark:border-white/[0.07]
                         text-stone-500 dark:text-stone-500">
              <span>{{ step.icon }}</span>
              <span>{{ step.label }}</span>
            </span>
            <span v-if="i < PIPELINE_STEPS.length - 1"
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
import { ref } from 'vue'
import { useRagStore } from '../../../subsystems/rag/ragStore'
import { useKbStore } from '../../../subsystems/knowledge-base/kbStore'
import ChatHistorySidebar from '../components/ChatHistorySidebar/ChatHistorySidebar.vue'
import QueryInput from '../components/QueryInput/QueryInput.vue'
import PipelineTracker from '../components/PipelineTracker/PipelineTracker.vue'
import ResultDisplay from '../components/ResultDisplay/ResultDisplay.vue'
import { PIPELINE_STEPS } from './chatView'

const store = useRagStore()
const kb = useKbStore()

const sidebarOpen = ref(false)
</script>

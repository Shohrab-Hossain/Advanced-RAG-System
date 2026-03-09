<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <!-- Header -->
    <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="text-xl">🧬</span>
          <div>
            <h1 class="text-sm font-bold text-white leading-none">Advanced RAG System</h1>
            <p class="text-[10px] text-slate-500">Self-RAG · GraphRAG · Cross-Encoder</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <!-- Active provider badge -->
          <span class="text-xs font-mono px-2 py-0.5 rounded-full"
            :class="store.llmProvider === 'ollama'
              ? 'bg-emerald-900/60 text-emerald-300'
              : 'bg-brand-900/60 text-brand-300'"
          >
            {{ store.llmProvider === 'ollama' ? '🦙 Ollama' : '🤖 OpenAI' }}
          </span>
          <span
            class="w-2 h-2 rounded-full"
            :class="connected ? 'bg-green-400 animate-pulse' : 'bg-slate-600'"
          />
          <span class="text-xs text-slate-500">{{ connected ? 'API connected' : 'Connecting…' }}</span>
        </div>
      </div>
    </header>

    <!-- Main layout: left sidebar + right panel -->
    <main class="max-w-7xl mx-auto px-4 py-6">
      <div class="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6">

        <!-- Left: controls -->
        <aside class="space-y-4">
          <LLMSelector />
          <FileUpload />
          <KnowledgeBases />
          <QueryInput />
          <PipelineTracker v-if="store.isRunning || store.hasResult || store.error" />
        </aside>

        <!-- Right: pipeline tracker (during run) + results -->
        <section class="space-y-4">
          <!-- Pipeline visible on large screens when running -->
          <PipelineTracker
            class="hidden lg:block"
            v-if="store.isRunning || store.hasResult || store.error"
          />

          <!-- Empty state -->
          <div
            v-if="!store.isRunning && !store.hasResult && !store.error"
            class="flex flex-col items-center justify-center h-64 text-center space-y-3"
          >
            <div class="text-5xl opacity-30">🔬</div>
            <p class="text-slate-400 font-medium">Upload documents and ask a question</p>
            <p class="text-slate-600 text-sm">
              The pipeline will retrieve, rerank, compress,<br>generate, and self-reflect in real time.
            </p>
          </div>

          <!-- Streaming placeholder while running -->
          <div v-if="store.isRunning && !store.hasResult" class="card space-y-3">
            <div class="flex items-center gap-3">
              <div class="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              <span class="text-slate-300 text-sm font-medium">Processing…</span>
            </div>
            <div class="space-y-2">
              <div class="h-3 bg-slate-800 rounded animate-pulse w-full" />
              <div class="h-3 bg-slate-800 rounded animate-pulse w-4/5" />
              <div class="h-3 bg-slate-800 rounded animate-pulse w-3/5" />
            </div>
          </div>

          <!-- Results -->
          <ResultDisplay v-if="store.hasResult" />
        </section>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRagStore } from './stores/rag'
import FileUpload from './components/FileUpload.vue'
import QueryInput from './components/QueryInput.vue'
import PipelineTracker from './components/PipelineTracker.vue'
import ResultDisplay from './components/ResultDisplay.vue'
import LLMSelector from './components/LLMSelector.vue'
import KnowledgeBases from './components/KnowledgeBases.vue'
import { healthCheck } from './services/api'

const store = useRagStore()
const connected = ref(false)

onMounted(async () => {
  try {
    await healthCheck()
    connected.value = true
    await Promise.all([store.refreshStats(), store.fetchProviders(), store.fetchKnowledgeBases()])
  } catch {
    connected.value = false
  }
})
</script>

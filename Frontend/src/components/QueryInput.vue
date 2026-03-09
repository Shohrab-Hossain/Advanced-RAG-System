<template>
  <div class="card space-y-3">
    <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">Ask a Question</h2>

    <div class="relative">
      <textarea
        v-model="localQuery"
        :disabled="store.isRunning"
        placeholder="Ask anything about your documents…"
        rows="3"
        class="w-full bg-slate-800 border border-slate-700 focus:border-brand-600 focus:ring-1 focus:ring-brand-600
               rounded-lg px-4 py-3 text-slate-100 placeholder-slate-500 resize-none outline-none
               transition-colors duration-150 disabled:opacity-50"
        @keydown.ctrl.enter="submit"
        @keydown.meta.enter="submit"
      />
      <span class="absolute bottom-2 right-3 text-[10px] text-slate-600">Ctrl+↵ to send</span>
    </div>

    <div class="flex gap-2">
      <button
        class="btn-primary flex-1 flex items-center justify-center gap-2"
        :disabled="!localQuery.trim() || store.isRunning"
        @click="submit"
      >
        <span v-if="store.isRunning" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        <span>{{ store.isRunning ? 'Running pipeline…' : 'Run RAG Pipeline' }}</span>
      </button>

      <button
        v-if="store.isRunning"
        class="btn-secondary px-3"
        @click="store.abortQuery()"
        title="Cancel"
      >✕</button>
    </div>

    <!-- Example queries -->
    <div v-if="!store.isRunning && !store.hasResult" class="space-y-1">
      <p class="text-[11px] text-slate-600 uppercase tracking-wider">Try an example</p>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="ex in examples"
          :key="ex"
          class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 px-2.5 py-1 rounded-md transition-colors"
          @click="localQuery = ex"
        >{{ ex }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRagStore } from '../stores/rag'

const store = useRagStore()
const localQuery = ref('')

const examples = [
  'Summarize the key findings',
  'What are the main risks mentioned?',
  'Who are the key stakeholders?',
  'What recommendations are given?',
]

function submit() {
  if (!localQuery.value.trim() || store.isRunning) return
  store.runQuery(localQuery.value)
}

// Sync external reset
watch(() => store.query, (q) => { if (!q) localQuery.value = '' })
</script>

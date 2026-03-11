<template>
  <div class="card space-y-4">
    <h2 class="section-label section-label-indigo">Ask a Question</h2>

    <div class="relative">
      <textarea
        ref="textareaRef"
        v-model="localQuery"
        :disabled="store.isRunning"
        placeholder="Ask anything about your documents…"
        rows="3"
        class="w-full bg-stone-50 dark:bg-[#0C0A09]/80
               border border-stone-200 dark:border-white/[0.08]
               focus:border-emerald-400 dark:focus:border-emerald-500/60
               focus:ring-2 focus:ring-emerald-500/10
               focus:outline-none
               rounded-xl px-4 py-3 pr-16
               text-stone-800 dark:text-stone-100
               placeholder-slate-400 dark:placeholder-slate-600
               resize-y overflow-y-auto
               transition duration-150 text-sm
               disabled:opacity-40"
        style="min-height: 80px; max-height: 400px"
        @input="autoGrow"
        @keydown.ctrl.enter="submit"
        @keydown.meta.enter="submit"
      />
      <span class="absolute bottom-2.5 right-3 text-[10px] text-slate-300 dark:text-slate-600 select-none
                   bg-stone-100 dark:bg-white/[0.05] px-1.5 py-0.5 rounded font-mono">
        ⌃↵
      </span>
    </div>

    <div class="flex gap-2">
      <button
        class="btn-primary flex-1 flex items-center justify-center gap-2 text-sm"
        :disabled="!localQuery.trim() || store.isRunning"
        @click="submit"
      >
        <span v-if="store.isRunning"
          class="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin flex-shrink-0" />
        <span v-else class="text-base leading-none">▶</span>
        {{ store.isRunning ? 'Running pipeline…' : 'Run RAG Pipeline' }}
      </button>
      <button v-if="store.isRunning"
        class="btn-secondary px-3 text-sm" @click="store.abortQuery()" title="Cancel">
        ✕
      </button>
    </div>

    <!-- Example queries -->
    <div v-if="!store.isRunning && !store.hasResult" class="space-y-2">
      <p class="text-[10px] text-slate-400 dark:text-slate-600 uppercase tracking-widest font-medium">
        Try an example
      </p>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="ex in examples" :key="ex"
          class="text-xs px-2.5 py-1.5 rounded-lg
                 bg-stone-50 hover:bg-stone-100
                 dark:bg-white/[0.04] dark:hover:bg-white/[0.07]
                 text-stone-500 hover:text-stone-700
                 dark:text-stone-500 dark:hover:text-slate-300
                 border border-stone-200 dark:border-white/[0.07]
                 transition-colors"
          @click="setExample(ex)"
        >{{ ex }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useRagStore } from '../stores/rag'

const store = useRagStore()
const localQuery = ref(store.query)   // initialise from store so nav away/back preserves text
const textareaRef = ref(null)

const examples = [
  'Summarize the key findings',
  'What are the main risks?',
  'Who are the key stakeholders?',
  'What recommendations are given?',
]

function autoGrow() {
  const el = textareaRef.value
  if (!el) return
  // Only auto-grow if content is taller than current box (don't shrink manual resizes)
  const natural = Math.min(el.scrollHeight, 400)
  const current = el.offsetHeight
  if (natural > current) {
    el.style.height = natural + 'px'
  }
}

function setExample(ex) { localQuery.value = ex; nextTick(autoGrow) }

function submit() {
  if (!localQuery.value.trim() || store.isRunning) return
  store.runQuery(localQuery.value)
}

// Keep textarea in sync with store — covers history load, reset, and pipeline completion
watch(() => store.query, (q) => {
  if (localQuery.value !== q) {
    localQuery.value = q
    nextTick(autoGrow)
  }
})
</script>

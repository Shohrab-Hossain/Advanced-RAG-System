<template>
  <div class="space-y-4 animate-fade-in">
    <!-- Answer card -->
    <div class="card space-y-4">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">Answer</h2>
        <div class="flex items-center gap-2">
          <span
            v-if="meta.grounded != null"
            class="text-xs px-2 py-0.5 rounded-full"
            :class="meta.grounded ? 'bg-green-900/50 text-green-400' : 'bg-amber-900/50 text-amber-400'"
          >
            {{ meta.grounded ? '✓ Grounded' : '⚠ Ungrounded' }}
          </span>
          <span
            v-if="meta.confidence != null"
            class="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full"
          >{{ Math.round(meta.confidence * 100) }}% conf.</span>
          <span
            v-if="meta.retry_count"
            class="text-xs bg-amber-900/40 text-amber-400 px-2 py-0.5 rounded-full"
          >{{ meta.retry_count }} retr{{ meta.retry_count > 1 ? 'ies' : 'y' }}</span>
        </div>
      </div>

      <!-- Answer body (rendered markdown) -->
      <div class="prose-rag" v-html="renderedAnswer" />

      <!-- Copy button -->
      <div class="flex justify-end">
        <button class="btn-secondary text-xs" @click="copy">
          {{ copied ? '✓ Copied' : 'Copy answer' }}
        </button>
      </div>
    </div>

    <!-- Sources (collapsible) -->
    <div v-if="store.sources.length" class="card space-y-3">
      <button
        class="w-full flex items-center justify-between group"
        @click="sourcesOpen = !sourcesOpen"
      >
        <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Sources
          <span class="ml-1 text-slate-600 font-normal">({{ store.sources.length }})</span>
        </h2>
        <span class="text-slate-500 group-hover:text-slate-300 transition-colors text-xs">
          {{ sourcesOpen ? '▲ collapse' : '▼ expand' }}
        </span>
      </button>
      <div v-if="sourcesOpen" class="grid gap-2 sm:grid-cols-2">
        <SourceCard v-for="src in store.sources" :key="src.index" :source="src" />
      </div>
    </div>

    <!-- Pipeline metadata -->
    <details class="card text-xs text-slate-500 cursor-pointer">
      <summary class="font-medium text-slate-400 select-none">Pipeline metadata</summary>
      <pre class="mt-2 overflow-x-auto text-[11px]">{{ JSON.stringify(store.metadata, null, 2) }}</pre>
    </details>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { marked } from 'marked'
import { useRagStore } from '../stores/rag'
import SourceCard from './SourceCard.vue'

const store = useRagStore()
const copied = ref(false)
const sourcesOpen = ref(true)

const meta = computed(() => store.metadata || {})

const renderedAnswer = computed(() => {
  if (!store.answer) return ''
  try { return marked.parse(store.answer) } catch { return store.answer }
})

function copy() {
  navigator.clipboard.writeText(store.answer)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
</script>

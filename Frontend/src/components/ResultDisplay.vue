<template>
  <div class="space-y-4 animate-fade-in">

    <!-- Answer -->
    <div class="card space-y-4">
      <div class="flex items-center justify-between flex-wrap gap-2">
        <h2 class="section-label section-label-emerald">Answer</h2>
        <div class="flex items-center gap-2 flex-wrap">
          <span v-if="meta.grounded != null"
            class="text-[10px] font-medium px-2 py-0.5 rounded-full border"
            :class="meta.grounded
              ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
              : 'bg-teal-50 dark:bg-teal-500/10 border-teal-200 dark:border-teal-500/20 text-teal-700 dark:text-teal-400'"
          >{{ meta.grounded ? '✓ Grounded' : '⚠ Ungrounded' }}</span>
          <span v-if="meta.confidence != null"
            class="text-[10px] font-medium px-2 py-0.5 rounded-full
                   bg-stone-100 dark:bg-white/[0.07]
                   text-stone-500 dark:text-slate-400
                   border border-stone-200 dark:border-white/[0.07]">
            {{ Math.round(meta.confidence * 100) }}% conf.
          </span>
          <span v-if="meta.retry_count"
            class="text-[10px] font-medium px-2 py-0.5 rounded-full
                   bg-teal-50 dark:bg-teal-500/10 text-teal-700 dark:text-teal-400
                   border border-teal-200 dark:border-teal-500/20">
            {{ meta.retry_count }} retr{{ meta.retry_count > 1 ? 'ies' : 'y' }}
          </span>
        </div>
      </div>

      <div class="prose-rag" v-html="renderedAnswer" />

      <div class="flex justify-end pt-2 border-t border-stone-100 dark:border-white/[0.05]">
        <button class="btn-secondary text-xs py-1.5 px-3" @click="copy">
          {{ copied ? '✓ Copied' : 'Copy answer' }}
        </button>
      </div>
    </div>

    <!-- Sources -->
    <div v-if="store.sources.length" class="card space-y-3">
      <button class="w-full flex items-center justify-between group" @click="sourcesOpen = !sourcesOpen">
        <h2 class="section-label section-label-sky">
          Sources
          <span class="ml-1 opacity-60 font-normal normal-case tracking-normal">({{ store.sources.length }})</span>
        </h2>
        <span class="text-[10px] text-slate-400 dark:text-slate-600
                     group-hover:text-slate-600 dark:group-hover:text-slate-400
                     transition-colors">
          {{ sourcesOpen ? '▲' : '▼' }}
        </span>
      </button>

      <div v-if="sourcesOpen" class="grid gap-2 sm:grid-cols-2">
        <SourceCard
          v-for="src in store.sources" :key="src.index"
          :source="src" :selected="selectedSource === src"
          @select="toggleSource(src)"
        />
      </div>

      <!-- Content panel -->
      <transition name="slide">
        <div v-if="selectedSource"
          class="rounded-xl border border-stone-200 dark:border-white/[0.07] overflow-hidden">
          <div class="flex items-center justify-between px-4 py-2
                      bg-stone-50 dark:bg-white/[0.04]
                      border-b border-stone-100 dark:border-white/[0.05]">
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-sm leading-none">{{ selectedSourceIcon }}</span>
              <span class="text-xs font-medium text-stone-700 dark:text-slate-300 truncate">
                {{ selectedSourceLabel }}
              </span>
              <span v-if="selectedSource.page" class="text-[10px] text-slate-400">
                · p. {{ selectedSource.page }}
              </span>
            </div>
            <button @click="selectedSource = null"
              class="text-slate-400 hover:text-stone-700 dark:text-stone-500 dark:hover:text-slate-300
                     transition-colors text-sm leading-none ml-2 flex-shrink-0">✕</button>
          </div>
          <pre class="text-[11px] text-slate-600 dark:text-slate-400
                      whitespace-pre-wrap break-words p-4 leading-relaxed
                      max-h-80 overflow-y-auto
                      bg-white dark:bg-[#0C0A09] font-mono">{{ selectedSource.content || selectedSource.content_preview }}</pre>
        </div>
      </transition>
    </div>

  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { marked } from 'marked'
import { useRagStore } from '../stores/rag'
import SourceCard from './SourceCard.vue'

const store = useRagStore()
const copied = ref(false)
const sourcesOpen = ref(true)
const selectedSource = ref(null)

const sourceIcons = { vector: '🗃️', bm25: '📝', graph: '🕸️', web: '🌐' }

const selectedSourceIcon = computed(() =>
  selectedSource.value ? (sourceIcons[selectedSource.value.source_type] || '📄') : '')
const selectedSourceLabel = computed(() =>
  selectedSource.value ? (selectedSource.value.file_name || selectedSource.value.url || 'Source') : '')

watch(() => store.sources, () => { selectedSource.value = null })

function toggleSource(src) {
  selectedSource.value = selectedSource.value === src ? null : src
}

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

<style scoped>
.slide-enter-active, .slide-leave-active { transition: all 0.18s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-4px); }
</style>

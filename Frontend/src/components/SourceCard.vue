<template>
  <div class="bg-slate-800 border border-slate-700 rounded-lg p-3 space-y-1.5 hover:border-slate-600 transition-colors">
    <!-- Header row -->
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-center gap-2 min-w-0">
        <span class="text-base flex-shrink-0">{{ sourceIcon }}</span>
        <span class="text-xs font-medium text-slate-300 truncate">{{ label }}</span>
      </div>
      <div class="flex items-center gap-1 flex-shrink-0">
        <span class="text-[10px] text-slate-500">{{ sourceTag }}</span>
        <span
          class="text-[10px] px-1.5 py-0.5 rounded font-mono"
          :class="scoreClass"
        >{{ scoreLabel }}</span>
      </div>
    </div>

    <!-- Content preview -->
    <p class="text-xs text-slate-400 leading-relaxed line-clamp-3">
      {{ source.content_preview }}
    </p>

    <!-- Footer: page / URL -->
    <div class="flex items-center gap-3 text-[10px] text-slate-600">
      <span v-if="source.page">p. {{ source.page }}</span>
      <a
        v-if="source.url"
        :href="source.url"
        target="_blank"
        rel="noopener"
        class="text-brand-600 hover:text-brand-400 truncate max-w-[200px]"
      >{{ source.url }}</a>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ source: Object })

const sourceIcons = { vector: '🗃️', bm25: '📝', graph: '🕸️', web: '🌐', unknown: '📄' }
const sourceLabels = { vector: 'Vector', bm25: 'BM25', graph: 'Graph', web: 'Web' }

const sourceIcon = computed(() => sourceIcons[props.source.source_type] || '📄')
const sourceTag = computed(() => sourceLabels[props.source.source_type] || props.source.source_type)
const label = computed(() => props.source.file_name || props.source.url || 'Source')

const scoreLabel = computed(() => {
  const s = props.source.rerank_score
  return s != null ? s.toFixed(3) : '—'
})

const scoreClass = computed(() => {
  const s = props.source.rerank_score ?? 0
  if (s > 5) return 'bg-green-900/60 text-green-400'
  if (s > 2) return 'bg-brand-900/60 text-brand-400'
  return 'bg-slate-700 text-slate-500'
})
</script>

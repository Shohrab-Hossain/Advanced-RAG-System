<template>
  <div
    class="border rounded-xl p-3 space-y-2 cursor-pointer transition-all duration-150 group"
    :class="selected
      ? 'border-emerald-300 dark:border-emerald-500/50 bg-emerald-50/60 dark:bg-emerald-500/[0.07]'
      : 'border-stone-200 dark:border-white/[0.07] bg-white dark:bg-white/[0.02] hover:border-slate-300 dark:hover:border-white/[0.12]'"
    @click="$emit('select', source)"
  >
    <!-- Header -->
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-center gap-2 min-w-0">
        <span class="text-[10px] font-bold font-mono px-1.5 py-0.5 rounded bg-stone-100 dark:bg-white/[0.08] text-stone-500 dark:text-slate-400 flex-shrink-0 leading-none">[{{ source.index }}]</span>
        <FileTypeIcon :filename="source.file_name" :type="source.source_type" :size="16" />
        <span class="text-xs font-semibold text-stone-700 dark:text-slate-300 truncate">{{ label }}</span>
      </div>
      <div class="flex items-center gap-1.5 flex-shrink-0">
        <span class="text-[9px] uppercase tracking-wider text-slate-400 dark:text-slate-600 font-medium">
          {{ sourceTag }}
        </span>
        <span class="text-[10px] px-1.5 py-0.5 rounded-md font-mono" :class="scoreClass">{{ scoreLabel }}</span>
      </div>
    </div>

    <!-- Preview -->
    <p class="text-[11px] text-stone-500 dark:text-stone-500 leading-relaxed line-clamp-3">
      {{ source.content_preview }}
    </p>

    <!-- Footer -->
    <div class="flex items-center justify-between text-[10px] text-slate-400 dark:text-slate-600">
      <span v-if="source.page">p. {{ source.page }}</span>
      <a v-if="source.url" :href="source.url" target="_blank" rel="noopener"
        class="text-emerald-500 dark:text-emerald-400 hover:underline truncate max-w-[180px]"
        @click.stop>{{ source.url }}</a>
      <span v-if="!source.page && !source.url" />
      <span class="text-slate-300 dark:text-stone-700 group-hover:text-stone-500 dark:group-hover:text-stone-500 transition-colors">
        {{ selected ? '▲' : '▼' }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import FileTypeIcon from './FileTypeIcon.vue'

const props = defineProps({ source: Object, selected: Boolean })
defineEmits(['select'])

const sourceLabels = { vector: 'Vector', bm25: 'BM25', graph: 'Graph', web: 'Web' }

const sourceTag = computed(() => sourceLabels[props.source.source_type] || props.source.source_type)
const label      = computed(() => props.source.file_name || props.source.url || 'Source')

const scoreLabel = computed(() => {
  const s = props.source.rerank_score
  return s != null ? s.toFixed(3) : '—'
})

const scoreClass = computed(() => {
  const s = props.source.rerank_score ?? 0
  if (s > 5) return 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
  if (s > 2) return 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
  return 'bg-stone-100 dark:bg-white/[0.06] text-slate-400 dark:text-stone-500'
})
</script>

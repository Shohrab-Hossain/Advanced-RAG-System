<template>
  <div class="flex items-start gap-3 px-3 py-2 rounded-xl transition-all duration-300" :class="rowClass">
    <!-- Status icon -->
    <div class="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-lg text-xs mt-0.5" :class="iconBg">
      <span v-if="status.status === 'active'"
        class="w-3 h-3 border-[1.5px] border-current border-t-transparent rounded-full animate-spin" />
      <span v-else-if="status.status === 'complete'" class="text-[10px]">✓</span>
      <span v-else-if="status.status === 'error'"   class="text-[10px]">✗</span>
      <span v-else-if="status.status === 'skipped'" class="text-[10px]">–</span>
      <span v-else class="text-[11px]">{{ stage.icon }}</span>
    </div>

    <!-- Label + message -->
    <div class="flex-1 min-w-0 py-0.5">
      <div class="flex items-center gap-2">
        <span class="text-xs font-semibold" :class="labelClass">{{ stage.label }}</span>
        <span v-if="status.status === 'skipped'"
          class="text-[9px] px-1.5 py-0.5 rounded
                 bg-stone-100 dark:bg-white/[0.05]
                 text-slate-400 dark:text-slate-600">skipped</span>
      </div>
      <p class="text-[11px] mt-0.5 truncate leading-snug" :class="msgClass">
        {{ status.message || stage.desc }}
      </p>
      <!-- Detail chips -->
      <div v-if="status.status === 'complete' && chips.length" class="flex flex-wrap gap-1 mt-1.5">
        <span v-for="chip in chips" :key="chip"
          class="text-[9px] px-1.5 py-0.5 rounded-md
                 bg-stone-100 dark:bg-white/[0.06]
                 text-stone-500 dark:text-stone-500 font-mono">{{ chip }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ stage: Object, status: Object })
const s = computed(() => props.status.status)

const rowClass = computed(() => ({
  'bg-emerald-50/70 dark:bg-emerald-500/[0.07]': s.value === 'active',
  'bg-emerald-50/50 dark:bg-emerald-500/[0.05]': s.value === 'complete',
  'opacity-35': s.value === 'skipped',
  'bg-red-50/60 dark:bg-red-500/[0.06]': s.value === 'error',
}))

const iconBg = computed(() => ({
  'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400': s.value === 'active',
  'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400': s.value === 'complete',
  'bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400': s.value === 'error',
  'bg-stone-100 dark:bg-white/[0.05] text-slate-400 dark:text-slate-600': s.value === 'idle' || s.value === 'skipped',
}))

const labelClass = computed(() => ({
  'text-emerald-600 dark:text-emerald-300': s.value === 'active',
  'text-emerald-600 dark:text-emerald-400': s.value === 'complete',
  'text-red-600 dark:text-red-400': s.value === 'error',
  'text-stone-700 dark:text-slate-300': s.value === 'idle',
  'text-slate-400 dark:text-slate-600': s.value === 'skipped',
}))

const msgClass = computed(() => ({
  'text-emerald-500 dark:text-emerald-400': s.value === 'active',
  'text-slate-400 dark:text-stone-500': s.value !== 'active',
}))

const chips = computed(() => {
  const d = props.status.details
  if (!d) return []
  const out = []
  if (d.vector_count != null) out.push(`${d.vector_count} vector`)
  if (d.bm25_count   != null) out.push(`${d.bm25_count} BM25`)
  if (d.graph_count  != null) out.push(`${d.graph_count} graph`)
  if (d.web_count    != null) out.push(`${d.web_count} web`)
  if (d.top_k        != null) out.push(`top ${d.top_k}`)
  if (d.confidence   != null) out.push(`${Math.round(d.confidence * 100)}% conf.`)
  if (d.grounded     != null) out.push(d.grounded ? 'grounded ✓' : 'ungrounded')
  if (d.ratio        != null) out.push(`${Math.round(d.ratio * 100)}% size`)
  return out
})
</script>

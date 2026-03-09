<template>
  <div
    class="flex items-start gap-3 px-3 py-2.5 rounded-lg transition-all duration-300"
    :class="rowClass"
  >
    <!-- Icon / spinner -->
    <div class="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-md text-base" :class="iconBg">
      <span v-if="status.status === 'active'" class="w-4 h-4 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
      <span v-else-if="status.status === 'complete'">✓</span>
      <span v-else-if="status.status === 'error'">✗</span>
      <span v-else-if="status.status === 'skipped'">–</span>
      <span v-else>{{ stage.icon }}</span>
    </div>

    <!-- Text -->
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium" :class="labelClass">{{ stage.label }}</span>
        <span v-if="status.status === 'skipped'" class="text-[10px] bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded">skipped</span>
      </div>
      <p class="text-xs mt-0.5 truncate" :class="msgClass">
        {{ status.message || stage.desc }}
      </p>

      <!-- Detail chips for complete stages -->
      <div v-if="status.status === 'complete' && chips.length" class="flex flex-wrap gap-1 mt-1.5">
        <span
          v-for="chip in chips"
          :key="chip"
          class="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded"
        >{{ chip }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stage: Object,
  status: Object,
})

const s = computed(() => props.status.status)

const rowClass = computed(() => ({
  'bg-brand-900/20 border border-brand-800/50': s.value === 'active',
  'bg-green-900/10': s.value === 'complete',
  'bg-slate-900/50': s.value === 'idle',
  'opacity-40': s.value === 'skipped',
  'bg-red-900/20': s.value === 'error',
}))

const iconBg = computed(() => ({
  'bg-brand-900 text-brand-400': s.value === 'active',
  'bg-green-900/60 text-green-400': s.value === 'complete',
  'bg-red-900/60 text-red-400': s.value === 'error',
  'bg-slate-800 text-slate-400': s.value === 'idle' || s.value === 'skipped',
}))

const labelClass = computed(() => ({
  'text-brand-300': s.value === 'active',
  'text-green-300': s.value === 'complete',
  'text-red-300': s.value === 'error',
  'text-slate-300': s.value === 'idle',
  'text-slate-500': s.value === 'skipped',
}))

const msgClass = computed(() => ({
  'text-brand-400': s.value === 'active',
  'text-slate-400': s.value !== 'active',
}))

// Extract meaningful chips from details
const chips = computed(() => {
  const d = props.status.details
  if (!d) return []
  const out = []
  if (d.vector_count != null) out.push(`${d.vector_count} vector`)
  if (d.bm25_count != null) out.push(`${d.bm25_count} BM25`)
  if (d.graph_count != null) out.push(`${d.graph_count} graph`)
  if (d.web_count != null) out.push(`${d.web_count} web`)
  if (d.top_k != null) out.push(`top ${d.top_k}`)
  if (d.confidence != null) out.push(`${Math.round(d.confidence * 100)}% conf.`)
  if (d.grounded != null) out.push(d.grounded ? 'grounded' : 'ungrounded')
  if (d.ratio != null) out.push(`${Math.round(d.ratio * 100)}% size`)
  return out
})
</script>

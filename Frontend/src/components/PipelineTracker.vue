<template>
  <div class="card space-y-1">
    <!-- Header -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <h2 class="section-label section-label-amber">Pipeline</h2>
        <span v-if="store.isRunning"
          class="w-3 h-3 border-[1.5px] border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>
      <div class="flex items-center gap-2">
        <span v-if="store.retryCount > 0"
          class="text-[10px] font-medium px-2 py-0.5 rounded-full
                 bg-teal-50 dark:bg-teal-500/10
                 text-teal-700 dark:text-teal-400
                 border border-teal-200 dark:border-teal-500/20">
          Retry {{ store.retryCount }}
        </span>
        <span v-if="store.isRunning"
          class="text-[10px] text-slate-400 dark:text-stone-500 tabular-nums font-mono">
          {{ completedCount }}/{{ STAGES.length }}
        </span>
      </div>
    </div>

    <!-- Progress bar -->
    <div v-if="store.isRunning || store.hasResult"
      class="h-1 rounded-full bg-stone-100 dark:bg-white/[0.06] overflow-hidden mb-4">
      <div class="h-full rounded-full transition-all duration-500 ease-out"
        :class="store.hasResult ? 'bg-emerald-500' : 'bg-teal-400 dark:bg-teal-500'"
        :style="{ width: progressPct + '%' }" />
    </div>

    <!-- Stages -->
    <div class="space-y-0.5">
      <StageRow v-for="stage in STAGES" :key="stage.id"
        :stage="stage" :status="store.stageStatuses[stage.id]" />
    </div>

    <!-- Error -->
    <div v-if="store.error"
      class="mt-3 rounded-xl px-4 py-3 text-xs
             bg-red-50 dark:bg-red-500/[0.07]
             text-red-700 dark:text-red-400
             border border-red-200 dark:border-red-500/20">
      ✗ {{ store.error }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRagStore, STAGES } from '../stores/rag'
import StageRow from './StageRow.vue'

const store = useRagStore()

const completedCount = computed(() =>
  STAGES.filter(s => ['complete', 'skipped'].includes(store.stageStatuses[s.id]?.status)).length
)

const progressPct = computed(() => {
  if (store.hasResult) return 100
  const active = STAGES.findIndex(s => store.stageStatuses[s.id]?.status === 'active')
  const numerator = completedCount.value + (active >= 0 ? 0.5 : 0)
  return Math.round((numerator / STAGES.length) * 100)
})
</script>

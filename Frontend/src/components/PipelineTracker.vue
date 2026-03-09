<template>
  <div class="card space-y-1">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">Pipeline</h2>
      <span v-if="store.retryCount > 0" class="text-xs bg-amber-900/40 text-amber-400 px-2 py-0.5 rounded-full">
        Retry {{ store.retryCount }}
      </span>
    </div>

    <div class="space-y-1">
      <StageRow
        v-for="stage in STAGES"
        :key="stage.id"
        :stage="stage"
        :status="store.stageStatuses[stage.id]"
      />
    </div>

    <!-- Error banner -->
    <div v-if="store.error" class="mt-3 bg-red-900/40 border border-red-800 rounded-lg px-3 py-2 text-sm text-red-400">
      ✗ {{ store.error }}
    </div>
  </div>
</template>

<script setup>
import { useRagStore, STAGES } from '../stores/rag'
import StageRow from './StageRow.vue'

const store = useRagStore()
</script>

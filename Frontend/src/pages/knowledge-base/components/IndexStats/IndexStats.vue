<template>
  <!-- Index stats — 3 horizontal cards (graph card slightly wider) -->
  <div class="grid grid-cols-1 sm:grid-cols-[1fr_1fr_1.4fr] gap-3">
    <div v-for="stat in stats" :key="stat.label"
      class="rounded-2xl border p-4 flex flex-col gap-3"
      :class="stat.cardBg">

      <!-- Icon + type badge -->
      <div class="flex items-start justify-between">
        <div class="w-9 h-9 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
          :class="stat.iconBg">{{ stat.icon }}</div>
        <span class="text-[9px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide"
          :class="stat.pillBg">{{ stat.badge }}</span>
      </div>

      <!-- Number section: single big number OR 3-column (graph card) -->
      <div v-if="!stat.triple">
        <p class="text-3xl font-extrabold tabular-nums leading-none" :class="stat.valueColor">{{ stat.value }}</p>
        <p class="text-[9px] font-medium uppercase tracking-widest mt-1 text-slate-400 dark:text-stone-500">{{ stat.unit }}</p>
      </div>
      <div v-else class="grid grid-cols-3">
        <div v-for="(m, i) in stat.triple" :key="m.label"
          :class="i === 0 ? 'text-left' : i === 1 ? 'text-center' : 'text-right'">
          <p class="text-3xl font-extrabold tabular-nums leading-none" :class="stat.valueColor">{{ m.val }}</p>
          <p class="text-[9px] font-medium uppercase tracking-widest mt-1 text-slate-400 dark:text-stone-500">{{ m.label }}</p>
        </div>
      </div>

      <!-- Footer: label + desc (no footer for graph card) -->
      <div class="border-t pt-2.5" :class="stat.dividerColor">
        <p class="text-[11px] font-semibold" :class="stat.labelColor">{{ stat.label }}</p>
        <p v-if="!stat.triple" class="text-[9px] text-slate-400 dark:text-stone-500 mt-0.5 leading-tight">{{ stat.desc }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  stats: { type: Array, required: true },
})
</script>

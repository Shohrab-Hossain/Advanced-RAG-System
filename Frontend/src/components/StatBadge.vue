<template>
  <div class="bg-stone-50 dark:bg-stone-800 rounded-xl px-3 py-2.5 text-center
              border border-stone-100 dark:border-stone-800">
    <div class="text-lg font-bold text-stone-800 dark:text-stone-200">{{ value }}</div>
    <div class="text-[10px] text-stone-400 dark:text-stone-400 uppercase tracking-widest mt-0.5">{{ label }}</div>
  </div>
</template>

<script setup>
defineProps({ label: String, value: [Number, String] })
</script>

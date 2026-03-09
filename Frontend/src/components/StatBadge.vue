<template>
  <div class="bg-slate-800 rounded-lg px-3 py-2 text-center">
    <div class="text-lg font-bold text-brand-400">{{ value }}</div>
    <div class="text-[10px] text-slate-500 uppercase tracking-wider">{{ label }}</div>
  </div>
</template>

<script setup>
defineProps({ label: String, value: [Number, String] })
</script>

<template>
  <!-- Uploaded knowledge bases -->
  <div v-if="items.length" class="space-y-4 pt-2 border-t border-stone-200 dark:border-white/[0.06]">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-base font-semibold text-stone-900 dark:text-stone-100">
          Uploaded Files
          <span class="ml-2 text-sm font-normal text-slate-400 dark:text-stone-500">
            {{ items.length }} {{ items.length === 1 ? 'file' : 'files' }}
          </span>
        </h2>
        <p class="text-xs text-slate-400 dark:text-stone-500 mt-0.5">
          Each file is independently retrievable and can be removed without affecting others.
        </p>
      </div>
      <button @click="$emit('clear')"
        class="text-xs font-medium text-slate-400 hover:text-red-500 dark:text-stone-500 dark:hover:text-red-400
               transition-colors px-3 py-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-500/[0.08]">
        Clear all
      </button>
    </div>

    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="kb in items" :key="kb.id"
        class="card group cursor-pointer
               transition-all duration-200
               hover:shadow-[0_4px_20px_rgba(16,185,129,0.12),0_2px_8px_rgba(0,0,0,0.08)]
               dark:hover:shadow-[0_4px_24px_rgba(52,211,153,0.10),0_2px_8px_rgba(0,0,0,0.3)]
               hover:border-emerald-200 dark:hover:border-emerald-500/25">

        <!-- Header -->
        <div class="flex items-start justify-between gap-2 mb-4">
          <div class="flex items-center gap-3 min-w-0">
            <FileTypeIcon :filename="kb.name" :size="28" />
            <div class="min-w-0">
              <p class="text-sm font-semibold text-stone-800 dark:text-stone-200 truncate" :title="kb.name">
                {{ kb.name }}
              </p>
              <p class="text-[10px] text-slate-400 dark:text-stone-500 mt-0.5">
                {{ kb.uploadedLabel }}
              </p>
            </div>
          </div>
          <button @click="$emit('remove', kb.id)" title="Delete file"
            class="opacity-20 group-hover:opacity-100 text-slate-400 dark:text-stone-600
                   hover:text-red-500 dark:hover:text-red-400
                   cursor-pointer transition-all text-sm flex-shrink-0 mt-0.5
                   hover:scale-110 active:scale-95">✕</button>
        </div>

        <!-- Stats row -->
        <div class="grid grid-cols-3 gap-2 text-center">
          <div v-for="s in kb.stats" :key="s.label"
            class="bg-stone-50 dark:bg-white/[0.03] rounded-lg py-2 px-1
                   border border-stone-100 dark:border-white/[0.05]">
            <div class="text-sm font-bold tabular-nums text-stone-700 dark:text-slate-300">{{ s.val }}</div>
            <div class="text-[9px] uppercase tracking-wide text-slate-400 dark:text-stone-500 mt-0.5">{{ s.label }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Empty state -->
  <div v-else
    class="flex flex-col items-center justify-center py-20 text-center">
    <div class="w-16 h-16 rounded-2xl
                bg-gradient-to-br from-emerald-500/10 to-sky-500/10
                border border-emerald-100 dark:border-emerald-500/15
                flex items-center justify-center text-3xl mb-4">🗂️</div>
    <p class="text-stone-700 dark:text-slate-300 font-semibold text-sm">No documents yet</p>
    <p class="text-slate-400 dark:text-stone-500 text-xs mt-1.5 max-w-xs leading-relaxed">
      Upload a PDF, DOCX, TXT, Markdown, JSON, CSV, HTML, or code file above to begin building your knowledge base.
    </p>
  </div>
</template>

<script setup>
import FileTypeIcon from '../../../../shared/components/FileTypeIcon/FileTypeIcon.vue'

defineProps({
  items: { type: Array, required: true },
})

defineEmits(['remove', 'clear'])
</script>

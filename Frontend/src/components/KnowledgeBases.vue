<template>
  <div v-if="store.knowledgeBases.length" class="card-sidebar space-y-3">
    <div class="flex items-center justify-between">
      <button @click="open = !open"
        class="flex items-center gap-2 group text-left">
        <h2 class="section-label section-label-muted">
          Knowledge Bases
          <span class="ml-1 opacity-60 font-normal normal-case tracking-normal">({{ store.knowledgeBases.length }})</span>
        </h2>
        <span class="text-[10px] text-stone-400 group-hover:text-stone-600 dark:group-hover:text-stone-300 transition-colors">
          {{ open ? '▲' : '▼' }}
        </span>
      </button>
      <button v-if="open" @click="clearAll"
        class="text-[11px] text-stone-400 hover:text-red-500 dark:text-stone-400 dark:hover:text-red-400
               transition-colors">
        Clear all
      </button>
    </div>

    <div v-show="open" class="space-y-2">
      <div v-for="kb in store.knowledgeBases" :key="kb.id"
        class="bg-stone-50 dark:bg-stone-700/30
               border border-stone-200 dark:border-stone-700/50
               rounded-xl px-3 py-2.5 space-y-2">

        <!-- Name + delete -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-sm flex-shrink-0">{{ fileIcon(kb.name) }}</span>
            <span class="text-xs font-medium text-stone-700 dark:text-stone-300 truncate" :title="kb.name">
              {{ kb.name }}
            </span>
          </div>
          <button @click="remove(kb.id)"
            class="text-stone-300 dark:text-stone-500 hover:text-red-500 dark:hover:text-red-400
                   transition-colors text-sm flex-shrink-0">✕</button>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-3 gap-1.5 text-[10px]">
          <div class="bg-stone-50 dark:bg-stone-700/40 rounded-lg px-2 py-1.5 text-center">
            <div class="font-semibold text-stone-700 dark:text-stone-300">{{ kb.vectors }}</div>
            <div class="text-stone-400 dark:text-stone-400 mt-0.5">Vectors</div>
          </div>
          <div class="bg-stone-50 dark:bg-stone-700/40 rounded-lg px-2 py-1.5 text-center">
            <div class="font-semibold text-stone-700 dark:text-stone-300">{{ kb.entities }}</div>
            <div class="text-stone-400 dark:text-stone-400 mt-0.5">Entities</div>
          </div>
          <div class="bg-stone-50 dark:bg-stone-700/40 rounded-lg px-2 py-1.5 text-center">
            <div class="font-semibold text-stone-700 dark:text-stone-300">{{ kb.chunks }}</div>
            <div class="text-stone-400 dark:text-stone-400 mt-0.5">Chunks</div>
          </div>
        </div>

        <div class="text-[10px] text-stone-300 dark:text-stone-500">{{ formatDate(kb.uploaded_at) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRagStore } from '../stores/rag'
import { useUiStore } from '../stores/ui'

const open = ref(true)

const store = useRagStore()
const ui = useUiStore()

const EXT_ICONS = { pdf: '📕', docx: '📘', txt: '📄', md: '📝' }
function fileIcon(name) { return EXT_ICONS[name.split('.').pop().toLowerCase()] || '📄' }
function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function remove(id) {
  if (await ui.confirm('Delete this knowledge base?')) await store.removeKnowledgeBase(id)
}
async function clearAll() {
  if (await ui.confirm('Remove all knowledge bases?')) await store.clearIndex()
}
</script>

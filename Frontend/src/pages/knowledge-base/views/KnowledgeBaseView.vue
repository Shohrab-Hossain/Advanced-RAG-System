<template>
  <main class="max-w-6xl mx-auto px-6 sm:px-8 py-8 space-y-8">

    <!-- Page header -->
    <div class="flex items-start gap-4 pb-5 border-b border-stone-200 dark:border-white/[0.06]">
      <div class="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-500/10
                  flex items-center justify-center text-xl flex-shrink-0 mt-0.5">🗂️</div>
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-stone-900 dark:text-stone-100">Knowledge Base</h1>
        <p class="text-sm text-stone-500 dark:text-slate-400 mt-1 leading-relaxed max-w-2xl">
          Upload documents to build your knowledge base. Each file is chunked into overlapping passages,
          embedded into a vector store, indexed with BM25 for keyword search, and added to the knowledge
          graph for entity-aware retrieval.
        </p>
      </div>
    </div>

    <!-- Upload + Stats -->
    <div class="space-y-5">
      <UploadPanel :accept="ACCEPT_ATTR" />

      <!-- Index stats header -->
      <div class="flex items-center gap-3 pt-1">
        <p class="section-label section-label-muted whitespace-nowrap">Index Overview</p>
        <div class="h-px flex-1 bg-stone-200 dark:bg-white/[0.06]" />
      </div>

      <IndexStats :stats="indexStats" />
    </div>

    <KnowledgeBaseList :items="kbCards" @remove="remove" @clear="clearAll" />

  </main>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useKbStore } from '../../../store/kbStore'
import { useUiStore } from '../../../store'
import UploadPanel from '../components/UploadPanel/UploadPanel.vue'
import IndexStats from '../components/IndexStats/IndexStats.vue'
import KnowledgeBaseList from '../components/KnowledgeBaseList/KnowledgeBaseList.vue'
import { ACCEPT_ATTR, buildIndexStats, buildKbCards } from './knowledgeBaseView'

const store = useKbStore()
const ui = useUiStore()

// The children are presentational — the view owns the data and hands each one
// a finished view-model, so no component reaches back up into this folder.
const indexStats = computed(() => buildIndexStats(store.indexStats))
const kbCards = computed(() => buildKbCards(store.knowledgeBases))

onMounted(async () => {
  await Promise.all([store.refreshStats(), store.fetchKnowledgeBases()])
})

// ── KB management ─────────────────────────────────────────────────────────────

async function remove(id) {
  if (await ui.confirm('Delete this file from the knowledge base?', {
    danger: true, confirmText: 'Yes, delete it', cancelText: 'No, keep it',
  })) await store.removeKnowledgeBase(id)
}

async function clearAll() {
  if (await ui.confirm('Remove all knowledge bases and clear the entire index?', {
    danger: true, confirmText: 'Yes, clear all', cancelText: 'No, keep them',
  })) await store.clearIndex()
}
</script>

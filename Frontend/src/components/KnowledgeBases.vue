<template>
  <div v-if="store.knowledgeBases.length" class="card space-y-3">
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">
        Knowledge Bases
        <span class="ml-1 text-slate-600 font-normal">({{ store.knowledgeBases.length }})</span>
      </h2>
      <button
        class="text-xs text-red-400 hover:text-red-300 transition-colors"
        @click="clearAll"
      >Clear all</button>
    </div>

    <div class="space-y-2">
      <div
        v-for="kb in store.knowledgeBases"
        :key="kb.id"
        class="bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2.5 space-y-2"
      >
        <!-- Name + delete -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-base flex-shrink-0">{{ fileIcon(kb.name) }}</span>
            <span class="text-xs font-medium text-slate-200 truncate" :title="kb.name">{{ kb.name }}</span>
          </div>
          <button
            class="text-slate-600 hover:text-red-400 transition-colors text-sm flex-shrink-0"
            title="Remove this knowledge base"
            @click="remove(kb.id)"
          >✕</button>
        </div>

        <!-- Stats row -->
        <div class="grid grid-cols-3 gap-1.5 text-[10px]">
          <div class="bg-slate-900/60 rounded px-2 py-1 text-center">
            <div class="text-brand-400 font-semibold">{{ kb.vectors }}</div>
            <div class="text-slate-500">Vectors</div>
          </div>
          <div class="bg-slate-900/60 rounded px-2 py-1 text-center">
            <div class="text-purple-400 font-semibold">{{ kb.entities }}</div>
            <div class="text-slate-500">Entities</div>
          </div>
          <div class="bg-slate-900/60 rounded px-2 py-1 text-center">
            <div class="text-slate-300 font-semibold">{{ kb.chunks }}</div>
            <div class="text-slate-500">Chunks</div>
          </div>
        </div>

        <!-- Upload time -->
        <div class="text-[10px] text-slate-600">
          {{ formatDate(kb.uploaded_at) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRagStore } from '../stores/rag'

const store = useRagStore()

const EXT_ICONS = { pdf: '📕', docx: '📘', txt: '📄', md: '📝' }

function fileIcon(name) {
  const ext = name.split('.').pop().toLowerCase()
  return EXT_ICONS[ext] || '📄'
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function remove(id) {
  await store.removeKnowledgeBase(id)
}

async function clearAll() {
  if (!confirm('Remove all knowledge bases?')) return
  await store.clearIndex()
}
</script>

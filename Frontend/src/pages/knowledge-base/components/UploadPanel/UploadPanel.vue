<template>
  <div class="card space-y-5">
    <div>
      <p class="section-label section-label-indigo mb-1">Upload Document</p>
      <p class="text-xs text-slate-400 dark:text-stone-500">
        PDF · DOCX · TXT · MD · JSON · CSV · HTML · Code files — up to 50 MB
      </p>
    </div>

    <!-- Drop zone -->
    <div
      class="relative border-2 border-dashed rounded-xl p-10 text-center
             transition-all duration-150 cursor-pointer"
      :class="[
        isDragging
          ? 'border-emerald-400 dark:border-emerald-500 bg-emerald-50 dark:bg-emerald-500/[0.07]'
          : 'border-stone-200 dark:border-white/[0.08] hover:border-emerald-300 dark:hover:border-emerald-500/30 hover:bg-stone-50 dark:hover:bg-white/[0.02]',
        (store.uploading || store.isIndexing) ? 'pointer-events-none opacity-50' : '',
      ]"
      @dragenter.prevent="onDragEnter"
      @dragover.prevent
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
      @click="$refs.fileInput.click()"
    >
      <input ref="fileInput" type="file" multiple class="hidden"
             :accept="accept" @change="onFileChange" />
      <div class="text-4xl mb-3">
        {{ isDragging && dragCount > 1 ? '📚' : '📄' }}
      </div>
      <p class="text-sm font-semibold text-stone-700 dark:text-slate-300">
        {{ isDragging && dragCount > 1
            ? `Drop ${dragCount} files`
            : 'Drop files here, or click to browse' }}
      </p>
      <p class="text-xs text-slate-400 dark:text-stone-500 mt-1.5">
        PDF · DOCX · TXT · MD · JSON · CSV · HTML · Code files — multiple files supported
      </p>
    </div>

    <!-- Unified progress: upload → processing → indexing (no gap) -->
    <div v-if="store.uploading || store.isIndexing" class="space-y-2">
      <div class="flex items-center justify-between text-xs text-stone-500 dark:text-slate-400">
        <span class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
          {{ progressLabel }}
          <span v-if="store.uploadQueueTotal > 1"
            class="ml-0.5 text-[10px] px-1.5 py-0.5 rounded font-mono
                   bg-stone-100 dark:bg-white/[0.06] text-slate-400 dark:text-stone-500">
            {{ store.uploadQueueCurrent }}/{{ store.uploadQueueTotal }}
          </span>
        </span>
        <span v-if="progressPct !== null" class="font-mono tabular-nums">{{ progressPct }}%</span>
      </div>
      <div class="h-1.5 bg-stone-100 dark:bg-white/[0.06] rounded-full overflow-hidden">
        <!-- Determinate bar (uploading / indexing) -->
        <div v-if="progressPct !== null"
          class="h-full bg-emerald-500 rounded-full transition-all duration-200"
          :style="{ width: progressPct + '%' }" />
        <!-- Indeterminate shimmer while server processes the file -->
        <div v-else class="h-full rounded-full bg-gradient-to-r from-emerald-500/30 via-emerald-500 to-emerald-500/30
                           animate-shimmer bg-[length:200%_100%]" />
      </div>
    </div>

    <!-- Status message -->
    <div v-if="store.uploadResult"
      class="text-xs rounded-xl px-4 py-3 flex items-start justify-between gap-2"
      :class="store.uploadResult.error
        ? 'bg-red-50 dark:bg-red-500/[0.07] text-red-700 dark:text-red-400 border border-red-200 dark:border-red-500/20'
        : 'bg-emerald-50 dark:bg-emerald-500/[0.07] text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20'"
    >
      <span v-if="store.uploadResult.error">✗ {{ store.uploadResult.error }}</span>
      <span v-else>
        ✓ Indexed <strong>{{ store.uploadResult.file_name }}</strong>
        — {{ store.uploadResult.chunks_indexed }} chunks added
      </span>
      <button @click="store.resetUploadResult()"
        class="shrink-0 opacity-50 hover:opacity-100 text-base leading-none transition-opacity">×</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useKbStore } from '../../../../store/kbStore'
import { useUiStore } from '../../../../store'

defineProps({
  accept: { type: String, required: true },
})

const store = useKbStore()
const ui = useUiStore()
const isDragging = ref(false)
const dragCount = ref(0)

// ── Drag handlers ────────────────────────────────────────────────────────────

function onDragEnter(e) {
  isDragging.value = true
  dragCount.value = e.dataTransfer?.items?.length ?? 1
}
function onDragLeave() {
  isDragging.value = false
  dragCount.value = 0
}

// ── Progress label / pct ─────────────────────────────────────────────────────

const progressLabel = computed(() => {
  if (store.isIndexing) return 'Indexing chunks…'
  if (store.uploading && store.uploadProgress >= 100) return 'Processing on server…'
  return 'Uploading file…'
})

const progressPct = computed(() => {
  if (store.isIndexing) return store.indexingProgress
  if (store.uploading && store.uploadProgress < 100) return store.uploadProgress
  return null   // indeterminate shimmer during server-processing phase
})

// ── Upload helpers ────────────────────────────────────────────────────────────

async function handleFiles(files) {
  if (!files.length) return
  const total = files.length
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const duplicate = store.knowledgeBases.find(
      kb => kb.name.toLowerCase() === file.name.toLowerCase(),
    )
    if (duplicate) {
      const ok = await ui.confirm(
        `"${file.name}" is already in the knowledge base. Re-upload to re-index it?`,
        { confirmText: 'Yes, re-index it', cancelText: 'No, keep existing' },
      )
      if (!ok) continue
      await store.removeKnowledgeBase(duplicate.id)
    }
    store.resetUploadResult()
    try {
      await store.uploadDocument(file, { queueCurrent: i + 1, queueTotal: total })
    } catch {
      // Swallowed on purpose: uploadDocument already records the failure on the
      // store, and the queue must continue so one bad file cannot abort the rest.
    }
  }
  setTimeout(() => store.resetUploadResult(), 6000)
}

function onFileChange(e) {
  const files = Array.from(e.target.files)
  e.target.value = ''   // reset so re-selecting same files triggers change
  handleFiles(files)
}

function onDrop(e) {
  isDragging.value = false
  dragCount.value = 0
  handleFiles(Array.from(e.dataTransfer.files))
}
</script>

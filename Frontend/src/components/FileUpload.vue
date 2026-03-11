<template>
  <div class="card-sidebar space-y-4">
    <h2 class="section-label section-label-muted">Upload Document</h2>

    <!-- Drop zone -->
    <div
      class="relative border-2 border-dashed rounded-xl p-6 text-center transition-all duration-150 cursor-pointer"
      :class="[
        isDragging
          ? 'border-teal-400 dark:border-teal-500 bg-teal-50 dark:bg-teal-950/20'
          : 'border-stone-200 dark:border-stone-800 hover:border-stone-300 dark:hover:border-stone-700',
        (store.uploading || store.isIndexing) ? 'pointer-events-none opacity-50' : '',
      ]"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="$refs.fileInput.click()"
    >
      <input ref="fileInput" type="file" class="hidden" :accept="accept" @change="onFileChange" />
      <div class="text-2xl mb-2">📄</div>
      <p class="text-sm text-stone-600 dark:text-stone-400 font-medium">
        Drop a file or click to browse
      </p>
      <p class="text-xs text-stone-400 dark:text-stone-400 mt-1">
        PDF · DOCX · TXT · Markdown
      </p>
    </div>

    <!-- Upload progress -->
    <div v-if="store.uploading" class="space-y-1.5">
      <div class="flex justify-between text-xs text-stone-500 dark:text-stone-400">
        <span>Uploading…</span><span>{{ store.uploadProgress }}%</span>
      </div>
      <div class="h-1 bg-stone-100 dark:bg-stone-800 rounded-full overflow-hidden">
        <div class="h-full bg-teal-500 transition-all duration-200 rounded-full"
             :style="{ width: store.uploadProgress + '%' }" />
      </div>
    </div>

    <!-- Indexing progress -->
    <div v-if="store.isIndexing" class="space-y-1.5">
      <div class="flex justify-between text-xs text-stone-500 dark:text-stone-400">
        <span>Indexing chunks…</span><span>{{ store.indexingProgress }}%</span>
      </div>
      <div class="h-1 bg-stone-100 dark:bg-stone-800 rounded-full overflow-hidden">
        <div class="h-full bg-emerald-500 transition-all duration-100 rounded-full"
             :style="{ width: store.indexingProgress + '%' }" />
      </div>
    </div>

    <!-- Status message -->
    <div v-if="store.uploadResult"
      class="text-xs rounded-xl px-3 py-2.5"
      :class="store.uploadResult.error
        ? 'bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-900/40'
        : 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/40'"
    >
      <div v-if="store.uploadResult.error" class="flex items-start justify-between gap-2">
        <span>✗ {{ store.uploadResult.error }}</span>
        <button @click="store.resetUploadResult()" class="shrink-0 opacity-60 hover:opacity-100 text-base leading-none">×</button>
      </div>
      <span v-else>
        ✓ Indexed <strong>{{ store.uploadResult.file_name }}</strong>
        — {{ store.uploadResult.chunks_indexed }} chunks
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRagStore } from '../stores/rag'

const store = useRagStore()
const isDragging = ref(false)
const accept = '.pdf,.txt,.md,.docx'

async function handleFile(file) {
  if (!file) return
  store.resetUploadResult()
  try {
    await store.uploadDocument(file)
    setTimeout(() => { store.resetUploadResult() }, 5000)
  } catch {}
}

function onFileChange(e) { handleFile(e.target.files[0]) }
function onDrop(e) { isDragging.value = false; handleFile(e.dataTransfer.files[0]) }
</script>

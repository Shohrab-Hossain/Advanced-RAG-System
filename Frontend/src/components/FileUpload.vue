<template>
  <div class="card space-y-4">
    <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">Upload Document</h2>

    <!-- Drop zone -->
    <div
      class="relative border-2 border-dashed rounded-lg p-5 text-center transition-colors duration-150 cursor-pointer"
      :class="[
        isDragging ? 'border-brand-500 bg-brand-900/20' : 'border-slate-700 hover:border-slate-600',
        (store.uploading || store.isIndexing) ? 'pointer-events-none opacity-60' : '',
      ]"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="$refs.fileInput.click()"
    >
      <input ref="fileInput" type="file" class="hidden" :accept="accept" @change="onFileChange" />
      <div class="text-3xl mb-1">📄</div>
      <p class="text-sm text-slate-300 font-medium">Drop a file or click to browse</p>
      <p class="text-xs text-slate-500 mt-0.5">PDF · DOCX · TXT · Markdown</p>
    </div>

    <!-- Phase 1: Upload progress -->
    <div v-if="store.uploading" class="space-y-1">
      <div class="flex justify-between text-xs text-slate-400">
        <span>Uploading…</span>
        <span>{{ store.uploadProgress }}%</span>
      </div>
      <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          class="h-full bg-brand-500 transition-all duration-200 rounded-full"
          :style="{ width: store.uploadProgress + '%' }"
        />
      </div>
    </div>

    <!-- Phase 2: Indexing progress -->
    <div v-if="store.isIndexing" class="space-y-1">
      <div class="flex justify-between text-xs text-slate-400">
        <span>Indexing (vectors · BM25 · graph)…</span>
        <span>{{ store.indexingProgress }}%</span>
      </div>
      <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          class="h-full bg-emerald-500 transition-all duration-100 rounded-full"
          :style="{ width: store.indexingProgress + '%' }"
        />
      </div>
    </div>

    <!-- Status message -->
    <div v-if="uploadResult" class="text-xs rounded-lg px-3 py-2"
      :class="uploadResult.error ? 'bg-red-900/40 text-red-400' : 'bg-green-900/40 text-green-400'">
      <div v-if="uploadResult.error" class="flex items-start justify-between gap-2">
        <span>✗ {{ uploadResult.error }}</span>
        <button @click="uploadResult = null" class="shrink-0 opacity-60 hover:opacity-100 text-base leading-none">×</button>
      </div>
      <span v-else>✓ Indexed <strong>{{ uploadResult.file_name }}</strong> — {{ uploadResult.chunks_indexed }} chunks</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRagStore } from '../stores/rag'

const store = useRagStore()
const isDragging = ref(false)
const uploadResult = ref(null)
const accept = '.pdf,.txt,.md,.docx'

async function handleFile(file) {
  if (!file) return
  uploadResult.value = null
  try {
    const result = await store.uploadDocument(file)
    uploadResult.value = result
    setTimeout(() => { uploadResult.value = null }, 5000)
  } catch (e) {
    uploadResult.value = { error: e.response?.data?.error || e.message }
  }
}

function onFileChange(e) { handleFile(e.target.files[0]) }
function onDrop(e) {
  isDragging.value = false
  handleFile(e.dataTransfer.files[0])
}
</script>

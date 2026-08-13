/**
 * Pinia Store — Knowledge Base State
 * -----------------------------------
 * State for the ingestion capability:
 *   - Document index stats (vector / BM25 / graph counts)
 *   - The knowledge-base registry
 *   - Upload + indexing progress for the current file
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { uploadFile, getDocuments, clearDocuments, getKnowledgeBases, deleteKnowledgeBase } from './kbApi'

export const useKbStore = defineStore('knowledgeBase', () => {
  // ── Document index ──────────────────────────────────────────────────────────
  const indexStats = ref({ vector_count: 0, bm25_count: 0, graph: {} })
  const knowledgeBases = ref([])
  const uploading = ref(false)
  const uploadProgress = ref(0)    // 0-100: file transfer
  const indexingProgress = ref(0)  // 0-100: server-side indexing phase
  const isIndexing = ref(false)
  const uploadQueueCurrent = ref(0)   // which file in a batch (1-based)
  const uploadQueueTotal = ref(0)     // total files in current batch
  // keep track of the last upload result so it can be cleared by other actions
  const uploadResult = ref(null)

  // ── Computed ─────────────────────────────────────────────────────────────────
  const hasDocuments = computed(() => indexStats.value.vector_count > 0)

  // ── Actions ──────────────────────────────────────────────────────────────────

  async function uploadDocument(file, { queueCurrent = 1, queueTotal = 1 } = {}) {
    uploading.value = true
    uploadProgress.value = 0
    isIndexing.value = false
    indexingProgress.value = 0
    uploadQueueCurrent.value = queueCurrent
    uploadQueueTotal.value = queueTotal
    uploadResult.value = null
    try {
      // Phase 1: file transfer — XHR progress callback
      const result = await uploadFile(file, (pct) => { uploadProgress.value = pct })
      // Phase 2: indexing — start immediately, no gap
      isIndexing.value = true
      uploading.value = false
      await _animateIndexing()
      isIndexing.value = false
      indexingProgress.value = 100
      await refreshStats()
      await fetchKnowledgeBases()
      uploadResult.value = result
      return result
    } catch (err) {
      uploadResult.value = { error: err.response?.data?.error || err.message }
      throw err
    } finally {
      uploading.value = false
      isIndexing.value = false
    }
  }

  function _animateIndexing() {
    return new Promise((resolve) => {
      indexingProgress.value = 0
      const step = () => {
        // Ease toward 95 quickly, hold there until resolved
        if (indexingProgress.value < 95) {
          indexingProgress.value = Math.min(95, indexingProgress.value + 5)
          setTimeout(step, 80)
        } else {
          resolve()
        }
      }
      step()
    })
  }

  async function refreshStats() {
    try {
      indexStats.value = await getDocuments()
    } catch { /* ignore */ }
  }

  async function fetchKnowledgeBases() {
    try {
      const data = await getKnowledgeBases()
      knowledgeBases.value = data.knowledge_bases || []
    } catch { /* ignore */ }
  }

  async function removeKnowledgeBase(fileHash) {
    // clear any prior upload information so user can start fresh
    resetUploadResult()
    await deleteKnowledgeBase(fileHash)
    await fetchKnowledgeBases()
    await refreshStats()
  }

  async function clearIndex() {
    await clearDocuments()
    knowledgeBases.value = []
    await refreshStats()
    resetUploadResult()
  }

  function resetUploadResult() {
    uploadResult.value = null
  }

  return {
    // document index
    indexStats, knowledgeBases,
    uploading, uploadProgress, indexingProgress, isIndexing,
    uploadQueueCurrent, uploadQueueTotal, uploadResult,
    // computed
    hasDocuments,
    // actions
    uploadDocument, refreshStats, fetchKnowledgeBases,
    removeKnowledgeBase, clearIndex, resetUploadResult,
  }
})

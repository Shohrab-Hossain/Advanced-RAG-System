<template>
  <!-- ── History overlay backdrop ─────────────────────────────── -->
  <transition name="backdrop">
    <div v-if="open"
      class="fixed inset-0 z-30 bg-black/20 dark:bg-black/40 backdrop-blur-[2px]"
      @click="$emit('close')" />
  </transition>

  <!-- ── History Sidebar — aligned to content left edge ─────── -->
  <!-- Outer wrapper mirrors the page layout so left-0 = content start -->
  <div class="fixed top-14 inset-x-0 bottom-0 z-40 pointer-events-none">
    <div class="max-w-7xl mx-auto h-full relative">
      <transition name="sidebar">
        <aside v-if="open"
          class="absolute left-0 top-0 bottom-0 w-72 pointer-events-auto flex flex-col
                 bg-white dark:bg-[#1C1917]
                 border-r border-stone-200 dark:border-white/[0.07]
                 shadow-[4px_0_24px_0_rgb(0,0,0,0.10)] dark:shadow-[4px_0_24px_0_rgb(0,0,0,0.4)]">

          <!-- Header -->
          <div class="flex items-center justify-between px-4 py-3
                      border-b border-stone-100 dark:border-white/[0.05] flex-shrink-0">
            <span class="section-label section-label-indigo">Chat History</span>
            <div class="flex items-center gap-3">
              <button v-if="store.chatHistory.length" @click="confirmClearAll"
                class="text-[10px] text-red-400 hover:text-red-600 dark:hover:text-red-400
                       transition-colors font-medium">
                Clear all
              </button>
              <button @click="$emit('close')"
                class="text-slate-400 hover:text-stone-700 dark:text-stone-500 dark:hover:text-slate-300
                       transition-colors text-sm leading-none">
                ✕
              </button>
            </div>
          </div>

          <!-- Empty state -->
          <div v-if="!store.chatHistory.length"
            class="flex flex-col items-center justify-center flex-1 px-4 py-10 text-center">
            <span class="text-3xl mb-3 opacity-30">🕐</span>
            <p class="text-xs font-medium text-slate-400 dark:text-slate-600">No history yet</p>
            <p class="text-[11px] text-slate-300 dark:text-stone-700 mt-1">
              Your chats will appear here
            </p>
          </div>

          <!-- List -->
          <div v-else class="flex-1 overflow-y-auto p-2 space-y-0.5">
            <div v-for="item in store.chatHistory" :key="item.id"
              class="group relative flex items-start gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer
                     transition-all duration-150"
              :class="activeHistoryId === item.id
                ? 'bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30'
                : 'border border-transparent hover:bg-stone-50 dark:hover:bg-white/[0.04] hover:border-stone-200 dark:hover:border-white/[0.07]'"
              @click="loadHistory(item)">
              <span class="text-xs flex-shrink-0 mt-0.5 opacity-50">💬</span>
              <div class="flex-1 min-w-0">
                <p class="text-[11px] font-medium leading-snug line-clamp-2"
                   :class="activeHistoryId === item.id
                     ? 'text-emerald-700 dark:text-emerald-300'
                     : 'text-stone-700 dark:text-slate-300'">
                  {{ item.query }}
                </p>
                <p class="text-[10px] text-slate-400 dark:text-slate-600 mt-1">
                  {{ formatTime(item.timestamp) }}
                </p>
              </div>
              <button
                class="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity
                       text-slate-300 hover:text-red-500 dark:text-slate-600 dark:hover:text-red-400
                       text-xs leading-none mt-0.5 p-0.5"
                @click.stop="confirmDelete(item.id)" title="Delete">
                ✕
              </button>
            </div>
          </div>
        </aside>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRagStore } from '../../../../store/ragStore'
import { useUiStore } from '../../../../store'
import { formatTime } from './chatHistorySidebar'

defineProps({
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const store = useRagStore()
const ui = useUiStore()
const activeHistoryId = ref(null)

// When a new query completes and is saved, highlight it in the history list
watch(() => store.chatHistory[0]?.id, (newId) => {
  if (newId && !store.isHistoryResult) {
    activeHistoryId.value = newId
  }
})

function loadHistory(item) {
  activeHistoryId.value = item.id
  store.loadHistoryItem(item)
  emit('close')
}

async function confirmDelete(id) {
  const ok = await ui.confirm('Delete this chat from history?', {
    danger: true, confirmText: 'Yes, delete it', cancelText: 'No, keep it',
  })
  if (!ok) return
  store.deleteHistoryItem(id)
  if (activeHistoryId.value === id) activeHistoryId.value = null
}

async function confirmClearAll() {
  const ok = await ui.confirm('Delete all chat history? This cannot be undone.', {
    danger: true, confirmText: 'Yes, delete all', cancelText: 'No, keep them',
  })
  if (!ok) return
  store.clearChatHistory()
  activeHistoryId.value = null
}
</script>

<style scoped src="./chatHistorySidebar.css"></style>

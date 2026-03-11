<template>
  <div class="card space-y-4">
    <div class="flex items-center justify-between">
      <p class="section-label section-label-muted">LLM Provider</p>
      <button @click="refresh" :disabled="checking"
        class="text-[11px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300
               transition-colors disabled:opacity-40 flex items-center gap-1">
        <span :class="checking ? 'animate-spin inline-block' : ''">↻</span>
        {{ checking ? 'Checking…' : 'Refresh' }}
      </button>
    </div>

    <!-- Provider cards -->
    <div class="grid grid-cols-2 gap-2">
      <button @click="select('openai')"
        class="flex flex-col items-start gap-2 p-3 rounded-xl border-2
               transition-all duration-150 cursor-pointer text-left"
        :class="store.llmProvider === 'openai'
          ? 'border-emerald-500 dark:border-emerald-400 bg-emerald-50/60 dark:bg-emerald-500/[0.07]'
          : 'border-stone-200 dark:border-white/[0.07] bg-white dark:bg-white/[0.02] hover:border-slate-300 dark:hover:border-white/[0.12]'"
      >
        <div class="flex items-center gap-2 w-full">
          <span class="text-base leading-none">🤖</span>
          <span class="text-xs font-semibold text-stone-800 dark:text-stone-200">OpenAI</span>
          <span v-if="store.llmProvider === 'openai'"
            class="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400" />
        </div>
        <span class="text-[10px] text-slate-400 font-mono truncate w-full">
          {{ activeOpenaiModel || openaiInfo.model || 'gpt-4o-mini' }}
        </span>
        <div class="flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
            :class="openaiInfo.available ? 'bg-emerald-500' : 'bg-teal-400'" />
          <span class="text-[10px]"
            :class="openaiInfo.available ? 'text-emerald-600 dark:text-emerald-400' : 'text-teal-600 dark:text-teal-400'">
            {{ openaiInfo.available ? 'Key set' : 'No key' }}
          </span>
        </div>
      </button>

      <button @click="select('ollama')"
        class="flex flex-col items-start gap-2 p-3 rounded-xl border-2
               transition-all duration-150 cursor-pointer text-left"
        :class="store.llmProvider === 'ollama'
          ? 'border-emerald-500 dark:border-emerald-400 bg-emerald-50/60 dark:bg-emerald-500/[0.07]'
          : 'border-stone-200 dark:border-white/[0.07] bg-white dark:bg-white/[0.02] hover:border-slate-300 dark:hover:border-white/[0.12]'"
      >
        <div class="flex items-center gap-2 w-full">
          <span class="text-base leading-none">🦙</span>
          <span class="text-xs font-semibold text-stone-800 dark:text-stone-200">Local</span>
          <span v-if="store.llmProvider === 'ollama'"
            class="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400" />
        </div>
        <span v-if="activeOllamaModel"
          class="text-[10px] text-slate-400 font-mono truncate w-full">{{ activeOllamaModel }}</span>
        <span v-else class="text-[10px] text-slate-300 dark:text-stone-700 italic w-full">not checked</span>
        <div class="flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
            :class="ollamaInfo.available ? 'bg-emerald-500' : 'bg-red-500 animate-pulse'" />
          <span class="text-[10px]"
            :class="ollamaInfo.available ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'">
            {{ ollamaInfo.available ? 'Running' : 'Offline' }}
          </span>
        </div>
      </button>
    </div>

    <!-- Ollama offline notice -->
    <div v-if="!ollamaInfo.available && ollamaError"
      class="text-[10px] rounded-xl px-3 py-2.5 space-y-1
             bg-red-50 dark:bg-red-500/[0.07]
             border border-red-200 dark:border-red-500/20
             text-red-700 dark:text-red-400">
      <p class="font-semibold">Cannot reach Ollama</p>
      <p class="opacity-70 break-all">{{ ollamaError }}</p>
      <p class="text-stone-500 dark:text-slate-400">
        Run: <code class="font-mono">ollama serve</code>
        then: <code class="font-mono">ollama pull {{ ollamaInfo.model || 'llama3.2' }}</code>
      </p>
    </div>

    <!-- OpenAI model picker -->
    <div v-if="store.llmProvider === 'openai' && openaiInfo.available && openaiModels.length" class="space-y-2">
      <p class="section-label section-label-muted">Model</p>
      <div class="space-y-1">
        <button v-for="m in openaiModels" :key="m"
          @click="store.setOpenaiModel(m)"
          class="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl border
                 transition-all duration-150 text-left"
          :class="m === activeOpenaiModel
            ? 'border-emerald-300 dark:border-emerald-500/50 bg-emerald-50 dark:bg-emerald-500/[0.08]'
            : 'border-stone-200 dark:border-white/[0.06] hover:bg-stone-50 dark:hover:bg-white/[0.04]'"
        >
          <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
            :class="m === activeOpenaiModel ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-stone-700'" />
          <span class="text-xs font-mono truncate"
            :class="m === activeOpenaiModel ? 'text-emerald-700 dark:text-emerald-300 font-semibold' : 'text-stone-500 dark:text-slate-400'">
            {{ m }}
          </span>
          <span v-if="m === activeOpenaiModel"
            class="ml-auto text-[9px] px-1.5 py-0.5 rounded
                   bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-medium flex-shrink-0">
            active
          </span>
        </button>
      </div>
    </div>

    <!-- Ollama model picker -->
    <div v-if="store.llmProvider === 'ollama' && ollamaInfo.available" class="space-y-2">
      <p class="section-label section-label-muted">Model</p>
      <div v-if="ollamaModels.length" class="space-y-1">
        <button v-for="m in ollamaModels" :key="m"
          @click="store.setOllamaModel(m)"
          class="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl border
                 transition-all duration-150 text-left"
          :class="m === activeOllamaModel
            ? 'border-emerald-300 dark:border-emerald-500/50 bg-emerald-50 dark:bg-emerald-500/[0.08]'
            : 'border-stone-200 dark:border-white/[0.06] hover:bg-stone-50 dark:hover:bg-white/[0.04]'"
        >
          <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
            :class="m === activeOllamaModel ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-stone-700'" />
          <span class="text-xs font-mono truncate"
            :class="m === activeOllamaModel ? 'text-emerald-700 dark:text-emerald-300 font-semibold' : 'text-stone-500 dark:text-slate-400'">
            {{ m }}
          </span>
          <span v-if="m === activeOllamaModel"
            class="ml-auto text-[9px] px-1.5 py-0.5 rounded
                   bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-medium flex-shrink-0">
            active
          </span>
        </button>
      </div>
      <p v-else class="text-[10px] text-slate-400 dark:text-stone-500 italic">
        No models found — run <code class="font-mono not-italic">ollama pull llama3.2</code>
      </p>
    </div>

    <!-- Footer -->
    <div class="flex items-center gap-2 pt-3 border-t border-stone-100 dark:border-white/[0.05]">
      <span class="text-[10px] text-slate-400 dark:text-slate-600">Active</span>
      <span class="text-[11px] font-mono truncate text-slate-600 dark:text-slate-300">
        {{ store.llmProvider === 'ollama'
            ? (activeOllamaModel ? '🦙 ' + activeOllamaModel : '🦙 —')
            : (activeOpenaiModel ? '🤖 ' + activeOpenaiModel : '🤖 —') }}
      </span>
      <span v-if="store.llmProvider === 'ollama' && !ollamaInfo.available"
        class="ml-auto text-[10px] text-teal-500 flex-shrink-0">⚠ offline</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRagStore } from '../stores/rag'

const store = useRagStore()
const checking = ref(false)

const openaiInfo   = computed(() => store.availableProviders.openai || { available: false })
const ollamaInfo   = computed(() => store.availableProviders.ollama || { available: false })
const openaiModels = computed(() => openaiInfo.value.models ?? [])
const ollamaModels = computed(() => ollamaInfo.value.models ?? [])
const ollamaError  = computed(() => ollamaInfo.value.error ?? '')

const activeOpenaiModel = computed(() =>
  store.openaiModel || openaiInfo.value.model || openaiModels.value[0] || null
)
const activeOllamaModel = computed(() =>
  store.ollamaModel || ollamaModels.value[0] || ollamaInfo.value.model || null
)

function select(p) {
  store.llmProvider = p
  if (p === 'ollama' && !store.ollamaModel && ollamaModels.value.length) store.setOllamaModel(ollamaModels.value[0])
  if (p === 'openai' && !store.openaiModel && openaiInfo.value.model) store.setOpenaiModel(openaiInfo.value.model)
}

async function refresh() { checking.value = true; await store.fetchProviders(); checking.value = false }

let pollTimer = null
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => { if (!ollamaInfo.value.available) await store.fetchProviders() }, 15_000)
}
function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

onMounted(async () => { await store.fetchProviders(); startPolling() })
onUnmounted(stopPolling)
</script>

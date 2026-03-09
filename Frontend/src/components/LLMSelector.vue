<template>
  <div class="card space-y-3">
    <!-- Header + refresh -->
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">LLM Provider</h2>
      <button
        @click="refresh"
        :disabled="checking"
        class="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-300 transition-colors disabled:opacity-40"
        title="Re-check provider status"
      >
        <span :class="checking ? 'animate-spin' : ''">↻</span>
        {{ checking ? 'Checking…' : 'Refresh' }}
      </button>
    </div>

    <!-- Provider buttons -->
    <div class="grid grid-cols-2 gap-2">

      <!-- OpenAI -->
      <button
        @click="select('openai')"
        class="flex flex-col items-start gap-1 p-3 rounded-lg border-2 transition-all duration-150 cursor-pointer"
        :class="store.llmProvider === 'openai'
          ? 'border-brand-600 bg-brand-900/30'
          : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'"
      >
        <div class="flex items-center gap-2 w-full">
          <span class="text-base">🤖</span>
          <span class="text-sm font-semibold text-slate-200">OpenAI</span>
          <span v-if="store.llmProvider === 'openai'"
            class="ml-auto w-2 h-2 rounded-full bg-brand-400" />
        </div>
        <span class="text-[10px] text-slate-500 font-mono truncate w-full">
          {{ openaiInfo.model || 'gpt-4o-mini' }}
        </span>
        <div class="flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full"
            :class="openaiInfo.available ? 'bg-brand-400' : 'bg-amber-500'" />
          <span class="text-[10px]"
            :class="openaiInfo.available ? 'text-brand-400' : 'text-amber-400'">
            {{ openaiInfo.available ? 'Key set' : 'No API key' }}
          </span>
        </div>
      </button>

      <!-- Ollama -->
      <button
        @click="select('ollama')"
        class="flex flex-col items-start gap-1 p-3 rounded-lg border-2 transition-all duration-150 cursor-pointer"
        :class="store.llmProvider === 'ollama'
          ? 'border-emerald-600 bg-emerald-900/30'
          : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'"
      >
        <div class="flex items-center gap-2 w-full">
          <span class="text-base">🦙</span>
          <span class="text-sm font-semibold text-slate-200">Local</span>
          <span v-if="store.llmProvider === 'ollama'"
            class="ml-auto w-2 h-2 rounded-full bg-emerald-400" />
        </div>
        <span class="text-[10px] text-slate-500 font-mono truncate w-full">
          {{ ollamaInfo.model || 'llama3.2:latest' }}
        </span>
        <div class="flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full"
            :class="ollamaInfo.available ? 'bg-emerald-400' : 'bg-red-500 animate-pulse'" />
          <span class="text-[10px]"
            :class="ollamaInfo.available ? 'text-emerald-400' : 'text-red-400'">
            {{ ollamaInfo.available ? 'Running' : 'Offline' }}
          </span>
        </div>
      </button>
    </div>

    <!-- Ollama offline detail -->
    <div v-if="!ollamaInfo.available && ollamaError"
      class="text-[10px] bg-red-950/40 border border-red-900/50 rounded-lg px-3 py-2 text-red-400 space-y-1">
      <p class="font-semibold">Cannot reach Ollama</p>
      <p class="text-red-500 break-all">{{ ollamaError }}</p>
      <p class="text-slate-500 mt-1">
        Make sure Ollama is running:
        <code class="text-slate-400">ollama serve</code>
        and the model is pulled:
        <code class="text-slate-400">ollama pull {{ ollamaInfo.model || 'llama3.2' }}</code>
      </p>
    </div>

    <!-- Ollama model picker (when multiple models available) -->
    <div v-if="ollamaInfo.available && ollamaModels.length > 1" class="space-y-1">
      <p class="text-[10px] text-slate-600 uppercase tracking-wider">Available models</p>
      <div class="flex flex-wrap gap-1">
        <span
          v-for="m in ollamaModels" :key="m"
          @click="store.setOllamaModel(m)"
          class="text-[10px] font-mono px-1.5 py-0.5 rounded cursor-pointer transition-colors"
          :class="m === store.ollamaModel
            ? 'bg-emerald-900/60 text-emerald-300'
            : 'bg-slate-800 text-slate-500 hover:text-slate-300'"
        >{{ m }}</span>
      </div>
    </div>

    <!-- Active provider footer -->
    <div class="flex items-center gap-2 pt-1 border-t border-slate-800">
      <span class="text-[10px] text-slate-600">Active:</span>
      <span class="text-[11px] font-mono"
        :class="store.llmProvider === 'ollama' ? 'text-emerald-300' : 'text-brand-300'">
        {{ store.llmProvider === 'ollama'
            ? '🦙 ' + (store.ollamaModel || ollamaInfo.model || 'llama3.2:latest')
            : '🤖 ' + (openaiInfo.model || 'gpt-4o-mini') }}
      </span>
      <!-- Warn if selected Ollama but it's offline -->
      <span v-if="store.llmProvider === 'ollama' && !ollamaInfo.available"
        class="ml-auto text-[10px] text-amber-400">⚠ offline</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRagStore } from '../stores/rag'

const store = useRagStore()
const checking = ref(false)

const openaiInfo = computed(() => store.availableProviders.openai  || { available: false })
const ollamaInfo = computed(() => store.availableProviders.ollama  || { available: false })
const ollamaModels = computed(() => ollamaInfo.value.models ?? [])
const ollamaError  = computed(() => ollamaInfo.value.error ?? '')

function select(p) {
  store.llmProvider = p   // always allow selection — backend will error if truly down
}

async function refresh() {
  checking.value = true
  await store.fetchProviders()
  checking.value = false
}

// Auto-poll every 15 s while Ollama is offline so it lights up automatically
// when the user starts it after loading the page
let pollTimer = null

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!ollamaInfo.value.available) {
      await store.fetchProviders()
    }
  }, 15_000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(async () => {
  await store.fetchProviders()
  startPolling()
})

onUnmounted(stopPolling)
</script>

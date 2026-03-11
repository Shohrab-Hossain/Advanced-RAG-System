<template>
  <main class="max-w-6xl mx-auto px-4 py-8 space-y-8">

    <!-- Page header -->
    <div class="flex items-start gap-4 pb-5 border-b border-stone-200 dark:border-white/[0.06]">
      <div class="w-10 h-10 rounded-xl bg-teal-50 dark:bg-teal-500/10
                  flex items-center justify-center text-xl flex-shrink-0 mt-0.5">⚙️</div>
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-stone-900 dark:text-stone-100">Configuration</h1>
        <p class="text-sm text-stone-500 dark:text-slate-400 mt-1 leading-relaxed max-w-2xl">
          Select your LLM provider and model. OpenAI requires an API key configured in the backend
          <code class="font-mono text-xs bg-stone-100 dark:bg-white/[0.07] px-1.5 py-0.5 rounded">.env</code>
          file. Ollama runs entirely on your machine — no data sent externally.
        </p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 items-start">

      <!-- LLM Selector -->
      <LLMSelector />

      <!-- Provider info -->
      <div class="space-y-4">

        <!-- OpenAI -->
        <div class="card">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 rounded-xl bg-stone-100 dark:bg-white/[0.07]
                        flex items-center justify-center text-xl flex-shrink-0">🤖</div>
            <div class="flex-1 min-w-0">
              <h3 class="text-sm font-semibold text-stone-800 dark:text-stone-200">OpenAI</h3>
              <p class="text-xs text-slate-400 dark:text-stone-500">Cloud-hosted · API key required</p>
            </div>
            <span class="text-[10px] font-medium px-2.5 py-1 rounded-full flex-shrink-0 border"
              :class="openaiAvailable
                ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                : 'bg-teal-50 dark:bg-teal-500/10 border-teal-200 dark:border-teal-500/20 text-teal-700 dark:text-teal-400'">
              {{ openaiAvailable ? '✓ Ready' : '⚠ No key' }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs mb-4">
            <div v-for="item in openaiFeatures" :key="item.text"
              class="flex items-start gap-2 p-2.5 rounded-lg
                     bg-stone-50 dark:bg-white/[0.03]
                     border border-stone-100 dark:border-white/[0.05]">
              <span class="flex-shrink-0 mt-0.5" :class="item.positive ? 'text-emerald-500' : 'text-slate-300 dark:text-slate-600'">
                {{ item.positive ? '✓' : '–' }}
              </span>
              <span class="text-stone-500 dark:text-slate-400 leading-relaxed">{{ item.text }}</span>
            </div>
          </div>

          <div v-if="!openaiAvailable"
            class="rounded-xl px-4 py-3 text-[11px]
                   bg-teal-50 dark:bg-teal-500/[0.07]
                   border border-teal-200 dark:border-teal-500/20
                   text-teal-700 dark:text-teal-400">
            <p class="font-semibold mb-1">API key not configured</p>
            <p>Add <code class="font-mono bg-teal-100 dark:bg-teal-500/20 px-1 rounded">OPENAI_API_KEY=sk-...</code>
               to <code class="font-mono bg-teal-100 dark:bg-teal-500/20 px-1 rounded">Backend/.env</code>
               and restart the server.</p>
          </div>
        </div>

        <!-- Ollama -->
        <div class="card">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 rounded-xl bg-stone-100 dark:bg-white/[0.07]
                        flex items-center justify-center text-xl flex-shrink-0">🦙</div>
            <div class="flex-1 min-w-0">
              <h3 class="text-sm font-semibold text-stone-800 dark:text-stone-200">Local (Ollama)</h3>
              <p class="text-xs text-slate-400 dark:text-stone-500">On-device · No API key needed</p>
            </div>
            <span class="text-[10px] font-medium px-2.5 py-1 rounded-full flex-shrink-0 border"
              :class="ollamaAvailable
                ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                : 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/20 text-red-700 dark:text-red-400'">
              {{ ollamaAvailable ? '✓ Running' : '✗ Offline' }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs mb-4">
            <div v-for="item in ollamaFeatures" :key="item.text"
              class="flex items-start gap-2 p-2.5 rounded-lg
                     bg-stone-50 dark:bg-white/[0.03]
                     border border-stone-100 dark:border-white/[0.05]">
              <span class="flex-shrink-0 mt-0.5" :class="item.positive ? 'text-emerald-500' : 'text-slate-300 dark:text-slate-600'">
                {{ item.positive ? '✓' : '–' }}
              </span>
              <span class="text-stone-500 dark:text-slate-400 leading-relaxed">{{ item.text }}</span>
            </div>
          </div>

          <div v-if="!ollamaAvailable"
            class="rounded-xl overflow-hidden border border-stone-200 dark:border-white/[0.07]">
            <div class="px-4 py-2 bg-stone-100 dark:bg-white/[0.05]
                        text-[10px] font-semibold text-stone-500 dark:text-slate-400 uppercase tracking-wider">
              Quick Start
            </div>
            <div class="px-4 py-3 bg-[#FAFAF9] dark:bg-[#0C0A09] font-mono text-[11px] space-y-1
                        text-slate-600 dark:text-slate-400">
              <p class="text-slate-400 dark:text-slate-600"># Install from https://ollama.com</p>
              <p>ollama serve</p>
              <p>ollama pull llama3.2</p>
            </div>
          </div>
        </div>

      </div>
    </div>

  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRagStore } from '../stores/rag'
import LLMSelector from '../components/LLMSelector.vue'

const store = useRagStore()

const openaiAvailable = computed(() => store.availableProviders.openai?.available ?? false)
const ollamaAvailable = computed(() => store.availableProviders.ollama?.available ?? false)

const openaiFeatures = [
  { text: 'Best reasoning and instruction following', positive: true },
  { text: 'gpt-4o-mini is fast and cost-effective', positive: true },
  { text: 'Requires OPENAI_API_KEY in backend', positive: false },
  { text: 'Data is sent to OpenAI servers', positive: false },
]

const ollamaFeatures = [
  { text: 'Fully private — no data leaves your machine', positive: true },
  { text: 'No API costs — unlimited queries', positive: true },
  { text: 'Requires Ollama running locally', positive: false },
  { text: 'Quality varies by model size (7B+ rec.)', positive: false },
]
</script>

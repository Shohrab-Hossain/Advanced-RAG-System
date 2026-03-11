<template>
  <header class="sticky top-0 z-20
                 bg-white/90 dark:bg-[#0C0A09]/95
                 border-b border-stone-200 dark:border-white/[0.06]
                 backdrop-blur-md transition-colors duration-200">
    <div class="max-w-7xl mx-auto px-4 h-14 flex items-center">

      <!-- Logo (left) -->
      <RouterLink to="/" class="flex items-center gap-2.5 flex-shrink-0 group">
        <div class="w-8 h-8 rounded-xl flex-shrink-0 overflow-hidden
                    bg-gradient-to-br from-emerald-500 via-emerald-600 to-teal-600
                    flex items-center justify-center
                    group-hover:shadow-[0_0_12px_2px_rgba(99,102,241,0.4)]
                    transition-shadow duration-200">
          <span class="text-sm leading-none">🧬</span>
        </div>
        <div class="hidden sm:block leading-none">
          <span class="text-[13px] font-semibold text-stone-800 dark:text-stone-100 tracking-tight">
            adRAG
          </span>
        </div>
      </RouterLink>

      <!-- Nav links (center) -->
      <nav class="flex-1 flex items-center justify-center gap-1">
        <RouterLink
          v-for="link in navLinks" :key="link.to"
          :to="link.to"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium
                 transition-all duration-150 select-none"
          :class="isActive(link.to)
            ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
            : 'text-stone-500 dark:text-slate-400 hover:text-stone-800 dark:hover:text-stone-200 hover:bg-stone-100 dark:hover:bg-white/[0.05]'"
        >
          <span class="text-[15px] leading-none">{{ link.icon }}</span>
          <span class="hidden sm:inline">{{ link.label }}</span>
        </RouterLink>
      </nav>

      <!-- Right controls -->
      <div class="flex items-center gap-2 flex-shrink-0">

        <!-- Active model badge — warning when OpenAI key missing -->
        <div v-if="store.llmProvider === 'openai' && !(store.availableProviders.openai?.available)"
          class="hidden md:flex items-center gap-1.5 text-[11px] font-mono
                 px-2.5 py-1 rounded-lg
                 bg-amber-50 dark:bg-amber-500/[0.08]
                 text-amber-600 dark:text-amber-400
                 border border-amber-200 dark:border-amber-500/25 max-w-[160px]">
          <span class="flex-shrink-0 text-xs">⚠</span>
          <span class="truncate">No API key</span>
        </div>
        <div v-else
          class="hidden md:flex items-center gap-1.5 text-[11px] font-mono
                 px-2.5 py-1 rounded-lg
                 bg-stone-100 dark:bg-white/[0.05]
                 text-slate-600 dark:text-slate-400
                 border border-stone-200 dark:border-white/[0.07] max-w-[150px]">
          <span class="flex-shrink-0 text-xs">{{ store.llmProvider === 'ollama' ? '🦙' : '🤖' }}</span>
          <span class="truncate">{{ activeModel ?? '—' }}</span>
        </div>

        <!-- Connection dot -->
        <div class="flex items-center gap-1.5 px-2">
          <span class="relative flex h-2 w-2">
            <span v-if="connected"
              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
            <span class="relative inline-flex rounded-full h-2 w-2"
              :class="connected ? 'bg-emerald-500' : 'bg-slate-400'" />
          </span>
          <span class="hidden lg:inline text-[11px] text-slate-400 dark:text-stone-500">
            {{ connected ? 'Connected' : 'Offline' }}
          </span>
        </div>

        <!-- Divider -->
        <div class="h-4 w-px bg-stone-200 dark:bg-white/[0.08]" />

        <!-- Theme toggle -->
        <button
          @click="ui.toggleTheme()"
          class="w-8 h-8 flex items-center justify-center rounded-lg
                 text-slate-400 hover:text-stone-700 dark:text-stone-500 dark:hover:text-stone-200
                 hover:bg-stone-100 dark:hover:bg-white/[0.06]
                 transition-all duration-150"
          :title="ui.theme === 'dark' ? 'Light mode' : 'Dark mode'"
        >
          <svg v-if="ui.theme === 'dark'" xmlns="http://www.w3.org/2000/svg"
               class="w-[15px] h-[15px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707
                 M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 7a5 5 0 100 10 5 5 0 000-10z" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg"
               class="w-[15px] h-[15px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
          </svg>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRagStore } from '../stores/rag'
import { useUiStore } from '../stores/ui'
import { healthCheck } from '../services/api'

const store = useRagStore()
const ui = useUiStore()
const route = useRoute()
const connected = ref(false)

const navLinks = [
  { to: '/',               icon: '🏠', label: 'Home' },
  { to: '/chat',           icon: '💬', label: 'Chat' },
  { to: '/knowledge-base', icon: '🗂️', label: 'Knowledge Base' },
  { to: '/configuration',  icon: '⚙️', label: 'Configuration' },
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(path + '/')
}

const activeModel = computed(() => {
  if (store.llmProvider === 'ollama') {
    const ollama = store.availableProviders.ollama || {}
    return store.ollamaModel || (ollama.models || [])[0] || ollama.model || null
  }
  const openai = store.availableProviders.openai || {}
  return store.openaiModel || openai.model || null
})

onMounted(async () => {
  try {
    await healthCheck()
    connected.value = true
    await Promise.all([store.refreshStats(), store.fetchProviders(), store.fetchKnowledgeBases()])
  } catch {
    connected.value = false
  }
})
</script>

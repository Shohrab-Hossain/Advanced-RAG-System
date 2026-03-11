<template>
  <div class="min-h-[calc(100vh-56px)] flex flex-col items-center justify-center px-6 sm:px-8 py-16">

    <!-- Hero -->
    <div class="text-center mb-12 animate-fade-in">
      <div class="w-20 h-20 mx-auto mb-6 rounded-3xl
                  bg-gradient-to-br from-emerald-500 via-emerald-600 to-teal-600
                  flex items-center justify-center text-4xl
                  shadow-[0_8px_32px_rgba(99,102,241,0.35)]">
        🧬
      </div>
      <h1 class="text-4xl font-bold tracking-tight text-stone-900 dark:text-stone-100 mb-4">
        adRAG
      </h1>
      <p class="text-base text-stone-500 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed">
        A multi-stage Retrieval-Augmented Generation pipeline that combines
        <span class="text-stone-700 dark:text-slate-300 font-medium">hybrid search</span> (Vector + BM25 + GraphRAG),
        <span class="text-stone-700 dark:text-slate-300 font-medium">cross-encoder reranking</span>, and a
        <span class="text-stone-700 dark:text-slate-300 font-medium">self-reflection agent</span>
        to generate grounded, cited answers from your documents.
      </p>
    </div>

    <!-- Centered nav links -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-2xl mb-14 animate-slide-up">
      <RouterLink to="/chat"
        class="group flex flex-col items-center gap-3 p-6 rounded-2xl
               border border-stone-200 dark:border-white/[0.07]
               bg-white dark:bg-[#1C1917]
               shadow-[0_1px_3px_0_rgb(0,0,0,0.07)] dark:shadow-none
               hover:border-emerald-300 dark:hover:border-emerald-500/40
               hover:shadow-[0_4px_20px_rgba(99,102,241,0.12)]
               transition-all duration-200">
        <span class="text-3xl group-hover:scale-110 transition-transform duration-200">💬</span>
        <div class="text-center">
          <div class="text-sm font-semibold text-stone-800 dark:text-stone-200">Chat</div>
          <div class="text-[11px] text-slate-400 dark:text-stone-500 mt-0.5">Ask questions about your docs</div>
        </div>
      </RouterLink>

      <RouterLink to="/knowledge-base"
        class="group flex flex-col items-center gap-3 p-6 rounded-2xl
               border border-stone-200 dark:border-white/[0.07]
               bg-white dark:bg-[#1C1917]
               shadow-[0_1px_3px_0_rgb(0,0,0,0.07)] dark:shadow-none
               hover:border-emerald-300 dark:hover:border-emerald-500/40
               hover:shadow-[0_4px_20px_rgba(99,102,241,0.12)]
               transition-all duration-200">
        <span class="text-3xl group-hover:scale-110 transition-transform duration-200">🗂️</span>
        <div class="text-center">
          <div class="text-sm font-semibold text-stone-800 dark:text-stone-200">Knowledge Base</div>
          <div class="text-[11px] text-slate-400 dark:text-stone-500 mt-0.5">Upload & manage documents</div>
        </div>
      </RouterLink>

      <RouterLink to="/configuration"
        class="group flex flex-col items-center gap-3 p-6 rounded-2xl
               border border-stone-200 dark:border-white/[0.07]
               bg-white dark:bg-[#1C1917]
               shadow-[0_1px_3px_0_rgb(0,0,0,0.07)] dark:shadow-none
               hover:border-emerald-300 dark:hover:border-emerald-500/40
               hover:shadow-[0_4px_20px_rgba(99,102,241,0.12)]
               transition-all duration-200">
        <span class="text-3xl group-hover:scale-110 transition-transform duration-200">⚙️</span>
        <div class="text-center">
          <div class="text-sm font-semibold text-stone-800 dark:text-stone-200">Configuration</div>
          <div class="text-[11px] text-slate-400 dark:text-stone-500 mt-0.5">Choose LLM provider & model</div>
        </div>
      </RouterLink>
    </div>

    <!-- Pipeline stages -->
    <div class="w-full max-w-3xl">
      <p class="text-center text-[10px] font-semibold uppercase tracking-[0.1em]
                text-slate-400 dark:text-slate-600 mb-4">Pipeline Stages</p>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div v-for="feature in features" :key="feature.label"
          class="flex flex-col items-center gap-2 p-4 rounded-xl
                 bg-white dark:bg-[#1C1917]
                 border border-stone-200/80 dark:border-white/[0.07]
                 shadow-[0_1px_3px_0_rgb(0,0,0,0.05)] dark:shadow-none text-center">
          <span class="text-2xl">{{ feature.icon }}</span>
          <div>
            <div class="text-[11px] font-semibold text-stone-700 dark:text-slate-300">{{ feature.label }}</div>
            <div class="text-[10px] text-slate-400 dark:text-stone-500 mt-0.5 leading-relaxed">{{ feature.desc }}</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
const features = [
  { icon: '🧠', label: 'Self-RAG Planner',       desc: 'Decides if retrieval or web search is needed' },
  { icon: '🔍', label: 'Hybrid Retrieval',        desc: 'Vector + BM25 + GraphRAG in parallel' },
  { icon: '🎯', label: 'Cross-Encoder Reranker',  desc: 'Scores evidence by true relevance' },
  { icon: '✂️', label: 'Context Compressor',      desc: 'Fits top evidence into the LLM window' },
  { icon: '💡', label: 'Reasoning Agent',         desc: 'Generates cited, structured answers' },
  { icon: '🔮', label: 'Self-Reflection',         desc: 'Verifies grounding, retries if needed' },
  { icon: '🌐', label: 'Web Search',              desc: 'DuckDuckGo fallback for live data' },
  { icon: '🗃️', label: 'Knowledge Graph',         desc: 'Entity-relationship traversal (GraphRAG)' },
]
</script>

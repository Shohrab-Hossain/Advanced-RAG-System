<template>
  <!-- File-extension pill (pdf, docx, txt, md …) -->
  <span v-if="info.mode === 'ext'"
    class="inline-flex items-center justify-center rounded-[4px] font-bold uppercase tracking-tighter leading-none text-white select-none flex-shrink-0"
    :style="{
      background: info.color,
      width:  size + 'px',
      height: size + 'px',
      fontSize: Math.max(7, Math.round(size * 0.30)) + 'px',
    }">
    {{ info.label }}
  </span>

  <!-- SVG icon for retrieval source types or unknown files -->
  <svg v-else :width="size" :height="size" viewBox="0 0 24 24" fill="none"
    xmlns="http://www.w3.org/2000/svg" class="flex-shrink-0">

    <!-- 🌐 Web / URL -->
    <template v-if="info.id === 'web'">
      <circle cx="12" cy="12" r="9" :stroke="info.color" stroke-width="1.7"/>
      <path d="M12 3C10.4 5.8 9.5 8.7 9.5 12C9.5 15.3 10.4 18.2 12 21"
        :stroke="info.color" stroke-width="1.5"/>
      <path d="M12 3C13.6 5.8 14.5 8.7 14.5 12C14.5 15.3 13.6 18.2 12 21"
        :stroke="info.color" stroke-width="1.5"/>
      <path d="M3.5 9H20.5M3.5 15H20.5"
        :stroke="info.color" stroke-width="1.5" stroke-linecap="round"/>
    </template>

    <!-- 🗃️ Vector / database -->
    <template v-else-if="info.id === 'vector'">
      <ellipse cx="12" cy="7" rx="7" ry="2.5" :stroke="info.color" stroke-width="1.5"/>
      <path d="M5 7v5c0 1.38 3.13 2.5 7 2.5S19 13.38 19 12V7"
        :stroke="info.color" stroke-width="1.5"/>
      <path d="M5 12v5c0 1.38 3.13 2.5 7 2.5S19 18.38 19 17v-5"
        :stroke="info.color" stroke-width="1.5"/>
    </template>

    <!-- 📝 BM25 / text search -->
    <template v-else-if="info.id === 'bm25'">
      <rect x="4" y="3" width="16" height="18" rx="2" :stroke="info.color" stroke-width="1.5"/>
      <line x1="8" y1="9"  x2="16" y2="9"  :stroke="info.color" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="8" y1="13" x2="16" y2="13" :stroke="info.color" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="8" y1="17" x2="12" y2="17" :stroke="info.color" stroke-width="1.5" stroke-linecap="round"/>
    </template>

    <!-- 🕸️ Graph / network -->
    <template v-else-if="info.id === 'graph'">
      <circle cx="12" cy="5"  r="2" :fill="info.color"/>
      <circle cx="5"  cy="18" r="2" :fill="info.color"/>
      <circle cx="19" cy="18" r="2" :fill="info.color"/>
      <line x1="12" y1="7"  x2="5.8"  y2="16" :stroke="info.color" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="12" y1="7"  x2="18.2" y2="16" :stroke="info.color" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="7"  y1="18" x2="17"   y2="18" :stroke="info.color" stroke-width="1.5" stroke-linecap="round"/>
    </template>

    <!-- generic document fallback -->
    <template v-else>
      <path d="M6 2H14L20 8V20C20 21.1 19.1 22 18 22H6C4.9 22 4 21.1 4 20V4C4 2.9 4.9 2 6 2Z"
        :fill="info.color" opacity="0.5"/>
      <path d="M14 2L20 8H14V2Z" :fill="info.color"/>
    </template>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  filename: { type: String, default: '' },
  type:     { type: String, default: '' }, // source_type: vector | bm25 | graph | web
  size:     { type: Number, default: 20 },
})

const EXT_MAP = {
  // Documents
  pdf:      { label: 'PDF',  color: '#EF4444' },
  docx:     { label: 'DOC',  color: '#3B82F6' },
  doc:      { label: 'DOC',  color: '#3B82F6' },
  txt:      { label: 'TXT',  color: '#6B7280' },
  md:       { label: 'MD',   color: '#8B5CF6' },
  markdown: { label: 'MD',   color: '#8B5CF6' },
  // Data
  json:     { label: 'JSON', color: '#F59E0B' },
  csv:      { label: 'CSV',  color: '#10B981' },
  html:     { label: 'HTML', color: '#F97316' },
  htm:      { label: 'HTML', color: '#F97316' },
  // Web / styles
  js:       { label: 'JS',   color: '#EAB308' },
  jsx:      { label: 'JSX',  color: '#EAB308' },
  ts:       { label: 'TS',   color: '#3B82F6' },
  tsx:      { label: 'TSX',  color: '#3B82F6' },
  css:      { label: 'CSS',  color: '#06B6D4' },
  scss:     { label: 'SCSS', color: '#C026D3' },
  // Backend / systems
  py:       { label: 'PY',   color: '#3B82F6' },
  java:     { label: 'JAVA', color: '#F97316' },
  c:        { label: 'C',    color: '#6B7280' },
  cpp:      { label: 'C++',  color: '#6B7280' },
  cs:       { label: 'C#',   color: '#8B5CF6' },
  go:       { label: 'GO',   color: '#06B6D4' },
  rb:       { label: 'RB',   color: '#EF4444' },
  php:      { label: 'PHP',  color: '#8B5CF6' },
  rs:       { label: 'RS',   color: '#F97316' },
  swift:    { label: 'SWIFT',color: '#F97316' },
  kt:       { label: 'KT',   color: '#8B5CF6' },
  scala:    { label: 'SCA',  color: '#EF4444' },
  r:        { label: 'R',    color: '#3B82F6' },
  lua:      { label: 'LUA',  color: '#6B7280' },
  dart:     { label: 'DART', color: '#06B6D4' },
  sql:      { label: 'SQL',  color: '#F59E0B' },
  sh:       { label: 'SH',   color: '#6B7280' },
  bat:      { label: 'BAT',  color: '#6B7280' },
  pl:       { label: 'PL',   color: '#6B7280' },
}

const TYPE_MAP = {
  web:    { id: 'web',    color: '#6366F1' },
  vector: { id: 'vector', color: '#10B981' },
  bm25:   { id: 'bm25',   color: '#0EA5E9' },
  graph:  { id: 'graph',  color: '#14B8A6' },
}

const info = computed(() => {
  if (props.filename) {
    const ext = props.filename.split('.').pop().toLowerCase()
    const extInfo = EXT_MAP[ext]
    if (extInfo) return { mode: 'ext', ...extInfo }
    return { mode: 'ext', label: ext.slice(0, 4).toUpperCase(), color: '#A8A29E' }
  }
  const typeInfo = TYPE_MAP[props.type]
  if (typeInfo) return { mode: 'svg', ...typeInfo }
  return { mode: 'svg', id: 'generic', color: '#A8A29E' }
})
</script>

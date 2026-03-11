import { defineStore } from 'pinia'
import { ref } from 'vue'

function applyTheme(t) {
  document.documentElement.classList.toggle('dark', t === 'dark')
}

export const useUiStore = defineStore('ui', () => {
  const theme = ref(localStorage.getItem('rag-theme') || 'dark')

  // Apply on store creation
  applyTheme(theme.value)

  function setTheme(t) {
    theme.value = t
    localStorage.setItem('rag-theme', t)
    applyTheme(t)
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  // ── Modal ──────────────────────────────────────────────────────────────────
  const modal = ref(null)

  function alert(message) {
    return new Promise((resolve) => { modal.value = { type: 'alert', message, resolve } })
  }

  function confirm(message, options = {}) {
    return new Promise((resolve) => {
      modal.value = { type: 'confirm', message, resolve, danger: options.danger || false }
    })
  }

  function close(result = true) {
    if (modal.value) { modal.value.resolve(result); modal.value = null }
  }

  return { theme, setTheme, toggleTheme, modal, alert, confirm, close }
})

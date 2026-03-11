<template>
  <transition name="fade">
    <div v-if="ui.modal"
      class="fixed inset-0 flex items-center justify-center z-50
             bg-black/20 dark:bg-black/60 backdrop-blur-sm">
      <div class="bg-white dark:bg-stone-900
                  border border-stone-200 dark:border-stone-800
                  rounded-2xl p-6 max-w-sm w-full mx-4 space-y-4
                  shadow-xl dark:shadow-none">
        <p class="text-sm text-stone-700 dark:text-stone-300 leading-relaxed">{{ ui.modal.message }}</p>
        <div class="flex justify-end gap-2">
          <button v-if="ui.modal.type === 'confirm'"
            class="btn-secondary text-xs py-1.5 px-4"
            @click="ui.close(false)">Cancel</button>
          <button
            class="text-xs py-1.5 px-4 font-semibold rounded-xl transition-colors duration-150"
            :class="ui.modal.danger
              ? 'bg-red-600 hover:bg-red-500 active:bg-red-700 text-white'
              : 'btn-primary'"
            @click="ui.close(true)">
            {{ ui.modal.danger ? 'Delete' : 'OK' }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { useUiStore } from '../stores/ui'
const ui = useUiStore()
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

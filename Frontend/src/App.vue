<template>
  <div class="min-h-screen bg-stone-50 dark:bg-[#0C0A09]
              text-stone-900 dark:text-stone-100
              transition-colors duration-200">
    <NavBar />
    <RouterView v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
    <ModalDialog />
  </div>
</template>

<script setup>
import { useUiStore } from './stores/ui'
import NavBar from './components/NavBar.vue'
import ModalDialog from './components/ModalDialog.vue'

useUiStore()
</script>

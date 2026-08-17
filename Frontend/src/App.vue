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
import { useUiStore } from './store'
import NavBar from './shared/components/NavBar/NavBar.vue'
import ModalDialog from './shared/components/ModalDialog/ModalDialog.vue'

useUiStore()
</script>

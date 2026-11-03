<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppNav from './components/AppNav.vue'
</script>

<template>
  <AppNav />
  <main class="content">
    <RouterView />
  </main>
</template>

<style scoped>
/* Deja lugar para la barra de abajo en el celular y para el menú en la computadora */
.content {
  padding: 16px 16px calc(80px + env(safe-area-inset-bottom));
  max-width: 1100px;
}

@media (min-width: 768px) {
  .content {
    margin-left: var(--sidebar-width);
    padding: 32px;
  }
}
</style>

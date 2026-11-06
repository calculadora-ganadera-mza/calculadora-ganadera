<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppNav from './components/AppNav.vue'
import LoginView from './views/LoginView.vue'
import { isAuthenticated } from './api/auth'
</script>

<template>
  <AppNav v-if="isAuthenticated" />
  <main class="content" :class="{ 'login-content': !isAuthenticated }">
    <RouterView v-if="isAuthenticated" />
    <LoginView v-else />
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

.content.login-content {
  margin: 0 auto;
  padding: 32px 16px;
}
</style>

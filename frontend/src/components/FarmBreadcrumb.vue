<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from 'vue-router'

// Ruta de navegación de Mi campo; el último paso es la pantalla actual y no lleva enlace
defineProps<{ steps: { label: string; to?: RouteLocationRaw }[] }>()
</script>

<template>
  <nav class="breadcrumb" aria-label="Ruta de navegación">
    <RouterLink to="/farm/scenarios">Mi campo</RouterLink>
    <!-- La clave es la posición: el escenario y el sector pueden llamarse igual -->
    <template v-for="(step, index) in steps" :key="index">
      <span aria-hidden="true">›</span>
      <RouterLink v-if="step.to" :to="step.to">{{ step.label }}</RouterLink>
      <span v-else aria-current="page">{{ step.label }}</span>
    </template>
  </nav>
</template>

<style scoped>
.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.breadcrumb a {
  color: var(--color-primary);
}
</style>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="calculators-page">
    <h1>Calculadoras</h1>
    <article class="card">
      <div>
        <h2>Receptividad</h2>
        <p>Cuántos animales soporta un sector según su pasto.</p>
      </div>
      <RouterLink class="button" :to="{ name: 'carrying-capacity' }">
        Calcular receptividad
      </RouterLink>
    </article>
  </section>
</template>

<style scoped>
.calculators-page {
  max-width: 1100px;
}
.card {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}
.card h2 {
  margin: 0;
  font-size: 1.05rem;
}
.card p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}
.button {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 8px;
  background: var(--color-primary);
  color: var(--color-surface);
  text-decoration: none;
}
</style>

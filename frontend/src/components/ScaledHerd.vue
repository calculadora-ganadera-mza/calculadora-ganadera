<script setup lang="ts">
import type { ScaledHerd } from '@/api/carryingCapacity'
import { upToOneDecimal } from '@/utils/format'

defineProps<{ herd: ScaledHerd | null; currentCowEquivalents: number }>()
</script>

<template>
  <section v-if="herd" class="scaled" aria-label="Mi rodeo ajustado al campo">
    <h2>Mi rodeo ajustado al campo</h2>

    <table>
      <thead>
        <tr>
          <th scope="col">Categoría</th>
          <th scope="col">Actual</th>
          <th scope="col">Ajustado</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="category in herd.categories" :key="category.animal_category_id">
          <th scope="row">{{ category.name }}</th>
          <td>{{ category.current_quantity }}</td>
          <td>{{ category.quantity }}</td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <th scope="row">Total</th>
          <td>{{ upToOneDecimal.format(currentCowEquivalents) }} EV</td>
          <td>{{ upToOneDecimal.format(herd.cow_equivalents) }} EV</td>
        </tr>
      </tfoot>
    </table>
    <p class="hint">
      El rodeo actual incluye las terneras de reposición, que la aplicación calcula a partir de las
      vacas.
    </p>
  </section>
</template>

<style scoped>
.scaled {
  padding: 20px 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}

h2 {
  margin: 0 0 12px;
  font-size: 1rem;
}

.hint {
  margin: 12px 0 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}

th,
td {
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
}

td,
thead th + th {
  text-align: right;
}

th {
  font-weight: 400;
}

thead th {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  font-weight: 500;
}

tfoot th,
tfoot td {
  border-bottom: 0;
  font-weight: 600;
}
</style>

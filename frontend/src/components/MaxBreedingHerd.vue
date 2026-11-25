<script setup lang="ts">
import { computed } from 'vue'
import type { CalculationWarning, MaxBreedingHerd } from '@/api/carryingCapacity'

const props = defineProps<{
  herd: MaxBreedingHerd | null
  warnings: CalculationWarning[]
}>()

const oneDecimal = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 })

// "1 macho", "3 machos"
const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

// Avisos del rodeo; el del índice ya se muestra junto a la receptividad
const HERD_WARNINGS = ['replacement_exceeds_females', 'herd_does_not_fit']
const herdWarnings = computed(() =>
  props.warnings.filter((warning) => HERD_WARNINGS.includes(warning.code)),
)
</script>

<template>
  <section v-if="herd || herdWarnings.length" class="breeding" aria-label="Rodeo de cría máximo">
    <h2 class="term heading">
      <button type="button" aria-describedby="tip-max-breeding">Rodeo de cría máximo</button>
      <span id="tip-max-breeding" class="tip" role="tooltip">
        Rodeo de cría estándar que entra en el sector. Parte del límite por pasto y baja si en
        verano necesita más agua de la que reponen las aguadas. Como usa sus propios litros por EV,
        puede quedar por encima del rodeo máximo.
      </span>
    </h2>

    <ul v-if="herdWarnings.length" class="warnings">
      <li v-for="warning in herdWarnings" :key="warning.code" role="status">
        {{ warning.message }}
      </li>
    </ul>

    <template v-if="herd">
      <table>
        <tbody>
          <tr v-for="category in herd.categories" :key="category.animal_category_id">
            <th scope="row">{{ category.name }}</th>
            <td>{{ category.quantity }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">Total</th>
            <td>{{ oneDecimal.format(herd.cow_equivalents) }} EV</td>
          </tr>
        </tfoot>
      </table>
      <p class="weaned">
        Terneros destetados por año: {{ count(herd.weaned_calves.males, 'macho', 'machos') }} y
        {{ count(herd.weaned_calves.females, 'hembra', 'hembras') }}. Salen al destete, salvo las
        terneras de reposición.
      </p>
    </template>
  </section>
</template>

<style scoped>
.breeding {
  padding: 20px 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}

h2 {
  margin: 0 0 12px;
  font-size: 1rem;
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

td {
  text-align: right;
}

th {
  font-weight: 400;
}

tfoot th,
tfoot td {
  border-bottom: 0;
  font-weight: 600;
}

.weaned {
  margin: 12px 0 0;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.warnings {
  margin: 0 0 12px;
  padding: 10px 12px 10px 28px;
  border-radius: 8px;
  background: var(--color-warning-soft);
  color: var(--color-warning);
  font-size: 0.9rem;
}
</style>

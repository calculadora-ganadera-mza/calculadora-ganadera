<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import type { CarryingCapacityResult, CorrectionIndex } from '@/api/carryingCapacity'
import type { AnimalCategory, HerdData } from '@/api/herds'
import { loadedAnimals, RANGE_CONDITION_LABELS } from '@/utils/herd'
import { formatDate } from '@/utils/season'

const props = defineProps<{
  result: CarryingCapacityResult
  rainfallMm: number
  herd: HerdData
  categories: AnimalCategory[]
  // Dónde se cambia cada dato; sin enlaces cuando se muestran valores simulados
  links?: { rainfall: RouteLocationRaw; sector: RouteLocationRaw }
}>()

const oneDecimal = new Intl.NumberFormat('es-AR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})
const number = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 })
const integer = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 })
// Los índices se muestran como los carga el administrador, sin redondear a un decimal
const indexNumber = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 3 })

const percent = (rate: number | null) =>
  rate === null ? 'Sin cargar' : `${number.format(rate * 100)} %`
const yesNo = (value: boolean) => (value ? 'Sí' : 'No')

const rangeCondition = computed(() => RANGE_CONDITION_LABELS[props.herd.range_condition])

// Una fila por dato, con el enlace a donde se cambia
const rows = computed(() => {
  const { herd, result, links } = props
  const refill = result.water.refill_l_day
  const sector = links?.sector
  return [
    {
      label: 'Lluvia de la campaña anterior',
      value: `${number.format(props.rainfallMm)} mm`,
      change: 'la lluvia',
      to: links?.rainfall,
    },
    {
      label: 'Estado del campo',
      value: rangeCondition.value,
      change: 'el estado del campo',
      to: sector,
    },
    {
      label: 'Rodeo cargado',
      value: 'Sin animales',
      animals: loadedAnimals(herd, props.categories),
      change: 'el rodeo',
      to: sector,
    },
    {
      label: 'Reposición',
      value: percent(herd.replacement_rate),
      change: 'la reposición',
      to: sector,
    },
    { label: 'Destete', value: percent(herd.weaning_rate), change: 'el destete', to: sector },
    {
      label: 'Inicio del entore',
      value: herd.breeding_start ? formatDate(herd.breeding_start) : 'Sin cargar',
      change: 'el inicio del entore',
      to: sector,
    },
    {
      label: 'Destete precoz',
      value: yesNo(herd.early_weaning),
      change: 'el destete precoz',
      to: sector,
    },
    {
      label: 'Suplementación',
      value: yesNo(herd.supplemented),
      change: 'la suplementación',
      to: sector,
    },
    {
      label: 'Superficie aprovechable',
      value: `${oneDecimal.format(result.usable_area_ha)} de ${oneDecimal.format(result.area_ha)} ha`,
      change: 'las aguadas o el contorno del sector',
      to: sector,
    },
    {
      label: 'Reposición de las aguadas',
      value: refill === null ? 'Sin datos' : `${integer.format(refill)} L/día`,
      change: 'los litros de las aguadas',
      to: sector,
    },
  ]
})

const INDEX_NAMES: Record<CorrectionIndex['code'], string> = {
  range_condition: 'Índice por estado del campo',
  early_weaning: 'Índice por destete precoz',
  supplementation: 'Índice por suplementación',
}

function indexName(index: CorrectionIndex) {
  const name = INDEX_NAMES[index.code]
  return index.code === 'range_condition' ? `${name} (${rangeCondition.value.toLowerCase()})` : name
}

function indexValue(index: CorrectionIndex) {
  if (!index.applies) return 'No marcado'
  return index.value === null ? 'Sin valor' : indexNumber.format(index.value)
}
</script>

<template>
  <section class="details" aria-labelledby="used-data-heading">
    <h2 id="used-data-heading">Datos usados</h2>
    <dl class="data-list">
      <div v-for="row in rows" :key="row.label">
        <dt>{{ row.label }}</dt>
        <dd>
          <ul v-if="row.animals?.length">
            <li v-for="animal in row.animals" :key="animal.id">
              <span>{{ animal.name }}</span> <span>{{ animal.quantity }}</span>
            </li>
          </ul>
          <template v-else>{{ row.value }}</template>
        </dd>
        <RouterLink v-if="row.to" :to="row.to">
          Cambiar <span class="visually-hidden">{{ row.change }}</span>
        </RouterLink>
      </div>
    </dl>

    <details class="breakdown">
      <summary>Desglose del cálculo</summary>
      <div class="breakdown-body">
        <table>
          <caption>
            Forraje
            <span class="source">Fuente: Guevara y otros (1995)</span>
          </caption>
          <tbody>
            <tr>
              <th scope="row">Lluvia de la campaña anterior</th>
              <td>{{ number.format(rainfallMm) }} mm</td>
            </tr>
            <tr>
              <th scope="row">Forraje consumible</th>
              <td>
                {{ oneDecimal.format(result.pasture_breakdown.consumable_forage_kg_ha_year) }}
                kg MS/ha/año
              </td>
            </tr>
            <tr>
              <th scope="row">Consumo anual de un EV</th>
              <td>
                {{ integer.format(result.pasture_breakdown.cow_equivalent_dm_intake_kg_year) }}
                kg MS
              </td>
            </tr>
          </tbody>
        </table>
        <table>
          <caption>
            Receptividad
          </caption>
          <tbody>
            <tr>
              <th scope="row">Base</th>
              <td>
                {{
                  oneDecimal.format(
                    result.pasture_breakdown.base_carrying_capacity_ha_per_cow_equivalent,
                  )
                }}
                ha/EV
              </td>
            </tr>
            <tr v-for="index in result.pasture_breakdown.indices" :key="index.code">
              <th scope="row">{{ indexName(index) }}</th>
              <td :class="{ muted: !index.applies || index.value === null }">
                {{ indexValue(index) }}
              </td>
            </tr>
            <tr class="total">
              <th scope="row">Corregida</th>
              <td>{{ oneDecimal.format(result.carrying_capacity_ha_per_cow_equivalent) }} ha/EV</td>
            </tr>
          </tbody>
        </table>
        <table>
          <caption>
            Límite por pasto
          </caption>
          <tbody>
            <tr>
              <th scope="row">Superficie aprovechable</th>
              <td>{{ oneDecimal.format(result.usable_area_ha) }} ha</td>
            </tr>
            <tr class="total">
              <th scope="row">Límite por pasto</th>
              <td>{{ oneDecimal.format(result.pasture_limit_cow_equivalents) }} EV</td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </section>
</template>

<style scoped>
.details {
  margin-top: 24px;
}

h2 {
  margin: 0 0 8px;
  font-size: 1rem;
}

.breakdown {
  margin-top: 24px;
}

.breakdown summary {
  font-weight: 600;
  cursor: pointer;
}

.breakdown-body {
  display: grid;
  gap: 16px;
  margin-top: 12px;
}

table {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
  font-size: 0.9rem;
  font-variant-numeric: tabular-nums;
}

caption {
  padding: 0 0 6px;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: left;
}

.source {
  margin-left: 8px;
  color: var(--color-text-muted);
  font-weight: 400;
}

th,
td {
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
}

th {
  font-weight: 400;
  text-align: left;
}

td {
  text-align: right;
  white-space: nowrap;
}

tr:last-child > * {
  border-bottom: 0;
}

.total > * {
  font-weight: 600;
}

.muted {
  color: var(--color-text-muted);
}
</style>

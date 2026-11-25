<script setup lang="ts">
import { computed } from 'vue'
import type { CarryingCapacityResult, LimitedBy } from '@/api/carryingCapacity'
import LoadThermometer from './LoadThermometer.vue'
import MaxBreedingHerd from './MaxBreedingHerd.vue'
import ScaledHerd from './ScaledHerd.vue'

const props = defineProps<{ result: CarryingCapacityResult; rainfallMm: number }>()

// Aviso del backend con ese código, si llegó alguno
function warning(code: string) {
  return props.result.warnings.find((item) => item.code === code)
}

const LIMITED_BY: Record<LimitedBy, string> = {
  pasture: 'Limita el pasto',
  water: 'Limita el agua',
}

const oneDecimal = new Intl.NumberFormat('es-AR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

const integer = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 })
const signed = new Intl.NumberFormat('es-AR', {
  maximumFractionDigits: 0,
  signDisplay: 'exceptZero',
})

const NO_ESTIMATE = 'Sin estimación'
const NO_DATA = 'Sin datos'

// Fila de la tabla del agua: lo que necesita el límite por pasto en la
// estación, lo que reponen las aguadas y la diferencia entre los dos
function waterRow(season: string, need: number | null) {
  const refill = props.result.water.refill_l_day
  const row = {
    season,
    need: need === null ? NO_ESTIMATE : integer.format(need),
    refill: refill === null ? NO_DATA : integer.format(refill),
  }
  if (need === null) return { ...row, difference: NO_ESTIMATE, negative: false }
  if (refill === null) return { ...row, difference: NO_DATA, negative: false }
  // Resta de los valores ya redondeados, para que cierre con lo que se ve
  const difference = Math.round(refill) - Math.round(need)
  return { ...row, difference: signed.format(difference), negative: difference < 0 }
}

const waterRows = computed(() => [
  waterRow('Verano', props.result.water.summer_need_l_day),
  waterRow('Invierno', props.result.water.winter_need_l_day),
])
</script>

<template>
  <section class="kpis" aria-label="Resultados">
    <div class="kpi">
      <span class="term">
        <button type="button" aria-describedby="tip-capacity">Receptividad</button>
        <span id="tip-capacity" class="tip" role="tooltip">
          Hectáreas que necesita un EV durante un año, según la lluvia de la campaña anterior y los
          índices de corrección.
        </span>
      </span>
      <p class="value">
        {{ oneDecimal.format(result.carrying_capacity_ha_per_cow_equivalent) }}
        <span class="unit">ha/EV</span>
      </p>
      <p class="sub">
        {{ rainfallMm }} mm de lluvia
        <span v-if="warning('missing_index')" class="tag warn">Falta un índice</span>
      </p>
    </div>
    <div class="kpi">
      <span class="term">
        <button type="button" aria-describedby="tip-pasture">Límite por pasto</button>
        <span id="tip-pasture" class="tip" role="tooltip">
          EV que puede alimentar el pasto del sector en un año: superficie aprovechable ÷
          receptividad.
        </span>
      </span>
      <p class="value">
        {{ oneDecimal.format(result.pasture_limit_cow_equivalents) }}
        <span class="unit">EV</span>
      </p>
      <p class="sub">{{ oneDecimal.format(result.usable_area_ha) }} ha aprovechables</p>
    </div>
    <div class="kpi">
      <span class="term">
        <button type="button" aria-describedby="tip-water">Límite por agua</button>
        <span id="tip-water" class="tip" role="tooltip">
          EV que pueden tomar agua en verano con lo que reponen por día las aguadas del sector,
          según los litros por EV del rodeo actual.
        </span>
      </span>
      <template v-if="result.water.evaluated">
        <p class="value">
          {{ oneDecimal.format(result.water.limit_cow_equivalents) }}
          <span class="unit">EV</span>
        </p>
        <p class="sub">
          {{ integer.format(result.water.refill_l_day) }} L/día de reposición
          <span v-if="warning('partial_water_data')" class="tag warn">Datos parciales</span>
        </p>
        <p v-if="warning('partial_water_data')" class="sub">
          {{ warning('partial_water_data')?.message }}
        </p>
      </template>
      <template v-else>
        <p class="value small">Sin evaluar</p>
        <p class="sub">{{ warning('water_not_evaluated')?.message }}</p>
      </template>
    </div>
    <div class="kpi max">
      <span class="term">
        <button type="button" aria-describedby="tip-max">Rodeo máximo</button>
        <span id="tip-max" class="tip" role="tooltip">
          El menor entre el límite por pasto y el límite por agua. 1 EV = una vaca con su ternero
          hasta el destete.
        </span>
      </span>
      <p class="value">
        {{ oneDecimal.format(result.max_herd.cow_equivalents) }}
        <span class="unit">EV</span>
      </p>
      <p class="sub">
        <span class="tag">{{ LIMITED_BY[result.max_herd.limited_by] }}</span>
      </p>
    </div>
  </section>
  <LoadThermometer
    :load="result.load_thermometer"
    :max-cow-equivalents="result.max_herd.cow_equivalents"
  />
  <div class="herds">
    <MaxBreedingHerd :herd="result.max_breeding_herd" :warnings="result.warnings" />
    <ScaledHerd
      :herd="result.scaled_herd"
      :current-cow-equivalents="result.load_thermometer.current_cow_equivalents"
    />
  </div>
  <section class="water-need" aria-label="Agua para aprovechar todo el pasto">
    <div class="section-head">
      <h2 class="term heading">
        <button type="button" aria-describedby="tip-water-need">
          Agua para aprovechar todo el pasto
        </button>
        <span id="tip-water-need" class="tip" role="tooltip">
          Litros por día que necesitan los
          {{ oneDecimal.format(result.pasture_limit_cow_equivalents) }} EV del límite por pasto, con
          los litros por EV del rodeo actual, comparados con lo que reponen las aguadas.
        </span>
      </h2>
      <span class="sub">L/día</span>
    </div>
    <div class="table-wrap water-table">
      <table>
        <thead>
          <tr>
            <th scope="col">Estación</th>
            <th scope="col">Necesita</th>
            <th scope="col">Reponen las aguadas</th>
            <th scope="col">Diferencia</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in waterRows" :key="row.season">
            <th scope="row">{{ row.season }}</th>
            <td>{{ row.need }}</td>
            <td>{{ row.refill }}</td>
            <td :class="{ negative: row.negative }">{{ row.difference }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}
.kpi {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding: 20px 24px;
}
.kpi + .kpi {
  border-left: 1px solid var(--color-border);
}
.kpi p {
  margin: 0;
}
.value {
  font-size: 2rem;
  font-weight: 600;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.unit {
  color: var(--color-text-muted);
  font-size: 0.95rem;
  font-weight: 500;
}
.value.small {
  font-size: 1.5rem;
}
/* El rodeo máximo se destaca: es el resultado que manda */
.max {
  border-radius: 0 11px 11px 0;
  background: var(--color-primary-soft);
}
.max .value {
  color: var(--color-primary);
}
.sub {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}
.herds {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 16px;
  margin-top: 24px;
}
.water-need {
  margin-top: 24px;
}
.section-head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.section-head h2 {
  margin: 0;
}
.water-table {
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
}
.water-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  font-variant-numeric: tabular-nums;
}
.water-table th,
.water-table td {
  padding: 11px 20px;
  border-bottom: 1px solid var(--color-border);
  text-align: right;
  white-space: nowrap;
}
.water-table th:first-child {
  text-align: left;
}
.water-table thead th {
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 600;
}
.water-table tbody th {
  font-weight: 400;
}
.water-table tbody tr:last-child > * {
  border-bottom: 0;
}
.negative {
  color: var(--color-danger);
}
@media (max-width: 900px) {
  .kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .kpi:nth-child(3) {
    border-left: 0;
  }
  .kpi:nth-child(n + 3) {
    border-top: 1px solid var(--color-border);
  }
  .max {
    border-radius: 0 0 11px 0;
  }
}
@media (max-width: 700px) {
  .kpis,
  .herds {
    grid-template-columns: minmax(0, 1fr);
  }
  .kpi + .kpi {
    border-left: 0;
    border-top: 1px solid var(--color-border);
  }
  .max {
    border-radius: 0 0 11px 11px;
  }
}
</style>

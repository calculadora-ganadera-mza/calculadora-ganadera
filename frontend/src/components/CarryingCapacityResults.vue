<script setup lang="ts">
import type { CarryingCapacityResult, LimitedBy } from '@/api/carryingCapacity'
import LoadThermometer from './LoadThermometer.vue'
import RecommendedHerd from './RecommendedHerd.vue'
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

function litresPerDay(value: number | null, unavailable: string) {
  return value === null ? unavailable : `${integer.format(value)} L/día`
}
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
          EV que pueden tomar agua en verano con lo que reponen por día las aguadas del sector.
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
  <LoadThermometer :load="result.load_thermometer" />
  <section class="water-need" aria-labelledby="water-need-heading">
    <h2 id="water-need-heading">Agua necesaria para el límite por pasto</h2>
    <dl>
      <div>
        <dt>Verano</dt>
        <dd>{{ litresPerDay(result.water.summer_need_l_day, 'Sin estimación') }}</dd>
      </div>
      <div>
        <dt>Invierno</dt>
        <dd>{{ litresPerDay(result.water.winter_need_l_day, 'Sin estimación') }}</dd>
      </div>
      <div>
        <dt>Reposición de las aguadas</dt>
        <dd>{{ litresPerDay(result.water.refill_l_day, 'Sin datos') }}</dd>
      </div>
    </dl>
  </section>
  <div class="herds">
    <RecommendedHerd :herd="result.recommended_herd" :warnings="result.warnings" />
    <ScaledHerd
      :herd="result.scaled_herd"
      :current-cow-equivalents="result.load_thermometer.current_cow_equivalents"
      :max-herd-cow-equivalents="result.max_herd.cow_equivalents"
    />
  </div>
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
.term {
  position: relative;
  align-self: flex-start;
}
.term button {
  padding: 0;
  border: 0;
  border-bottom: 1px dotted var(--color-text-muted);
  background: none;
  color: var(--color-text-muted);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: help;
}
.tip {
  display: none;
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 5;
  width: 250px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-text);
  color: var(--color-background);
  font-size: 0.8rem;
  line-height: 1.45;
}
.term:hover .tip,
.term:focus-within .tip {
  display: block;
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
.tag {
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-hover);
  color: var(--color-text);
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}
.tag.warn {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.water-need {
  margin: 16px 0;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
}
.water-need h2 {
  margin: 0 0 12px;
  font-size: 1rem;
}
.water-need dl {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
  margin: 0;
  font-variant-numeric: tabular-nums;
}
.water-need dt {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}
.water-need dd {
  margin: 2px 0 0;
  font-weight: 600;
}
.herds {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 16px;
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

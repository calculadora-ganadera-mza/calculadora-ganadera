<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { calculateCarryingCapacity, type CarryingCapacityResult } from '@/api/carryingCapacity'
import { ApiError } from '@/api/errors'
import RecommendedHerd from '@/components/RecommendedHerd.vue'
import { listHerds } from '@/api/herds'
import { listProductionUnits, type ProductionUnit } from '@/api/productionUnits'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'
import { seasonLabel } from '@/utils/season'

const route = useRoute()
const scenario = ref<Scenario>()
const season = ref<Season>()
const unit = ref<ProductionUnit>()
// Dato de la campaña que falta cargar antes de calcular
const missing = ref<'rainfall' | 'herd'>()
const result = ref<CarryingCapacityResult>()
const loading = ref(true)
const error = ref('')

// El backend avisa cuando calculó sin algún índice de corrección
const missingIndex = computed(
  () => result.value?.warnings.some((warning) => warning.code === 'missing_index') ?? false,
)

const oneDecimal = new Intl.NumberFormat('es-AR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

async function load() {
  loading.value = true
  error.value = ''
  missing.value = undefined
  result.value = undefined
  const scenarioId = Number(route.params.scenarioId)
  const unitId = Number(route.params.unitId)
  const seasonId = Number(route.params.seasonId)
  try {
    const [scenarios, seasons, units, herds] = await Promise.all([
      listScenarios(),
      listSeasons(scenarioId),
      listProductionUnits(scenarioId),
      listHerds(seasonId),
    ])
    scenario.value = scenarios.find((item) => item.id === scenarioId)
    season.value = seasons.find((item) => item.id === seasonId)
    unit.value = units.find((item) => item.id === unitId)
    const herd = herds.find((item) => item.production_unit_id === unitId)
    if (!scenario.value || !season.value || !unit.value) {
      error.value = 'No se encontró el escenario, el sector o la campaña elegidos.'
    } else if (!season.value.rainfall_mm) {
      missing.value = 'rainfall'
    } else if (!herd) {
      missing.value = 'herd'
    } else {
      result.value = await calculateCarryingCapacity(unitId, {
        ...herd,
        rainfall_mm: season.value.rainfall_mm,
      })
    }
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'No se pudo calcular.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="result-page">
    <nav class="breadcrumb" aria-label="Ubicación">
      <RouterLink to="/calculators">Calculadoras</RouterLink>
      <span aria-hidden="true">›</span>
      <span>Receptividad</span>
    </nav>
    <h1>Receptividad</h1>
    <p v-if="scenario && unit && season" class="subtitle">
      {{ scenario.name }} · {{ unit.name }} · campaña
      {{ seasonLabel(season.start_date, season.end_date) }} ·
      <RouterLink :to="{ name: 'sector', params: { scenarioId: scenario.id, unitId: unit.id } }">
        ver sector
      </RouterLink>
    </p>
    <p v-if="loading">Calculando…</p>
    <div v-else-if="error" class="error" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="load">Reintentar</button>
    </div>
    <p v-else-if="missing === 'rainfall'" class="missing" role="alert">
      Para calcular falta cargar la lluvia de la campaña anterior.
      <RouterLink to="/farm">Cargarla en Mi campo</RouterLink>
    </p>
    <p v-else-if="missing === 'herd' && scenario && unit" class="missing" role="alert">
      Para calcular falta cargar los datos de la campaña del sector.
      <RouterLink :to="{ name: 'sector', params: { scenarioId: scenario.id, unitId: unit.id } }">
        Cargarlos en el sector
      </RouterLink>
    </p>
    <section v-else-if="result && season" class="kpis" aria-label="Resultados">
      <div class="kpi">
        <span class="term">
          <button type="button" aria-describedby="tip-capacity">Receptividad</button>
          <span id="tip-capacity" class="tip" role="tooltip">
            Hectáreas que necesita un EV durante un año, según la lluvia de la campaña anterior y
            los índices de corrección.
          </span>
        </span>
        <p class="value">
          {{ oneDecimal.format(result.carrying_capacity_ha_per_cow_equivalent) }}
          <span class="unit">ha/EV</span>
        </p>
        <p class="sub">
          {{ season.rainfall_mm }} mm de lluvia
          <span v-if="missingIndex" class="tag">Falta un índice</span>
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
    </section>
    <RecommendedHerd
      v-if="result && season && !loading && !error && !missing"
      :herd="result.recommended_herd"
      :warnings="result.warnings"
    />
  </section>
</template>

<style scoped>
.result-page {
  max-width: 1100px;
}
.breadcrumb {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}
.breadcrumb a,
.subtitle a,
.missing a {
  color: var(--color-primary);
}
.subtitle {
  color: var(--color-text-muted);
}
.kpis {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  max-width: 720px;
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
  background: var(--color-warning-soft);
  color: var(--color-warning);
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}
.error p {
  color: var(--color-danger);
}
.error button {
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  cursor: pointer;
}
@media (max-width: 700px) {
  .kpis {
    grid-template-columns: minmax(0, 1fr);
  }
  .kpi + .kpi {
    border-left: 0;
    border-top: 1px solid var(--color-border);
  }
}
</style>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { calculateCarryingCapacity, type CarryingCapacityResult } from '@/api/carryingCapacity'
import { ApiError } from '@/api/errors'
import CarryingCapacityResults from '@/components/CarryingCapacityResults.vue'
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
    <header class="result-header">
      <div>
        <h1>Receptividad</h1>
        <p v-if="scenario && unit && season" class="subtitle">
          {{ scenario.name }} · {{ unit.name }} · campaña
          {{ seasonLabel(season.start_date, season.end_date) }} ·
          <RouterLink
            :to="{ name: 'sector', params: { scenarioId: scenario.id, unitId: unit.id } }"
          >
            ver sector
          </RouterLink>
        </p>
      </div>
      <RouterLink
        v-if="!loading && result && scenario && unit && season"
        class="simulate-link"
        :to="{
          name: 'carrying-capacity-simulate',
          query: { scenario: scenario.id, unit: unit.id, season: season.id },
        }"
      >
        Simular con otros valores
      </RouterLink>
    </header>
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
    <CarryingCapacityResults
      v-else-if="result && season?.rainfall_mm"
      :result="result"
      :rainfall-mm="season.rainfall_mm"
    />
  </section>
</template>

<style scoped>
.result-page {
  max-width: 1100px;
}
.result-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 12px 24px;
  margin-bottom: 12px;
}
.simulate-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  margin-inline-start: auto;
  padding: 0 14px;
  border: 1px solid var(--color-primary);
  border-radius: 8px;
  color: var(--color-primary);
  text-decoration: none;
}
.simulate-link:hover {
  background: var(--color-primary-soft);
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
  margin: 0;
  color: var(--color-text-muted);
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
</style>

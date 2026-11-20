<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { calculateCarryingCapacity, type CarryingCapacityResult } from '@/api/carryingCapacity'
import { ApiError } from '@/api/errors'
import CarryingCapacityResults from '@/components/CarryingCapacityResults.vue'
import HerdDataForm from '@/components/HerdDataForm.vue'
import { listAnimalCategories, listHerds, type AnimalCategory, type HerdData } from '@/api/herds'
import { listProductionUnits, type ProductionUnit } from '@/api/productionUnits'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'
import { seasonLabel } from '@/utils/season'

const route = useRoute()
const scenario = ref<Scenario>()
const season = ref<Season>()
const unit = ref<ProductionUnit>()
const campaignHerd = ref<HerdData>()
// Dato de la campaña que falta cargar antes de calcular
const missing = ref<'rainfall' | 'herd'>()
const result = ref<CarryingCapacityResult>()
const loading = ref(true)
const error = ref('')
const simulation = ref<{
  categories?: AnimalCategory[]
  rainfallMm: number | ''
  bullsPer100Cows: number | ''
  busy: boolean
  error: string
  calculated?: { result: CarryingCapacityResult; rainfallMm: number }
}>()

async function load() {
  loading.value = true
  error.value = ''
  missing.value = undefined
  result.value = undefined
  campaignHerd.value = undefined
  simulation.value = undefined
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
      campaignHerd.value = herd
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

async function startSimulation() {
  if (!season.value?.rainfall_mm) return
  simulation.value = {
    rainfallMm: season.value.rainfall_mm,
    bullsPer100Cows: '',
    busy: false,
    error: '',
  }
  const draft = simulation.value
  try {
    draft.categories = await listAnimalCategories()
  } catch {
    draft.error = 'No se pudieron cargar las categorías de animales.'
  }
}

async function recalculate(herd: HerdData) {
  const draft = simulation.value
  if (!draft || !unit.value || draft.busy) return
  const { rainfallMm, bullsPer100Cows } = draft
  if (rainfallMm === '' || !Number.isFinite(rainfallMm) || rainfallMm <= 0) {
    draft.error = 'Ingresá una lluvia mayor que cero.'
    return
  }
  if (bullsPer100Cows !== '' && (!Number.isFinite(bullsPer100Cows) || bullsPer100Cows <= 0)) {
    draft.error = 'Ingresá una cantidad de toros mayor que cero o dejá el campo vacío.'
    return
  }

  draft.busy = true
  try {
    const result = await calculateCarryingCapacity(unit.value.id, {
      ...herd,
      rainfall_mm: rainfallMm,
      ...(bullsPer100Cows === '' ? {} : { bulls_per_100_cows: bullsPer100Cows }),
    })
    draft.calculated = { result, rainfallMm }
  } catch (err) {
    draft.error = err instanceof ApiError ? err.message : 'No se pudo simular. Probá de nuevo.'
  } finally {
    draft.busy = false
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
      <button
        v-if="result && !simulation"
        class="simulate-button"
        type="button"
        @click="startSimulation"
      >
        Simular otros valores
      </button>
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
    <template v-else-if="result && season?.rainfall_mm">
      <div v-if="simulation" class="simulation-notice">
        <div>
          <strong>Modo simulación</strong>
          <p>Los cambios de la simulación son temporales.</p>
        </div>
        <button class="simulate-button" type="button" @click="simulation = undefined">
          Volver a mis datos
        </button>
      </div>
      <section v-if="simulation" class="simulation-panel" aria-labelledby="simulation-title">
        <h2 id="simulation-title">Valores simulados</h2>
        <HerdDataForm
          v-if="simulation.categories"
          class="simulation-form"
          :categories="simulation.categories"
          id-prefix="simulation"
          :initial="campaignHerd"
          :busy="simulation.busy"
          :action="simulation.busy ? 'Recalculando…' : 'Recalcular'"
          :error="simulation.error"
          @attempt="simulation.error = ''"
          @submit="recalculate"
        >
          <fieldset class="simulation-inputs" :disabled="simulation.busy">
            <legend>Parámetros del cálculo</legend>
            <label>
              Lluvia de la campaña anterior (mm)
              <input
                v-model.number="simulation.rainfallMm"
                required
                type="number"
                min="0"
                step="any"
              />
            </label>
            <label>
              Toros cada 100 vacas (opcional)
              <input v-model.number="simulation.bullsPer100Cows" type="number" min="0" step="any" />
            </label>
          </fieldset>
        </HerdDataForm>
        <div v-else-if="simulation.error" class="error" role="alert">
          <p>{{ simulation.error }}</p>
          <button type="button" @click="startSimulation">Reintentar</button>
        </div>
        <p v-else role="status">Cargando categorías de animales…</p>
      </section>
      <CarryingCapacityResults
        :result="simulation?.calculated?.result ?? result"
        :rainfall-mm="simulation?.calculated?.rainfallMm ?? season.rainfall_mm"
      />
    </template>
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
.simulate-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  margin-inline-start: auto;
  padding: 0 14px;
  border: 1px solid var(--color-primary);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-primary);
  font: inherit;
  cursor: pointer;
}
.simulate-button:hover {
  background: var(--color-primary-soft);
}
.simulation-notice,
.simulation-panel {
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
}
.simulation-notice {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  background: var(--color-primary-soft);
}
.simulation-notice p {
  margin: 4px 0 0;
}
.simulation-panel {
  background: var(--color-surface);
}
.simulation-panel h2 {
  margin: 0;
  font-size: 1.05rem;
}
.simulation-panel .simulation-form {
  display: grid;
  max-width: none;
}
.simulation-form :deep(fieldset) {
  min-width: 0;
}
.simulation-inputs {
  display: grid;
  gap: 10px;
  min-width: 0;
  margin: 0;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.simulation-inputs legend {
  padding: 0 4px;
  font-weight: 600;
}
.simulation-inputs label {
  display: grid;
  gap: 4px;
  font-weight: 600;
}
.simulation-inputs input {
  width: 100%;
  min-height: 44px;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
}
.simulation-panel :deep(button[type='submit']) {
  justify-self: start;
  min-height: 44px;
  padding: 0 18px;
  border: 0;
  border-radius: 8px;
  background: var(--color-primary);
  color: var(--color-surface);
  font: inherit;
  cursor: pointer;
}
.simulation-panel :deep(button[type='submit']:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}
@media (min-width: 900px) {
  .simulation-form,
  .simulation-inputs {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .simulation-inputs,
  .simulation-form :deep([role='alert']) {
    grid-column: 1 / -1;
  }
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

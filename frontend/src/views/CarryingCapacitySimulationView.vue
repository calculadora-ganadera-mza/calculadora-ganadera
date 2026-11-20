<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { simulateCarryingCapacity, type CarryingCapacityResult } from '@/api/carryingCapacity'
import { ApiError } from '@/api/errors'
import { listAnimalCategories, listHerds, type AnimalCategory, type HerdData } from '@/api/herds'
import { listProductionUnits, type ProductionUnit } from '@/api/productionUnits'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'
import CarryingCapacityResults from '@/components/CarryingCapacityResults.vue'
import HerdDataForm from '@/components/HerdDataForm.vue'
import { seasonLabel } from '@/utils/season'

const route = useRoute()
const scenarios = ref<Scenario[]>([])
const seasons = ref<Season[]>([])
const units = ref<ProductionUnit[]>([])
const categories = ref<AnimalCategory[]>([])
const scenarioId = ref<number>()
const unitId = ref<number>()
const seasonId = ref<number>()
const initialHerd = ref<HerdData>()
const formVersion = ref(0)
const rainfallMm = ref<number | ''>('')
const bullsPer100Cows = ref<number | ''>('')
const loading = ref(true)
const loadingOptions = ref(false)
const loadingCampaign = ref(false)
const loadError = ref('')
const optionsError = ref('')
const campaignError = ref('')
const simulating = ref(false)
const error = ref('')
const simulation = ref<{
  result: CarryingCapacityResult
  rainfallMm: number
  unitName: string
}>()

async function loadScenario(preselectedUnit?: number, preselectedSeason?: number) {
  unitId.value = undefined
  seasonId.value = undefined
  units.value = []
  seasons.value = []
  optionsError.value = ''
  if (!scenarioId.value) return

  loadingOptions.value = true
  try {
    ;[units.value, seasons.value] = await Promise.all([
      listProductionUnits(scenarioId.value),
      listSeasons(scenarioId.value),
    ])
    unitId.value = units.value.find((unit) => unit.id === preselectedUnit)?.id
    seasonId.value = (
      seasons.value.find((season) => season.id === preselectedSeason) ??
      seasons.value.find((season) => season.is_current)
    )?.id
  } catch {
    optionsError.value = 'No se pudieron cargar los sectores y las campañas.'
  } finally {
    loadingOptions.value = false
  }
  await loadCampaign()
}

async function loadCampaign() {
  clearResult()
  campaignError.value = ''
  const season = seasons.value.find((item) => item.id === seasonId.value)
  initialHerd.value = undefined
  rainfallMm.value = season?.rainfall_mm ?? ''
  bullsPer100Cows.value = ''

  if (unitId.value && season) {
    loadingCampaign.value = true
    try {
      const herds = await listHerds(season.id)
      initialHerd.value = herds.find((herd) => herd.production_unit_id === unitId.value)
    } catch {
      campaignError.value = 'No se pudieron cargar los datos del rodeo de la campaña.'
    } finally {
      loadingCampaign.value = false
    }
  }
  formVersion.value++
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    ;[scenarios.value, categories.value] = await Promise.all([
      listScenarios(),
      listAnimalCategories(),
    ])
    scenarioId.value = (
      scenarios.value.find((scenario) => scenario.id === Number(route.query.scenario)) ??
      scenarios.value.find((scenario) => scenario.is_main) ??
      scenarios.value[0]
    )?.id
    await loadScenario(Number(route.query.unit), Number(route.query.season))
  } catch {
    loadError.value = 'No se pudieron cargar los escenarios y las categorías de animales.'
  } finally {
    loading.value = false
  }
}

function clearResult() {
  simulation.value = undefined
  error.value = ''
}

async function simulate(herd: HerdData) {
  const unit = units.value.find((item) => item.id === unitId.value)
  const rainfall = rainfallMm.value
  const bulls = bullsPer100Cows.value
  if (!unit || simulating.value) return
  if (rainfall === '' || !Number.isFinite(rainfall) || rainfall <= 0) {
    error.value = 'Ingresá una lluvia mayor que cero.'
    return
  }
  if (bulls !== '' && (!Number.isFinite(bulls) || bulls <= 0)) {
    error.value = 'Ingresá una cantidad de toros mayor que cero o dejá el campo vacío.'
    return
  }

  simulating.value = true
  try {
    const result = await simulateCarryingCapacity(unit.id, {
      ...herd,
      rainfall_mm: rainfall,
      ...(bulls === '' ? {} : { bulls_per_100_cows: bulls }),
    })
    simulation.value = { result, rainfallMm: rainfall, unitName: unit.name }
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'No se pudo simular. Probá de nuevo.'
  } finally {
    simulating.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="simulation-page">
    <nav class="breadcrumb" aria-label="Ubicación">
      <RouterLink to="/calculators">Calculadoras</RouterLink>
      <span aria-hidden="true">›</span>
      <RouterLink
        :to="{
          name: 'carrying-capacity',
          query: { scenario: scenarioId, unit: unitId, season: seasonId },
        }"
      >
        Receptividad
      </RouterLink>
    </nav>

    <h1>Simular receptividad</h1>
    <p>
      La simulación usa la superficie y las aguadas del sector. Los datos ingresados no se guardan.
    </p>

    <p v-if="loading" role="status">Cargando…</p>
    <div v-else-if="loadError">
      <p class="error" role="alert">{{ loadError }}</p>
      <button type="button" @click="load">Reintentar</button>
    </div>
    <p v-else-if="scenarios.length === 0">
      Creá un escenario en <RouterLink to="/farm">Mi campo</RouterLink> para simular.
    </p>
    <HerdDataForm
      v-else
      :key="formVersion"
      class="simulation-form"
      :categories="categories"
      id-prefix="simulation"
      :initial="initialHerd"
      :busy="simulating || loadingOptions || loadingCampaign"
      :disabled="!unitId || !seasonId || !!campaignError"
      :action="simulating ? 'Simulando…' : 'Simular'"
      :error="error"
      @attempt="clearResult"
      @submit="simulate"
    >
      <fieldset
        class="simulation-inputs"
        :disabled="simulating || loadingOptions || loadingCampaign"
      >
        <legend>Sector y parámetros</legend>
        <label>
          Escenario
          <select v-model="scenarioId" @change="loadScenario()">
            <option v-for="scenario in scenarios" :key="scenario.id" :value="scenario.id">
              {{ scenario.name }}
            </option>
          </select>
        </label>
        <label>
          Sector
          <select v-model="unitId" :disabled="units.length === 0" @change="loadCampaign">
            <option :value="undefined" disabled>Elegí un sector…</option>
            <option v-for="unit in units" :key="unit.id" :value="unit.id">{{ unit.name }}</option>
          </select>
        </label>
        <label>
          Campaña
          <select v-model="seasonId" :disabled="seasons.length === 0" @change="loadCampaign">
            <option :value="undefined" disabled>Elegí una campaña…</option>
            <option v-for="season in seasons" :key="season.id" :value="season.id">
              {{ seasonLabel(season.start_date, season.end_date) }}
              {{ season.is_current ? '(actual)' : '' }}
            </option>
          </select>
        </label>
        <p v-if="loadingOptions || loadingCampaign" role="status">Cargando datos de la campaña…</p>
        <template v-else-if="optionsError">
          <p class="error" role="alert">{{ optionsError }}</p>
          <button type="button" @click="loadScenario()">Reintentar</button>
        </template>
        <template v-else-if="campaignError">
          <p class="error" role="alert">{{ campaignError }}</p>
          <button type="button" @click="loadCampaign">Reintentar</button>
        </template>
        <p v-else-if="units.length === 0">Este escenario todavía no tiene sectores.</p>
        <p v-else-if="seasons.length === 0">Este escenario todavía no tiene campañas.</p>
        <label>
          Lluvia de la campaña anterior (mm)
          <input v-model.number="rainfallMm" required type="number" min="0" step="any" />
        </label>
        <label>
          Toros cada 100 vacas (opcional)
          <input v-model.number="bullsPer100Cows" type="number" min="0" step="any" />
        </label>
      </fieldset>
    </HerdDataForm>

    <section v-if="simulation" class="simulation-result" aria-labelledby="simulation-result-title">
      <h2 id="simulation-result-title">Resultado de la simulación</h2>
      <p>{{ simulation.unitName }}</p>
      <CarryingCapacityResults :result="simulation.result" :rainfall-mm="simulation.rainfallMm" />
    </section>
  </section>
</template>

<style scoped>
.simulation-page {
  max-width: 1100px;
}

.breadcrumb {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

a {
  color: var(--color-primary);
}

.simulation-form {
  padding: 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
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

.simulation-inputs input,
.simulation-inputs select {
  width: 100%;
  min-height: 44px;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
}

.simulation-inputs p {
  margin: 0;
}

.simulation-form :deep(button[type='submit']) {
  min-height: 44px;
  padding: 0 18px;
  border: 0;
  border-radius: 8px;
  background: var(--color-primary);
  color: var(--color-surface);
  font: inherit;
  cursor: pointer;
}

.simulation-form :deep(button[type='submit']:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  color: var(--color-danger);
}

.simulation-result {
  margin-top: 24px;
}

.simulation-result h2 {
  margin: 0 0 8px;
}
</style>

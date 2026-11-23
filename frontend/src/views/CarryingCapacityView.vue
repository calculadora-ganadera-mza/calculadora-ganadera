<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { listProductionUnits, type ProductionUnit } from '@/api/productionUnits'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'
import { pickSeason, seasonLabel } from '@/utils/season'

const route = useRoute()
const router = useRouter()
const scenarios = ref<Scenario[]>([])
const seasons = ref<Season[]>([])
const units = ref<ProductionUnit[]>([])
const scenarioId = ref<number>()
const unitId = ref<number>()
const seasonId = ref<number>()
const loading = ref(true)
const error = ref('')

const ready = computed(
  () => !loading.value && !!scenarioId.value && !!unitId.value && !!seasonId.value,
)

// Id que llega en la URL desde el botón Calcular del sector
function queryId(name: string): number {
  return Number(route.query[name])
}

// Carga sectores y campañas del escenario; arranca con la campaña actual
async function loadScenario(preselectedUnit?: number, preselectedSeason?: number) {
  unitId.value = undefined
  seasonId.value = undefined
  if (!scenarioId.value) return
  loading.value = true
  error.value = ''
  try {
    ;[seasons.value, units.value] = await Promise.all([
      listSeasons(scenarioId.value),
      listProductionUnits(scenarioId.value),
    ])
    unitId.value = units.value.find((unit) => unit.id === preselectedUnit)?.id
    seasonId.value = pickSeason(seasons.value, preselectedSeason)?.id
  } catch {
    error.value = 'No se pudieron cargar los sectores y las campañas.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    scenarios.value = await listScenarios()
  } catch {
    error.value = 'No se pudieron cargar los escenarios.'
    loading.value = false
    return
  }
  scenarioId.value = (
    scenarios.value.find((scenario) => scenario.id === queryId('scenario')) ??
    scenarios.value.find((scenario) => scenario.is_main)
  )?.id
  await loadScenario(queryId('unit'), queryId('season'))
  loading.value = false
})

function calculate() {
  router.push({
    name: 'carrying-capacity-result',
    params: { scenarioId: scenarioId.value, unitId: unitId.value, seasonId: seasonId.value },
  })
}
</script>

<template>
  <section class="carrying-capacity-page">
    <nav class="breadcrumb" aria-label="Ubicación">
      <RouterLink to="/calculators">Calculadoras</RouterLink>
      <span aria-hidden="true">›</span>
      <span>Receptividad</span>
    </nav>
    <h1>Calcular receptividad</h1>
    <form class="card" @submit.prevent="calculate">
      <label>
        Escenario
        <select v-model="scenarioId" :disabled="loading" @change="loadScenario()">
          <option v-for="scenario in scenarios" :key="scenario.id" :value="scenario.id">
            {{ scenario.name }}
          </option>
        </select>
      </label>
      <label>
        Sector
        <select v-model="unitId" :disabled="loading">
          <option v-for="unit in units" :key="unit.id" :value="unit.id">{{ unit.name }}</option>
        </select>
      </label>
      <label>
        Campaña
        <select v-model="seasonId" :disabled="loading">
          <option v-for="season in seasons" :key="season.id" :value="season.id">
            {{ seasonLabel(season.start_date, season.end_date) }}
            {{ season.is_current ? '(actual)' : '' }}
          </option>
        </select>
      </label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button type="submit" :disabled="!ready">Calcular</button>
    </form>
  </section>
</template>

<style scoped>
.carrying-capacity-page {
  max-width: 1100px;
}
.breadcrumb {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}
.breadcrumb a {
  color: var(--color-primary);
}
.card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 420px;
  padding: 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}
label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-weight: 600;
}
select {
  min-height: 44px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
  font-weight: 400;
}
.hint {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  font-weight: 400;
}
.error {
  margin: 0;
  color: var(--color-danger);
}
button {
  min-height: 44px;
  border: 0;
  border-radius: 8px;
  background: var(--color-primary);
  color: var(--color-surface);
  font: inherit;
  cursor: pointer;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

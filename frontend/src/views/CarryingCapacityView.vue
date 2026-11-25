<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import { listAnimalCategories, listHerds, type AnimalCategory, type Herd } from '@/api/herds'
import { listProductionUnits, type ProductionUnit } from '@/api/productionUnits'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'
import { loadedAnimals, RANGE_CONDITION_LABELS } from '@/utils/herd'
import { pickSeason, seasonLabel } from '@/utils/season'

const route = useRoute()
const router = useRouter()
const scenarios = ref<Scenario[]>([])
const seasons = ref<Season[]>([])
const units = ref<ProductionUnit[]>([])
const scenarioId = ref<number>()
const unitId = ref<number>()
const seasonId = ref<number>()
const categories = ref<AnimalCategory[]>([])
// Rodeos de la campaña elegida; undefined mientras se cargan
const herds = ref<Herd[]>()
const loading = ref(true)
const error = ref('')

const unit = computed(() => units.value.find((item) => item.id === unitId.value))
const season = computed(() => seasons.value.find((item) => item.id === seasonId.value))
const herd = computed(() => herds.value?.find((item) => item.production_unit_id === unitId.value))

const number = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 })

// Datos que va a usar el cálculo. Si falta uno, la fila lo marca y enlaza a
// donde se carga. La lluvia, el rodeo y la superficie hacen falta para calcular.
const calculationData = computed(() => {
  if (!scenarioId.value || !unit.value || !season.value || !herds.value) return undefined
  const sector: RouteLocationRaw = {
    name: 'sector',
    params: { scenarioId: scenarioId.value, unitId: unit.value.id },
    query: { season: season.value.id },
  }
  const rainfall = season.value.rainfall_mm
  const refill = unit.value.refill_l_day
  const animals = herd.value ? loadedAnimals(herd.value, categories.value) : []
  return [
    {
      label: 'Lluvia de la campaña anterior',
      value: rainfall ? `${number.format(rainfall)} mm` : undefined,
      required: true,
      load: 'la lluvia',
      to: {
        name: 'scenario',
        params: { scenarioId: scenarioId.value },
        query: { season: season.value.id },
      },
    },
    {
      label: 'Superficie aprovechable',
      value:
        unit.value.usable_area_ha > 0
          ? `${number.format(unit.value.usable_area_ha)} ha`
          : undefined,
      required: true,
      load: 'una aguada en el sector',
      to: sector,
    },
    {
      label: 'Reposición de las aguadas',
      value: refill === null ? undefined : `${number.format(refill)} L/día`,
      required: false,
      load: 'los litros de las aguadas',
      to: sector,
    },
    {
      label: 'Rodeo cargado',
      value: herd.value ? 'Sin animales' : undefined,
      animals,
      required: true,
      load: 'el rodeo',
      to: sector,
    },
    {
      label: 'Estado del campo',
      value: herd.value ? RANGE_CONDITION_LABELS[herd.value.range_condition] : undefined,
      required: true,
      load: 'el estado del campo',
      to: sector,
    },
  ]
})

const ready = computed(
  () =>
    !loading.value &&
    !!calculationData.value?.every((row) => !row.required || row.value !== undefined),
)

// Rodeos de la campaña elegida, para saber si el sector tiene datos
watch(seasonId, async (id) => {
  herds.value = undefined
  if (!id) return
  try {
    const loaded = await listHerds(id)
    if (seasonId.value === id) herds.value = loaded
  } catch {
    error.value = 'No se pudieron cargar los datos de la campaña.'
  }
})

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
    ;[scenarios.value, categories.value] = await Promise.all([
      listScenarios(),
      listAnimalCategories(),
    ])
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
    <section v-if="calculationData" class="calculation-data" aria-labelledby="data-heading">
      <h2 id="data-heading">Datos del cálculo</h2>
      <dl class="data-list">
        <div v-for="row in calculationData" :key="row.label">
          <dt>{{ row.label }}</dt>
          <dd>
            <ul v-if="row.animals?.length">
              <li v-for="animal in row.animals" :key="animal.id">
                <span>{{ animal.name }}</span> <span>{{ animal.quantity }}</span>
              </li>
            </ul>
            <template v-else-if="row.value">{{ row.value }}</template>
            <span v-else class="tag warn">Falta</span>
          </dd>
          <RouterLink v-if="row.value === undefined" :to="row.to">
            Cargar <span class="visually-hidden">{{ row.load }}</span>
          </RouterLink>
        </div>
      </dl>
    </section>
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
.calculation-data {
  max-width: 560px;
  margin-top: 24px;
}
.calculation-data h2 {
  margin: 0 0 8px;
  font-size: 1rem;
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

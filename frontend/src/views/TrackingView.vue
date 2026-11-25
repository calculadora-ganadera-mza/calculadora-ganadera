<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AddSeason from '@/components/AddSeason.vue'
import HistoryCharts from '@/components/HistoryCharts.vue'
import { getUnitHistory, type HistoryEntry } from '@/api/history'
import { listProductionUnits, type ProductionUnit } from '@/api/productionUnits'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'
import { routeId } from '@/utils/farm'
import { headCount, historyCategories, percent } from '@/utils/history'
import { seasonName } from '@/utils/season'

const route = useRoute()
const router = useRouter()
const scenario = ref<Scenario>()
const units = ref<ProductionUnit[]>([])
const seasons = ref<Season[]>([])
const entries = ref<HistoryEntry[]>([])
const loading = ref(true)
const error = ref('')
const historyLoading = ref(false)
const historyError = ref('')
// Campaña anterior recién agregada, para ofrecer cargarle los datos
const created = ref<Season>()
let historyVersion = 0

// El sector elegido queda en la dirección (?unit=) para volver a él; sin uno válido, el primero
const selected = computed(
  () => units.value.find((unit) => unit.id === routeId(route.query.unit)) ?? units.value[0],
)
const selectedId = computed({
  get: () => selected.value?.id,
  set: (id) => void router.replace({ query: { unit: id } }),
})
const categories = computed(() => historyCategories(entries.value))
const labels = computed(() => entries.value.map((entry) => entryName(entry)))

function entryName(entry: HistoryEntry): string {
  const season = seasons.value.find((item) => item.id === entry.season_id)
  return season ? seasonName(season.start_date, season.end_date) : String(entry.start_year)
}

function cell(value: number | null, unit = ''): string {
  return value === null ? '—' : `${value.toLocaleString('es-AR')}${unit}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const scenarios = await listScenarios()
    // Seguimiento muestra el escenario principal
    scenario.value = scenarios.find((item) => item.is_main) ?? scenarios[0]
    if (scenario.value)
      [units.value, seasons.value] = await Promise.all([
        listProductionUnits(scenario.value.id),
        listSeasons(scenario.value.id),
      ])
  } catch {
    error.value = 'No se pudo cargar el seguimiento. Intentá de nuevo.'
  } finally {
    loading.value = false
  }
}

// Con refresh se mantiene lo que ya se ve, para que la página no salte
async function loadHistory(refresh = false) {
  const unit = selected.value
  const version = ++historyVersion
  historyError.value = ''
  if (!refresh) {
    entries.value = []
    historyLoading.value = Boolean(unit)
  }
  if (!unit) return
  try {
    const loaded = await getUnitHistory(unit.id)
    if (version === historyVersion) entries.value = loaded
  } catch {
    if (version === historyVersion)
      historyError.value = 'No se pudo cargar la evolución del sector.'
  } finally {
    if (version === historyVersion) historyLoading.value = false
  }
}

async function onSeasonCreated(season: Season) {
  created.value = season
  if (!scenario.value) return
  try {
    seasons.value = await listSeasons(scenario.value.id)
  } catch {
    seasons.value = [season, ...seasons.value]
  }
  await loadHistory(true)
}

watch(selected, () => loadHistory())
onMounted(load)
</script>

<template>
  <section class="tracking-page">
    <header class="heading">
      <div>
        <h1>Seguimiento</h1>
        <p v-if="scenario" class="summary">
          {{ scenario.name }}
          <span v-if="scenario.is_main" class="badge">Principal</span>
        </p>
      </div>
      <div v-if="units.length" class="unit-bar">
        <label for="unit-select">Sector</label>
        <select id="unit-select" v-model="selectedId">
          <option v-for="unit in units" :key="unit.id" :value="unit.id">{{ unit.name }}</option>
        </select>
      </div>
    </header>

    <p v-if="loading">Cargando…</p>
    <div v-else-if="error" role="alert">
      <p class="error">{{ error }}</p>
      <button type="button" class="btn" @click="load">Reintentar</button>
    </div>
    <p v-else-if="!scenario" class="hint">
      Todavía no tenés un escenario. <RouterLink to="/farm">Crealo en Mi campo</RouterLink>.
    </p>
    <p v-else-if="!selected" class="hint">
      El escenario todavía no tiene sectores.
      <RouterLink :to="{ name: 'scenario', params: { scenarioId: scenario.id } }">
        Dibujá uno en Mi campo
      </RouterLink>
      .
    </p>
    <template v-else>
      <p v-if="historyLoading">Cargando la evolución del sector…</p>
      <div v-else-if="historyError" role="alert">
        <p class="error">{{ historyError }}</p>
        <button type="button" class="btn" @click="loadHistory()">Reintentar</button>
      </div>
      <template v-else>
        <HistoryCharts :entries="entries" :labels="labels" />

        <h2 class="table-title">Datos por campaña</h2>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Campaña</th>
                <th v-for="category in categories" :key="category.id" class="number">
                  {{ category.name }}
                </th>
                <th class="number">Destete</th>
                <th class="number">Reposición</th>
                <th class="number">Lluvia de la campaña anterior</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(entry, index) in entries" :key="entry.season_id">
                <td>
                  <RouterLink
                    :to="{
                      name: 'sector',
                      params: { scenarioId: scenario.id, unitId: selected.id },
                      query: { season: entry.season_id },
                    }"
                  >
                    {{ labels[index] }}
                  </RouterLink>
                </td>
                <td v-for="category in categories" :key="category.id" class="number">
                  {{ cell(headCount(entry, category.id)) }}
                </td>
                <td class="number">{{ cell(percent(entry.weaning_rate), ' %') }}</td>
                <td class="number">{{ cell(percent(entry.replacement_rate), ' %') }}</td>
                <td class="number">{{ cell(entry.rainfall_mm, ' mm') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <section class="panel load-season">
        <h2>Cargá tu campaña</h2>
        <p class="hint">Sumá un año anterior para comparar cómo venía el sector.</p>
        <AddSeason
          previous
          :scenario-id="scenario.id"
          :seasons="seasons"
          @created="onSeasonCreated"
        />
        <p v-if="created" role="status">
          Se agregó la campaña {{ seasonName(created.start_date, created.end_date) }}. Cargá
          <RouterLink
            :to="{
              name: 'sector',
              params: { scenarioId: scenario.id, unitId: selected.id },
              query: { season: created.id },
            }"
          >
            el rodeo del sector
          </RouterLink>
          y
          <RouterLink
            :to="{
              name: 'scenario',
              params: { scenarioId: scenario.id },
              query: { season: created.id },
            }"
          >
            la lluvia
          </RouterLink>
          de esa campaña.
        </p>
      </section>
    </template>
  </section>
</template>

<style scoped>
.tracking-page {
  max-width: 1100px;
}

.heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

h1 {
  margin: 0;
  font-size: 1.6rem;
  letter-spacing: -0.025em;
}

h2 {
  margin: 0;
  font-size: 0.95rem;
}

.summary {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.badge {
  display: inline-block;
  margin-left: 6px;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.75rem;
}

.unit-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unit-bar label {
  font-size: 0.9rem;
  font-weight: 600;
}

.unit-bar select {
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
  font-size: 0.9rem;
}

.table-title {
  margin: 28px 0 10px;
}

.load-season {
  display: grid;
  gap: 8px;
  margin-top: 28px;
}

.load-season p {
  margin: 0;
}
</style>

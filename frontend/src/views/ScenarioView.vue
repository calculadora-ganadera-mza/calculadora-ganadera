<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AddSeason from '@/components/AddSeason.vue'
import AppModal from '@/components/AppModal.vue'
import FarmBreadcrumb from '@/components/FarmBreadcrumb.vue'
import SeasonRainfall from '@/components/SeasonRainfall.vue'
import UnitsMap from '@/components/UnitsMap.vue'
import { loadScenarioMap, type ScenarioMap } from '@/api/farm'
import { listSeasons, type Season } from '@/api/scenarios'
import { hectares, keepSeason, routeId } from '@/utils/farm'
import { formatDate, pickSeason, seasonName } from '@/utils/season'

const route = useRoute()
const router = useRouter()
const data = ref<ScenarioMap>()
const seasons = ref<Season[]>([])
const loading = ref(true)
// La carga falló y se puede reintentar
const error = ref('')
// La dirección trae un escenario que no existe: reintentar no sirve
const missing = ref('')
const addingSeason = ref(false)
let loadVersion = 0

// La campaña elegida sale de la dirección (?season=); sin una válida, la actual
const selected = computed(() => pickSeason(seasons.value, route.query.season))
// Elegir otra reemplaza la dirección sin sumar un paso al historial
const selectedId = computed({
  get: () => selected.value?.id,
  set: (id) => void router.replace({ query: { season: id } }),
})
// El servidor las da de la más vieja a la más nueva
const newestFirst = computed(() => [...seasons.value].reverse())
const totalArea = computed(() =>
  (data.value?.units ?? []).reduce((total, unit) => total + unit.area_ha, 0),
)

function waterPointCount(unitId: number): number {
  return (data.value?.waterPoints ?? []).filter((point) => point.production_unit_id === unitId)
    .length
}

async function load() {
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  missing.value = ''
  data.value = undefined
  const scenarioId = routeId(route.params.scenarioId)
  try {
    const loaded = scenarioId === null ? null : await loadScenarioMap(scenarioId)
    const loadedSeasons = loaded ? await listSeasons(loaded.scenario.id) : []
    if (version !== loadVersion) return
    if (!loaded) {
      missing.value = 'No se encontró el escenario.'
      return
    }
    data.value = loaded
    seasons.value = loadedSeasons
  } catch {
    if (version === loadVersion) error.value = 'No se pudo cargar el escenario. Intentá de nuevo.'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

// La campaña nueva queda elegida. Se piden todas de nuevo
// porque la actual puede cambiar con ella
async function onSeasonCreated(created: Season) {
  addingSeason.value = false
  if (!data.value) return
  try {
    seasons.value = await listSeasons(data.value.scenario.id)
  } catch {
    await load()
  }
  selectedId.value = created.id
}

// La lista guarda la lluvia nueva para mostrarla al volver a esta campaña
function onRainfallSaved(saved: Season) {
  seasons.value = seasons.value.map((season) => (season.id === saved.id ? saved : season))
}

function openSector(unitId: number) {
  if (!data.value) return
  void router.push({
    name: 'sector',
    params: { scenarioId: data.value.scenario.id, unitId },
    query: keepSeason(route.query),
  })
}

watch(() => route.params.scenarioId, load, { immediate: true })
</script>

<template>
  <section class="scenario-page">
    <FarmBreadcrumb :steps="[{ label: data?.scenario.name ?? 'Escenario' }]" />
    <p v-if="loading">Cargando escenario…</p>
    <p v-else-if="missing" class="error" role="alert">{{ missing }}</p>
    <div v-else-if="error" role="alert">
      <p class="error">{{ error }}</p>
      <button type="button" class="btn" @click="load">Reintentar</button>
    </div>
    <template v-else-if="data">
      <header class="heading">
        <div>
          <h1>{{ data.scenario.name }}</h1>
          <p class="summary">
            Sectores <strong>{{ data.units.length }}</strong> · Superficie
            <strong>{{ hectares(totalArea) }} ha</strong>
          </p>
        </div>
        <div class="season-bar">
          <template v-if="seasons.length">
            <label for="season-select">Campaña</label>
            <select id="season-select" v-model="selectedId">
              <option v-for="season in newestFirst" :key="season.id" :value="season.id">
                {{ seasonName(season.start_date, season.end_date) }}
                {{ season.is_current ? '(actual)' : '' }}
              </option>
            </select>
          </template>
          <button type="button" class="btn" @click="addingSeason = true">Nueva campaña</button>
        </div>
      </header>

      <div class="overview">
        <div class="map-box panel">
          <UnitsMap
            :units="data.units"
            :draft="null"
            :editing-id="null"
            :water-points="data.waterPoints"
            read-only
            show-labels
            @select-unit="openSector"
          />
          <div class="map-legend">
            <span><i class="coverage-key"></i>Superficie aprovechable</span>
            <span><i class="water-key"></i>Aguada</span>
          </div>
        </div>

        <section class="campaign panel" aria-label="Campaña elegida">
          <template v-if="selected">
            <h2>
              Campaña {{ seasonName(selected.start_date, selected.end_date) }}
              <span v-if="selected.is_current" class="current">actual</span>
            </h2>
            <p class="hint">
              Del {{ formatDate(selected.start_date) }} al {{ formatDate(selected.end_date) }}
            </p>
            <SeasonRainfall
              :key="selected.id"
              :season-id="selected.id"
              :rainfall-mm="selected.rainfall_mm"
              @saved="onRainfallSaved"
            />
          </template>
          <p v-else class="hint">El escenario todavía no tiene campañas.</p>
        </section>
      </div>

      <div class="section-heading">
        <h2>Sectores</h2>
        <RouterLink
          class="btn"
          :to="{
            name: 'new-sector',
            params: { scenarioId: data.scenario.id },
            query: keepSeason(route.query),
          }"
        >
          Dibujar sector
        </RouterLink>
      </div>
      <div v-if="data.units.length" class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Sector</th>
              <th class="number">Superficie</th>
              <th class="number">Aprovechable</th>
              <th class="number">Aguadas</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="unit in data.units" :key="unit.id">
              <td>
                <RouterLink
                  :to="{
                    name: 'sector',
                    params: { scenarioId: data.scenario.id, unitId: unit.id },
                    query: keepSeason(route.query),
                  }"
                >
                  {{ unit.name }}
                </RouterLink>
              </td>
              <td class="number">{{ hectares(unit.area_ha) }} ha</td>
              <td class="number">{{ hectares(unit.usable_area_ha) }} ha</td>
              <td class="number">{{ waterPointCount(unit.id) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="hint">Todavía no hay sectores. Dibujá el primero.</p>

      <AppModal v-if="addingSeason" title="Nueva campaña" @close="addingSeason = false">
        <AddSeason :scenario-id="data.scenario.id" :seasons="seasons" @created="onSeasonCreated">
          <template #actions>
            <button type="button" class="btn" @click="addingSeason = false">Cancelar</button>
          </template>
        </AddSeason>
      </AppModal>
    </template>
  </section>
</template>

<style scoped>
.scenario-page {
  max-width: 1100px;
}

.heading,
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
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

.summary strong {
  color: var(--color-text);
}

.overview {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(260px, 1fr);
  gap: 16px;
  align-items: start;
  margin: 20px 0 28px;
}

.map-box {
  padding: 0;
  overflow: hidden;
}

.map-box :deep(.units-map) {
  border: 0;
  border-radius: 0;
}

.map-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 10px 16px;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.map-legend span {
  display: flex;
  align-items: center;
  gap: 6px;
}

.map-legend i {
  display: inline-block;
  width: 10px;
  height: 10px;
}

.coverage-key {
  background: #90b889;
  border-radius: 2px;
}

.water-key {
  background: #2678a7;
  border-radius: 50%;
}

.campaign {
  display: grid;
  gap: 6px;
}

.current {
  display: inline-block;
  margin-left: 6px;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 400;
}

.season-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.season-bar label {
  font-size: 0.9rem;
  font-weight: 600;
}

.season-bar select {
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
  font-size: 0.9rem;
}

.section-heading {
  margin-bottom: 10px;
}

@media (max-width: 800px) {
  .overview {
    grid-template-columns: 1fr;
  }
}
</style>

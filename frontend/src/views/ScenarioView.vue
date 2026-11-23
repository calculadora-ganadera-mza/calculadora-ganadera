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
import { hectares, routeId } from '@/utils/farm'
import { formatDate, seasonLabel, seasonName } from '@/utils/season'

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

const current = computed(() => seasons.value.find((season) => season.is_current))
const otherSeasons = computed(() => seasons.value.filter((season) => !season.is_current))
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

// La campaña actual puede cambiar con la nueva
async function onSeasonCreated() {
  addingSeason.value = false
  if (!data.value) return
  try {
    seasons.value = await listSeasons(data.value.scenario.id)
  } catch {
    await load()
  }
}

function openSector(unitId: number) {
  if (!data.value) return
  void router.push({ name: 'sector', params: { scenarioId: data.value.scenario.id, unitId } })
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
        <button type="button" class="btn" @click="addingSeason = true">Nueva campaña</button>
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

        <section class="campaign panel" aria-label="Campaña actual">
          <template v-if="current">
            <h2>
              Campaña {{ seasonName(current.start_date, current.end_date) }}
              <span class="current">actual</span>
            </h2>
            <p class="hint">
              Del {{ formatDate(current.start_date) }} al {{ formatDate(current.end_date) }}
            </p>
            <SeasonRainfall
              :key="current.id"
              :season-id="current.id"
              :rainfall-mm="current.rainfall_mm"
            />
          </template>
          <p v-else class="hint">El escenario todavía no tiene campañas.</p>
          <details v-if="otherSeasons.length" class="past-seasons">
            <summary>Otras campañas</summary>
            <ul>
              <li v-for="season in otherSeasons" :key="season.id">
                Campaña {{ seasonLabel(season.start_date, season.end_date) }}
              </li>
            </ul>
          </details>
        </section>
      </div>

      <div class="section-heading">
        <h2>Sectores</h2>
        <RouterLink
          class="btn"
          :to="{ name: 'new-sector', params: { scenarioId: data.scenario.id } }"
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
        <AddSeason :scenario-id="data.scenario.id" :seasons="seasons" @created="onSeasonCreated" />
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

.past-seasons {
  margin-top: 8px;
  color: var(--color-text-muted);
  font-size: 0.85rem;
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

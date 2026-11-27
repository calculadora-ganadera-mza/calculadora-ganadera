<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppModal from '@/components/AppModal.vue'
import FarmBreadcrumb from '@/components/FarmBreadcrumb.vue'
import HerdForm from '@/components/HerdForm.vue'
import UnitsMap from '@/components/UnitsMap.vue'
import { loadScenarioMap, type ScenarioMap } from '@/api/farm'
import {
  ApiError,
  deleteProductionUnit,
  updateProductionUnit,
  type PolygonGeoJSON,
} from '@/api/productionUnits'
import { listSeasons, type Season } from '@/api/scenarios'
import { waterRequest, type WaterPoint } from '@/api/waterPoints'
import { hectares, keepSeason, routeId } from '@/utils/farm'
import { pickSeason, seasonName } from '@/utils/season'

const route = useRoute()
const router = useRouter()
const data = ref<ScenarioMap>()
const season = ref<Season>()
const loading = ref(true)
// La carga falló y se puede reintentar
const error = ref('')
// La dirección trae un escenario o un sector que no existe: reintentar no sirve
const missing = ref('')
const actionError = ref('')
const saving = ref(false)
const mapRef = ref<InstanceType<typeof UnitsMap>>()
let loadVersion = 0

const unitId = computed(() => routeId(route.params.unitId))
const unit = computed(() => data.value?.units.find((item) => item.id === unitId.value))
// El mapa recibe siempre la misma lista para no redibujarse en cada cambio de la pantalla
const unitList = computed(() => (unit.value ? [unit.value] : []))
const neighbors = computed(() => (data.value?.units ?? []).filter((item) => item !== unit.value))
const ownPoints = computed<WaterPoint[]>(() =>
  (data.value?.waterPoints ?? []).filter((point) => point.production_unit_id === unitId.value),
)
// Aguadas de otros sectores que el servidor comparte con este
const sharedPoints = computed(() =>
  (data.value?.waterPoints ?? []).filter(
    (point) =>
      point.production_unit_id !== unitId.value &&
      point.shared &&
      unitId.value !== null &&
      point.neighbor_unit_ids.includes(unitId.value),
  ),
)
// Sin aguadas propias ni compartidas no hay superficie aprovechable
const withoutWater = computed(() => ownPoints.value.length + sharedPoints.value.length === 0)
const usablePercent = computed(() =>
  unit.value && unit.value.area_ha > 0
    ? Math.round((unit.value.usable_area_ha / unit.value.area_ha) * 100)
    : 0,
)
const refillTotal = computed(() =>
  ownPoints.value.reduce((total, point) => total + (point.refill_l_day ?? 0), 0),
)
// Aviso de la tarjeta de reposición; vacío si todas las aguadas tienen los litros
const refillWarning = computed(() => {
  const total = ownPoints.value.length
  const missingRefill = ownPoints.value.filter((point) => point.refill_l_day === null).length
  if (!total) return 'El sector no tiene aguadas.'
  if (!missingRefill) return ''
  if (total === 1) return 'Falta cargar los litros de la aguada.'
  if (missingRefill === total) return `Falta cargar los litros de las ${total} aguadas.`
  return `Falta cargar los litros de ${missingRefill} de las ${total} aguadas.`
})

// Con refresh no se vuelve a mostrar "Cargando" para no rearmar el mapa
async function load(refresh = false) {
  const version = ++loadVersion
  if (!refresh) {
    loading.value = true
    data.value = undefined
  }
  error.value = ''
  missing.value = ''
  const scenarioId = routeId(route.params.scenarioId)
  try {
    const loaded = scenarioId === null ? null : await loadScenarioMap(scenarioId)
    const seasons = loaded ? await listSeasons(loaded.scenario.id) : []
    if (version !== loadVersion) return
    if (!loaded) missing.value = 'No se encontró el escenario.'
    else if (!loaded.units.some((item) => item.id === unitId.value))
      missing.value = 'No se encontró este sector en el escenario.'
    data.value = loaded ?? undefined
    season.value = pickSeason(seasons, route.query.season)
  } catch {
    if (version === loadVersion) error.value = 'No se pudo cargar el sector. Volver a intentar.'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

// Cambiar el nombre
const renaming = ref(false)
const newName = ref('')
const renameError = ref('')

function openRename() {
  newName.value = unit.value?.name ?? ''
  renameError.value = ''
  renaming.value = true
}

async function saveName() {
  const current = unit.value
  const trimmed = newName.value.trim()
  if (!current) return
  if (!trimmed) {
    renameError.value = 'Falta el nombre del sector.'
    return
  }
  saving.value = true
  renameError.value = ''
  try {
    await updateProductionUnit(current.id, { name: trimmed, polygon: current.polygon })
    renaming.value = false
    await load(true)
  } catch (err) {
    renameError.value = err instanceof ApiError ? err.message : 'No se pudo cambiar el nombre.'
  } finally {
    saving.value = false
  }
}

// Editar el contorno: el resto de la pantalla queda bloqueado
const editingShape = ref(false)
const reshaped = ref<PolygonGeoJSON | null>(null)

function startShape() {
  reshaped.value = null
  actionError.value = ''
  editingShape.value = true
}

function cancelShape() {
  reshaped.value = null
  editingShape.value = false
}

async function saveShape() {
  const current = unit.value
  if (!current || !reshaped.value) {
    cancelShape()
    return
  }
  saving.value = true
  actionError.value = ''
  try {
    await updateProductionUnit(current.id, { name: current.name, polygon: reshaped.value })
    // La superficie y el alcance de las aguadas cambian con el contorno
    await load(true)
    cancelShape()
    // El contorno nuevo puede quedar fuera de la vista: el mapa se vuelve a encuadrar
    await nextTick()
    mapRef.value?.fitUnits?.()
  } catch (err) {
    actionError.value = err instanceof ApiError ? err.message : 'No se pudo guardar el contorno.'
  } finally {
    saving.value = false
  }
}

async function removePoint(point: WaterPoint) {
  if (!window.confirm(`¿Eliminar la aguada «${point.name}»?`)) return
  actionError.value = ''
  try {
    await waterRequest(`/water-points/${point.id}`, 'DELETE')
    await load(true)
  } catch (err) {
    actionError.value = err instanceof Error ? err.message : 'No se pudo eliminar la aguada.'
  }
}

async function removeUnit() {
  const current = unit.value
  if (!current || !data.value) return
  const question = `¿Eliminar el sector «${current.name}»? También se borran sus aguadas y rodeos. Los sectores vecinos perderán las aguadas compartidas.`
  if (!window.confirm(question)) return
  actionError.value = ''
  try {
    await deleteProductionUnit(current.id)
    await router.push({
      name: 'scenario',
      params: { scenarioId: data.value.scenario.id },
      query: keepSeason(route.query),
    })
  } catch (err) {
    actionError.value = err instanceof ApiError ? err.message : 'No se pudo eliminar el sector.'
  }
}

watch(
  () => [route.params.scenarioId, route.params.unitId, route.query.season],
  () => {
    cancelShape()
    void load()
  },
  { immediate: true },
)
</script>

<template>
  <section class="sector-page">
    <FarmBreadcrumb
      :class="{ locked: editingShape }"
      :inert="editingShape || undefined"
      :steps="[
        {
          label: data?.scenario.name ?? 'Escenario',
          to: {
            name: 'scenario',
            params: { scenarioId: route.params.scenarioId },
            query: keepSeason(route.query),
          },
        },
        { label: unit?.name ?? 'Sector' },
      ]"
    />
    <p v-if="loading">Cargando sector…</p>
    <p v-else-if="missing" class="error" role="alert">{{ missing }}</p>
    <div v-else-if="error" role="alert">
      <p class="error">{{ error }}</p>
      <button type="button" class="btn" @click="load()">Reintentar</button>
    </div>
    <template v-else-if="data && unit">
      <header class="heading" :class="{ locked: editingShape }" :inert="editingShape || undefined">
        <div>
          <div class="title">
            <h1>{{ unit.name }}</h1>
            <button type="button" class="text-button" @click="openRename">Editar</button>
          </div>
          <p v-if="season" class="hint season-meta">
            <span>Campaña {{ seasonName(season.start_date, season.end_date) }}</span>
            <RouterLink
              class="text-button"
              :to="{
                name: 'scenario',
                params: { scenarioId: data.scenario.id },
                query: keepSeason(route.query),
              }"
            >
              Cambiar campaña
            </RouterLink>
          </p>
        </div>
        <div class="actions">
          <button type="button" class="btn" @click="startShape">Editar contorno</button>
          <RouterLink
            v-if="season"
            class="btn btn-primary"
            :to="{
              name: 'carrying-capacity',
              query: { scenario: data.scenario.id, unit: unit.id, season: season.id },
            }"
          >
            Calcular
          </RouterLink>
        </div>
      </header>

      <div class="cards panel" :class="{ locked: editingShape }" :inert="editingShape || undefined">
        <div>
          <p class="card-label">Superficie total</p>
          <p class="card-value">{{ hectares(unit.area_ha) }} <small>ha</small></p>
        </div>
        <div>
          <p class="card-label">Superficie aprovechable</p>
          <p class="card-value">{{ hectares(unit.usable_area_ha) }} <small>ha</small></p>
          <p v-if="withoutWater" class="hint">
            Sin aguadas no hay superficie aprovechable: se mide dentro del alcance de cada aguada.
            <RouterLink
              :to="{
                name: 'new-water-point',
                params: { scenarioId: data.scenario.id, unitId: unit.id },
                query: keepSeason(route.query),
              }"
            >
              Ubicar aguada
            </RouterLink>
          </p>
          <p v-else class="hint">{{ usablePercent }} % del total</p>
        </div>
        <div>
          <p class="card-label">Reposición de las aguadas</p>
          <p class="card-value">{{ refillTotal.toLocaleString('es-AR') }} <small>L/día</small></p>
          <p v-if="refillWarning" class="warning">{{ refillWarning }}</p>
          <p v-else class="hint">
            {{ ownPoints.length }} {{ ownPoints.length === 1 ? 'aguada' : 'aguadas' }}
          </p>
        </div>
      </div>

      <div class="map-box panel" :class="{ editing: editingShape }">
        <div v-if="editingShape" class="shape-bar">
          <p>Arrastrar las esquinas. Tocar un borde agrega una esquina.</p>
          <button type="button" class="btn btn-primary" :disabled="saving" @click="saveShape">
            {{ saving ? 'Guardando…' : 'Guardar contorno' }}
          </button>
          <button type="button" class="btn" :disabled="saving" @click="cancelShape">
            Cancelar
          </button>
        </div>
        <UnitsMap
          ref="mapRef"
          :units="unitList"
          :reference-units="neighbors"
          :draft="null"
          :editing-id="editingShape ? unit.id : null"
          :water-points="ownPoints"
          :shared-water-points="sharedPoints"
          read-only
          @reshape="reshaped = $event"
        />
        <div class="map-legend">
          <span v-if="!withoutWater"><i class="water-key"></i>Aguada</span>
          <span v-if="unit.usable_area_ha > 0">
            <i class="coverage-key"></i>Superficie aprovechable
          </span>
          <span v-if="neighbors.length"><i class="neighbor-key"></i>Sector vecino</span>
        </div>
      </div>
      <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>

      <div class="rest" :class="{ locked: editingShape }" :inert="editingShape || undefined">
        <div class="section-heading">
          <h2>Aguadas</h2>
          <RouterLink
            class="btn"
            :to="{
              name: 'new-water-point',
              params: { scenarioId: data.scenario.id, unitId: unit.id },
              query: keepSeason(route.query),
            }"
          >
            Ubicar aguada
          </RouterLink>
        </div>
        <div v-if="ownPoints.length" class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Aguada</th>
                <th class="number">Repone</th>
                <th>Compartida</th>
                <th><span class="visually-hidden">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="point in ownPoints" :key="point.id">
                <td>
                  {{ point.name }}
                  <p v-if="point.shared && !point.neighbor_unit_ids.length" class="warning">
                    Esta aguada ya no está en el límite con otro sector y no se está compartiendo.
                  </p>
                </td>
                <td class="number">
                  {{
                    point.refill_l_day === null
                      ? 'Sin cargar'
                      : `${point.refill_l_day.toLocaleString('es-AR')} L/día`
                  }}
                </td>
                <td>{{ point.shared ? 'Sí' : 'No' }}</td>
                <td class="row-actions">
                  <RouterLink
                    class="text-button"
                    :to="{
                      name: 'water-point',
                      params: {
                        scenarioId: data.scenario.id,
                        unitId: unit.id,
                        waterPointId: point.id,
                      },
                      query: keepSeason(route.query),
                    }"
                  >
                    Editar
                  </RouterLink>
                  <button type="button" class="text-button danger" @click="removePoint(point)">
                    Eliminar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="hint">Este sector no tiene aguadas.</p>

        <h2 class="herd-title">
          Rodeo de la campaña{{
            season ? ` ${seasonName(season.start_date, season.end_date)}` : ''
          }}
        </h2>
        <HerdForm v-if="season" :key="season.id" :season-id="season.id" :unit-id="unit.id" />
        <p v-else class="hint">El escenario no tiene una campaña para cargar el rodeo.</p>

        <div class="danger-zone">
          <button type="button" class="text-button danger" @click="removeUnit">
            Eliminar sector
          </button>
        </div>
      </div>

      <AppModal v-if="renaming" title="Nombre del sector" @close="renaming = false">
        <form class="rename" novalidate @submit.prevent="saveName">
          <div class="field">
            <label for="unit-new-name">Nombre</label>
            <input id="unit-new-name" v-model="newName" maxlength="100" autocomplete="off" />
          </div>
          <p v-if="renameError" class="error" role="alert">{{ renameError }}</p>
          <div class="actions">
            <button class="btn btn-primary" :disabled="saving">Guardar</button>
            <button type="button" class="btn" @click="renaming = false">Cancelar</button>
          </div>
        </form>
      </AppModal>
    </template>
  </section>
</template>

<style scoped>
.sector-page {
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

.title {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.season-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 16px;
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

.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 18px 0;
}

.cards p {
  margin: 0;
}

.card-label {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.card-value {
  font-size: 1.4rem;
  font-weight: 700;
}

.card-value small {
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 400;
}

.warning {
  margin: 4px 0 0;
  color: var(--color-warning);
  font-size: 0.85rem;
}

.map-box {
  padding: 0;
  overflow: hidden;
}

.map-box.editing {
  border: 2px solid var(--color-primary);
}

.map-box :deep(.units-map) {
  border: 0;
  border-radius: 0;
}

.shape-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
}

.shape-bar p {
  flex: 1;
  margin: 0;
  font-size: 0.85rem;
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

.water-key {
  background: #2678a7;
  border-radius: 50%;
}

.coverage-key {
  background: #90b889;
  border-radius: 2px;
}

.neighbor-key {
  border: 1px dashed #376a32;
}

.rest {
  margin-top: 24px;
}

.section-heading {
  margin-bottom: 10px;
}

.row-actions {
  display: flex;
  justify-content: flex-end;
  gap: 14px;
}

.herd-title {
  margin: 28px 0 10px;
}

.danger-zone {
  margin-top: 32px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.locked {
  opacity: 0.45;
}

.rename {
  display: grid;
  gap: 14px;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
}

@media (max-width: 700px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>

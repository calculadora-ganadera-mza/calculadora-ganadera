<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import WaterPoints from './WaterPoints.vue'
import { confirmSharing, waterRequest, type WaterPoint } from '@/api/waterPoints'
import type { Position } from '@/api/productionUnits'
import UnitsMap from './UnitsMap.vue'
import HerdForm from './HerdForm.vue'
import {
  ApiError,
  createProductionUnit,
  deleteProductionUnit,
  listProductionUnits,
  updateProductionUnit,
  type PolygonGeoJSON,
  type ProductionUnit,
} from '@/api/productionUnits'

// seasonId: campaña en la que se cargan los animales de cada sector
const props = defineProps<{
  scenarioId: number
  seasonId?: number
  overview?: boolean
  unitId?: number
}>()
const emit = defineEmits<{ removed: [] }>()
const visibleUnits = computed(() =>
  props.unitId === undefined ? units.value : units.value.filter((unit) => unit.id === props.unitId),
)

const selectedWaterId = ref<number | null>(null)
const waterMode = ref(false)
const selectedUnit = computed(() => units.value.find((u) => u.id === waterUnitId.value))
const waterUnitId = ref<number | null>(null)
const pointsByUnit = ref<Record<number, WaterPoint[]>>({})
const waterPoints = computed(() =>
  props.unitId === undefined
    ? Object.values(pointsByUnit.value).flat()
    : (pointsByUnit.value[props.unitId] ?? []),
)
// El servidor determina qué vecinos reciben el aporte de cada aguada.
const sharedWaterPoints = computed(() => {
  const unitId = props.unitId
  if (unitId === undefined) return []
  return Object.entries(pointsByUnit.value)
    .filter(([ownerId]) => Number(ownerId) !== unitId)
    .flatMap(([, points]) => points)
    .filter((point) => point.shared && point.neighbor_unit_ids.includes(unitId))
})
const mapRef = ref<InstanceType<typeof UnitsMap>>()
const waterRefs = ref<Record<number, InstanceType<typeof WaterPoints>>>({})
function focusUnit(id: number) {
  if (props.overview) return
  selectWater(id)
  mapRef.value?.focusUnit?.(id)
}
const creatingWater = ref(false)
const newWaterName = ref('')
const newWaterRefill = ref<number | ''>('')
function addWater(id: number) {
  waterRefs.value[waterUnitId.value ?? -1]?.cancel?.()
  cancelDraft()
  cancelEditing()
  waterUnitId.value = id
  mapRef.value?.focusUnit?.(id)
  waterPosition.value = null
  editingWaterId.value = null
  selectedWaterId.value = null
  creatingWater.value = true
  newWaterName.value = `Aguada ${waterPoints.value.length + 1}`
  newWaterRefill.value = ''
  waterMode.value = true
  actionError.value = ''
}
function cancelWaterPlacement() {
  if (saving.value) return
  if (creatingWater.value) {
    creatingWater.value = false
    waterMode.value = false
    waterPosition.value = null
    actionError.value = ''
  } else waterRefs.value[waterUnitId.value ?? -1]?.cancel?.()
}
async function confirmWaterPlacement() {
  if (saving.value) return
  if (!creatingWater.value) {
    waterRefs.value[waterUnitId.value ?? -1]?.confirmPosition()
    return
  }
  const unit = selectedUnit.value
  const position = waterPosition.value
  if (!unit || !position) {
    actionError.value = 'Marcá la ubicación de la aguada en el sector elegido.'
    return
  }
  if (!newWaterName.value.trim()) {
    actionError.value = 'Completá el nombre de la aguada.'
    return
  }
  if (
    newWaterRefill.value !== '' &&
    (!Number.isFinite(Number(newWaterRefill.value)) || Number(newWaterRefill.value) <= 0)
  ) {
    actionError.value = 'Los litros deben ser mayores que cero.'
    return
  }
  saving.value = true
  actionError.value = ''
  try {
    let point = await waterRequest<WaterPoint>(
      `/production-units/${unit.id}/water-points`,
      'POST',
      {
        shared: false,
        name: newWaterName.value.trim(),
        location: { type: 'Point', coordinates: position },
        refill_l_day: newWaterRefill.value === '' ? null : Number(newWaterRefill.value),
      },
    )
    try {
      point = await confirmSharing(point)
    } catch (err) {
      actionError.value =
        err instanceof Error ? err.message : 'No se pudo confirmar el uso compartido.'
    }
    pointsByUnit.value[unit.id] = [...(pointsByUnit.value[unit.id] ?? []), point]
    creatingWater.value = false
    waterMode.value = false
    selectWater(unit.id)
    selectedWaterId.value = point.id
    waterPosition.value = null
    await refreshUnits()
  } catch (err) {
    waterPosition.value = null
    actionError.value =
      err instanceof Error ? err.message : 'No se pudo guardar la aguada. Intentá nuevamente.'
  } finally {
    saving.value = false
  }
}
const waterPosition = ref<Position | null>(null)
const editingWaterId = ref<number | null>(null)
function selectWater(id: number | null) {
  if (creatingWater.value) return
  if (waterUnitId.value === id) return
  waterRefs.value[waterUnitId.value ?? -1]?.cancel?.()
  selectedWaterId.value = null
  waterMode.value = false
  waterUnitId.value = id

  waterPosition.value = null
  editingWaterId.value = null
  editingId.value = null
  draft.value = null
}
function editWater(id: number | null) {
  if (id !== null) {
    // Cambiar de modo descarta el borrador de contorno anterior.
    cancelDraft()
    cancelEditing()
  }
  editingWaterId.value = id
  waterPosition.value = null
}
const refreshError = ref('')
const refreshing = ref(false)
let refreshVersion = 0
async function refreshUnits(): Promise<boolean> {
  const version = ++refreshVersion
  refreshing.value = true
  refreshError.value = ''
  try {
    const [updatedUnits, points] = await Promise.all([
      listProductionUnits(props.scenarioId),
      waterRequest<(WaterPoint & { production_unit_id: number })[]>(
        `/scenarios/${props.scenarioId}/water-points`,
      ),
    ])
    if (version !== refreshVersion) return true
    const grouped: Record<number, WaterPoint[]> = {}
    for (const unit of updatedUnits) grouped[unit.id] = []
    for (const point of points) grouped[point.production_unit_id]?.push(point)
    pointsByUnit.value = grouped
    units.value = updatedUnits
    return true
  } catch {
    if (version === refreshVersion) {
      refreshError.value =
        'No se pudieron actualizar las aguadas y la superficie. Los datos mostrados pueden estar desactualizados.'
    }
    return false
  } finally {
    if (version === refreshVersion) refreshing.value = false
  }
}
const units = ref<ProductionUnit[]>([])
const loading = ref(true)
const loadError = ref('')
const actionError = ref('')
const saving = ref(false)
// Contorno recién dibujado, a la espera de un nombre
const draft = ref<PolygonGeoJSON | null>(null)
const draftName = ref('')
//Sector con el contorno en edición y el contorno nuevo, si se movió
const editingId = ref<number | null>(null)
const reshaped = ref<PolygonGeoJSON | null>(null)

function hectares(value: number): string {
  return value.toLocaleString('es-AR', { maximumFractionDigits: 1 })
}

function messageOf(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    if (!(await refreshUnits())) loadError.value = 'No se pudieron cargar los sectores.'
  } catch {
    loadError.value = 'No se pudieron cargar los sectores.'
  } finally {
    loading.value = false
  }
}

function onDraw(polygon: PolygonGeoJSON) {
  draft.value = polygon
  editingId.value = null
  actionError.value = ''
}

function cancelDraft() {
  draft.value = null
  mapRef.value?.cancelDraw?.()
  actionError.value = ''
}

async function saveDraft() {
  const name = draftName.value.trim()
  if (!name) {
    actionError.value = 'Falta el nombre del sector.'
    return
  }
  const polygon = draft.value
  if (!polygon) return
  saving.value = true
  actionError.value = ''
  try {
    const unit = await createProductionUnit(props.scenarioId, { name, polygon })
    units.value = [...units.value, unit]
    // Solo se limpia si no se dibujó otro contorno mientras se guardaba
    if (draft.value === polygon) {
      draft.value = null
      focusUnit(unit.id)
    }
    await refreshUnits()
  } catch (err) {
    actionError.value = messageOf(err, 'No se pudo guardar el sector.')
  } finally {
    saving.value = false
  }
}

function startEditing(unit: ProductionUnit) {
  cancelWaterPlacement()
  focusUnit(unit.id)
  selectWater(unit.id)
  waterRefs.value[unit.id]?.cancel?.()
  editingId.value = unit.id
  reshaped.value = null
  draft.value = null
  actionError.value = ''
}

function cancelEditing() {
  reshaped.value = null
  // Al dejar de editar, el mapa vuelve a dibujar el contorno guardado
  editingId.value = null
  actionError.value = ''
}

async function saveShape(unit: ProductionUnit) {
  const polygon = reshaped.value
  if (!polygon) {
    cancelEditing()
    return
  }
  saving.value = true
  actionError.value = ''
  try {
    const updated = await updateProductionUnit(unit.id, {
      name: unit.name,
      polygon,
    })
    units.value = units.value.map((item) => (item.id === updated.id ? updated : item))
    await refreshUnits()
    // Solo se cierra si no se empezó otra edición mientras se guardaba
    if (editingId.value === unit.id && reshaped.value === polygon) editingId.value = null
  } catch (err) {
    cancelEditing()
    reshaped.value = null
    actionError.value = messageOf(err, 'No se pudo guardar el contorno.')
  } finally {
    saving.value = false
  }
}

async function remove(unit: ProductionUnit) {
  const question = `¿Eliminar el sector «${unit.name}»? También se borran sus aguadas y rodeos. Los sectores vecinos perderán las aguadas compartidas.`
  if (!window.confirm(question)) return
  actionError.value = ''
  try {
    await deleteProductionUnit(unit.id)
    if (waterUnitId.value === unit.id) selectWater(null)
    delete pointsByUnit.value[unit.id]
    units.value = units.value.filter((item) => item.id !== unit.id)
    if (editingId.value === unit.id) editingId.value = null
    await refreshUnits()
    if (props.unitId === unit.id) emit('removed')
  } catch (err) {
    actionError.value = messageOf(err, 'No se pudo eliminar el sector.')
  }
}

onMounted(load)
</script>

<template>
  <section class="units" :class="{ overview }">
    <header class="sector-heading">
      <h2 v-if="overview">Sectores del escenario</h2>
      <h1 v-else-if="unitId">{{ visibleUnits[0]?.name ?? 'Administrar sector' }}</h1>
      <h3 v-else>Sectores y aguadas</h3>
    </header>
    <p v-if="loading">Cargando sectores…</p>
    <div v-else-if="loadError" role="alert">
      {{ loadError }} <button @click="load">Reintentar</button>
    </div>
    <p v-else-if="unitId && !visibleUnits.length" role="status">
      No se encontró este sector en el establecimiento.
    </p>
    <template v-else>
      <p v-if="!overview" class="hint">
        <template v-if="unitId === undefined">
          Para agregar un sector, dibujá su contorno con la herramienta de polígono del mapa.
        </template>
        Para agregar una aguada, elegí «Ubicar aguada» en el sector correspondiente.
      </p>
      <p v-if="refreshing" role="status">Actualizando aguadas y superficie…</p>
      <p v-if="refreshError" role="alert" class="error">
        {{ refreshError }}
        <button :disabled="refreshing" @click="refreshUnits">Reintentar actualización</button>
      </p>
      <UnitsMap
        ref="mapRef"
        :units="visibleUnits"
        :reference-units="unitId === undefined ? [] : units.filter((unit) => unit.id !== unitId)"
        :draft="draft"
        :editing-id="editingId"
        :read-only="!overview && unitId !== undefined"
        :show-labels="overview"
        :water-points="waterPoints"
        :shared-water-points="sharedWaterPoints"
        :water-mode="waterMode"
        :selected-unit-id="waterUnitId"
        :selected-water-id="selectedWaterId"
        :editing-water-id="editingWaterId"
        :water-position="waterPosition"
        @select-unit="focusUnit"
        @select-water="
          (id) => {
            const owner = units.find((u) => pointsByUnit[u.id]?.some((p) => p.id === id))
            if (owner) focusUnit(owner.id)
            selectedWaterId = id
          }
        "
        @locate="waterPosition = $event"
        @draw="onDraw"
        @reshape="reshaped = $event"
      />
      <div v-if="waterMode" id="crosshair-action-bar" class="map-bar water-bar">
        <div>
          <strong>Ubicando aguada en {{ selectedUnit?.name }}</strong>
          <p class="hint">Marcá el punto en el mapa o arrastralo para ajustar su ubicación.</p>
        </div>
        <template v-if="creatingWater">
          <label class="placement-field"
            >Nombre<input v-model="newWaterName" maxlength="100" :disabled="saving"
          /></label>
          <label class="placement-field"
            >Reposición (L/día)<input
              v-model="newWaterRefill"
              type="number"
              min="0"
              step="any"
              placeholder="(Opcional)"
              :disabled="saving"
          /></label>
        </template>
        <button :disabled="saving" @click="cancelWaterPlacement">Cancelar</button>
        <button class="sky" :disabled="saving || !waterPosition" @click="confirmWaterPlacement">
          Confirmar
        </button>
      </div>

      <form v-if="draft" class="draft" @submit.prevent="saveDraft">
        <label for="unit-name">Nombre del sector</label>
        <input id="unit-name" v-model="draftName" maxlength="100" />
        <button :disabled="saving">Guardar sector</button>
        <button type="button" @click="cancelDraft">Cancelar</button>
      </form>
      <p v-if="actionError" role="alert" class="error">{{ actionError }}</p>
      <div v-if="overview" class="map-legend">
        <span><i class="coverage-key"></i>Superficie aprovechable</span>
        <span><i class="water-key"></i>Aguada</span>
      </div>
      <ul v-if="overview" class="sector-links">
        <li v-for="unit in visibleUnits" :key="unit.id">
          <RouterLink
            :to="{ name: 'sector', params: { scenarioId: props.scenarioId, unitId: unit.id } }"
          >
            <span>{{ unit.name }}</span
            ><span aria-hidden="true">›</span>
          </RouterLink>
        </li>
      </ul>
      <ul v-else class="unit-list">
        <li
          v-for="unit in visibleUnits"
          :key="unit.id"
          :class="{ active: waterUnitId === unit.id }"
        >
          <div class="unit-heading">
            <button class="unit-name" @click="focusUnit(unit.id)">{{ unit.name }}</button>
            <span
              >{{ hectares(unit.area_ha) }} ha — {{ hectares(unit.usable_area_ha) }} ha
              aprovechables</span
            >
            <template v-if="editingId === unit.id">
              <button :disabled="saving" @click="saveShape(unit)">Guardar contorno</button>
              <button @click="cancelEditing">Cancelar</button>
            </template>
            <button v-else @click="startEditing(unit)">Editar contorno</button>
            <button @click="remove(unit)">Eliminar</button>
          </div>
          <WaterPoints
            :ref="
              (el) => {
                if (el) waterRefs[unit.id] = el as InstanceType<typeof WaterPoints>
              }
            "
            global-creation
            @create-requested="addWater(unit.id)"
            :saved-points="pointsByUnit[unit.id] ?? []"
            :unit-id="unit.id"
            :unit-name="unit.name"
            :selected-point-id="waterUnitId === unit.id ? selectedWaterId : null"
            :position="waterUnitId === unit.id ? waterPosition : null"
            @select="
              (id) => {
                focusUnit(unit.id)
                selectedWaterId = id
              }
            "
            @points="pointsByUnit[unit.id] = $event"
            @changed="refreshUnits"
            @reset-position="waterPosition = null"
            @reload="refreshUnits"
            @mode="
              (active) => {
                // El alta pertenece al padre; cancelar la lista no la cierra.
                if (creatingWater) return
                if (active) {
                  if (waterUnitId !== unit.id) selectWater(unit.id)
                  mapRef?.cancelDraw?.()
                }
                if (waterUnitId === unit.id) waterMode = active
              }
            "
            @edit="
              (id) => {
                if (!creatingWater && waterUnitId === unit.id) editWater(id)
              }
            "
          />
          <HerdForm
            v-if="seasonId && editingId !== unit.id"
            :season-id="seasonId"
            :unit-id="unit.id"
          />
        </li>
      </ul>
      <p v-if="!visibleUnits.length">Todavía no hay sectores.</p>
    </template>
  </section>
</template>
<style scoped>
.units {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.units h3 {
  margin: 0;
  font-size: 1rem;
}

.hint {
  margin: 0;
  color: var(--color-text-muted);
}

.draft,
.unit-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.draft input,
.placement-field input {
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
}

.unit-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.unit-list > li {
  display: grid;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
}
.unit-name {
  font-weight: 600;
}
.map-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 8px;
}
.placement-field {
  display: grid;
  gap: 4px;
}

.error {
  margin: 0;
  color: var(--color-danger);
}

button {
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  cursor: pointer;
}

button:disabled {
  opacity: 0.6;
  cursor: default;
}

.overview {
  gap: 0;
  margin-top: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 11px;
  overflow: hidden;
}
.sector-heading {
  padding: 16px;
}
.sector-heading h1,
.sector-heading h2,
.sector-heading h3 {
  margin: 0;
}
.sector-heading h2 {
  font-size: 0.95rem;
}
.overview :deep(.units-map) {
  border: 0;
  border-radius: 0;
}
.overview > .draft,
.overview > .error,
.overview > [role='status'] {
  margin: 12px 16px;
}
.map-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 12px 16px;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  border-bottom: 1px solid var(--color-border);
}
.map-legend span {
  display: flex;
  align-items: center;
  gap: 6px;
}
.map-legend i {
  width: 10px;
  height: 10px;
  display: inline-block;
}
.coverage-key {
  background: #90b889;
  border-radius: 2px;
}
.water-key {
  background: #2678a7;
  border-radius: 50%;
}
.sector-links {
  list-style: none;
  margin: 0;
  padding: 0;
}
.sector-links li + li {
  border-top: 1px solid var(--color-border);
}
.sector-links a {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 16px;
  color: var(--color-text);
  font-weight: 600;
  text-decoration: none;
}
.sector-links a:hover,
.sector-links a:focus-visible {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
</style>

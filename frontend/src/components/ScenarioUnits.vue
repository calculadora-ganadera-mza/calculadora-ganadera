<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import WaterPoints from './WaterPoints.vue'
import { confirmSharing, waterRequest, type WaterPoint } from '@/api/waterPoints'
import { containsPosition, distanceToPolygon } from '@/utils/geometry'
import type { Position } from '@/api/productionUnits'
import UnitsMap from './UnitsMap.vue'
import {
  ApiError,
  createProductionUnit,
  deleteProductionUnit,
  listProductionUnits,
  updateProductionUnit,
  type PolygonGeoJSON,
  type ProductionUnit,
} from '@/api/productionUnits'

const props = defineProps<{ scenarioId: number }>()

const selectedWaterId = ref<number | null>(null)
const waterMode = ref(false)
const selectedUnit = computed(() => units.value.find((u) => u.id === waterUnitId.value))
const waterUnitId = ref<number | null>(null)
const pointsByUnit = ref<Record<number, WaterPoint[]>>({})
const waterPoints = computed(() => Object.values(pointsByUnit.value).flat())
const mapRef = ref<InstanceType<typeof UnitsMap>>()
const waterRefs = ref<Record<number, InstanceType<typeof WaterPoints>>>({})
const layout = ref('grid')
const cards = ref<HTMLElement>()
const drawing = ref(false)
function coverage(unit: ProductionUnit) {
  return unit.area_ha ? Math.round((unit.usable_area_ha / unit.area_ha) * 100) : 0
}
function focusUnit(id: number) {
  selectWater(id)
  mapRef.value?.focusUnit?.(id)
  if (layout.value === 'carousel')
    document
      .getElementById(`card-${id}`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
}
const creatingWater = ref(false)
const newWaterName = ref('')
const newWaterRefill = ref<number | ''>('')
const placingUnit = computed(() => {
  if (!waterPosition.value) return undefined
  const position = waterPosition.value
  return (
    units.value.find((unit) => containsPosition(unit.polygon, position)) ??
    units.value
      .map((unit) => ({ unit, distance: distanceToPolygon(unit.polygon, position) }))
      .filter(({ distance }) => distance <= 5)
      .sort((a, b) => a.distance - b.distance || a.unit.id - b.unit.id)[0]?.unit
  )
})
function addWater(id?: number) {
  waterRefs.value[waterUnitId.value ?? -1]?.cancel?.()
  cancelDraft()
  cancelEditing()
  if (id !== undefined) mapRef.value?.focusUnit?.(id)
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
  const unit = placingUnit.value
  const position = waterPosition.value
  if (!unit || !position) {
    actionError.value = 'Ubicá el punto dentro de un sector o hasta 5 m de su borde.'
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
function beginDraw() {
  cancelWaterPlacement()
  waterRefs.value[waterUnitId.value ?? -1]?.cancel?.()
  selectWater(null)
  drawing.value = true
  mapRef.value?.startDraw?.()
}
function step(direction: number) {
  const index = units.value.findIndex((u) => u.id === waterUnitId.value)
  const unit = units.value[(index + direction + units.value.length) % units.value.length]
  if (unit) focusUnit(unit.id)
}
function syncScroll() {
  if (creatingWater.value || layout.value !== 'carousel' || !cards.value) return
  const rect = cards.value.getBoundingClientRect()
  let nearest: ProductionUnit | undefined
  let distance = Infinity
  for (const unit of units.value) {
    const card = document.getElementById(`card-${unit.id}`)
    if (!card) continue
    const d = Math.abs(card.getBoundingClientRect().left - rect.left)
    if (d < distance) {
      distance = d
      nearest = unit
    }
  }
  if (nearest && nearest.id !== waterUnitId.value) {
    selectWater(nearest.id)
    mapRef.value?.focusUnit?.(nearest.id)
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
  drawing.value = true
  draft.value = polygon
  editingId.value = null
  actionError.value = ''
}

function cancelDraft() {
  draft.value = null
  drawing.value = false
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
      drawing.value = false
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
  } catch (err) {
    actionError.value = messageOf(err, 'No se pudo eliminar el sector.')
  }
}

onMounted(load)
</script>

<template>
  <section class="units agro">
    <h3>Sectores y Aguadas</h3>
    <p v-if="loading">Cargando sectores…</p>
    <div v-else-if="loadError" role="alert">
      {{ loadError }} <button @click="load">Reintentar</button>
    </div>
    <template v-else>
      <p v-if="refreshing" role="status">Actualizando aguadas y superficie…</p>
      <p v-if="refreshError" role="alert" class="error">
        {{ refreshError }}
        <button :disabled="refreshing" @click="refreshUnits">Reintentar actualización</button>
      </p>
      <div class="map-wrapper">
        <UnitsMap
          ref="mapRef"
          :units="units"
          :draft="draft"
          :editing-id="editingId"
          :water-points="waterPoints"
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
        <div class="map-actions">
          <button @click="beginDraw">⬡ + Lote</button
          ><button class="accent" :disabled="!units.length" @click="addWater()">💧 + Aguada</button>
        </div>
        <div v-if="waterMode" id="crosshair-overlay">
          <span
            >Tocá el mapa para ubicar la aguada. Arrastrá el punto para ajustarlo al borde.</span
          >
        </div>
      </div>
      <div v-if="waterMode" id="crosshair-action-bar" class="map-bar water-bar">
        <div>
          <strong>{{
            creatingWater
              ? placingUnit
                ? `Nueva aguada en ${placingUnit.name}`
                : 'Ubicá la aguada dentro de un sector o hasta 5 m del borde'
              : `Ubicando aguada para ${selectedUnit?.name}`
          }}</strong>
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
        <button
          class="sky"
          :disabled="saving || (creatingWater && !placingUnit)"
          @click="confirmWaterPlacement"
        >
          Confirmar
        </button>
      </div>
      <form
        v-else-if="drawing || draft"
        id="draw-lote-bar"
        class="map-bar"
        @submit.prevent="draft && saveDraft()"
      >
        <label class="lote-name-field" for="unit-name">
          <input id="unit-name" v-model="draftName" placeholder="Nombre del lote" maxlength="100" />
        </label>
        <button type="button" aria-label="Deshacer último punto" @click="mapRef?.undoDraw()">
          ↶</button
        ><button type="button" @click="cancelDraft">Cancelar</button
        ><button class="primary" :disabled="saving || !draft">Guardar lote</button>
      </form>
      <p v-if="actionError" role="alert" class="error">{{ actionError }}</p>
      <header class="diagnosis-header">
        <h3>
          Diagnóstico por Lote <span class="badge">{{ units.length }} lotes</span>
        </h3>
        <div class="view-toggle">
          <button :aria-pressed="layout === 'grid'" @click="layout = 'grid'">▦ Tarjetas</button
          ><button :aria-pressed="layout === 'carousel'" @click="layout = 'carousel'">
            ↔ Carrusel
          </button>
        </div>
      </header>
      <div ref="cards" class="lote-cards" :class="layout" @scroll.passive="syncScroll">
        <article
          v-for="unit in units"
          :id="`card-${unit.id}`"
          :key="unit.id"
          class="lote-card"
          :class="{ active: waterUnitId === unit.id }"
        >
          <div class="card-heading">
            <div>
              <button class="lote-name" @click="focusUnit(unit.id)">{{ unit.name }} ⌖</button>
              <p>
                {{ hectares(unit.area_ha) }} ha — {{ hectares(unit.usable_area_ha) }} ha
                aprovechables
              </p>
            </div>
            <span class="badge"
              >{{ coverage(unit) }}% {{ coverage(unit) ? 'cubierto' : 'sin agua' }}</span
            >
          </div>
          <div>
            <div
              class="progress"
              role="progressbar"
              :aria-valuenow="coverage(unit)"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="`Cobertura de ${unit.name}`"
            >
              <div :style="{ width: Math.min(100, coverage(unit)) + '%' }"></div>
            </div>
            <div class="coverage-legend">
              <span
                >Aprovechable: <b>{{ hectares(unit.usable_area_ha) }} ha</b></span
              ><span
                >Sin agua:
                <em>{{ hectares(Math.max(0, unit.area_ha - unit.usable_area_ha)) }} ha</em></span
              >
            </div>
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
            @reload="refreshUnits"
            @mode="
              (active) => {
                // El alta global pertenece al padre; cancelar la tarjeta no la cierra.
                if (creatingWater) return
                if (active) {
                  if (waterUnitId !== unit.id) selectWater(unit.id)
                  mapRef?.cancelDraw?.()
                  drawing = false
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
          <footer>
            <template v-if="editingId === unit.id"
              ><button :disabled="saving" @click="saveShape(unit)">Guardar contorno</button
              ><button @click="cancelEditing">Cancelar</button></template
            ><button v-else class="shape" @click="startEditing(unit)">Editar contorno</button
            ><button class="delete" @click="remove(unit)">Eliminar</button>
          </footer>
        </article>
      </div>
      <p v-if="!units.length">Todavía no hay lotes. Usá + Lote para dibujar el primero.</p>
      <nav v-if="layout === 'carousel' && units.length" class="carousel-nav" aria-label="Lotes">
        <button aria-label="Lote anterior" @click="step(-1)">‹</button
        ><button
          v-for="unit in units"
          :key="unit.id"
          :aria-label="unit.name"
          :aria-current="waterUnitId === unit.id"
          class="dot"
          @click="focusUnit(unit.id)"
        ></button
        ><button aria-label="Lote siguiente" @click="step(1)">›</button>
      </nav>
    </template>
  </section>
</template>
<style scoped src="../assets/aguadas.css"></style>

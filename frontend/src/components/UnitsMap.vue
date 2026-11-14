<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import '@geoman-io/leaflet-geoman-free'
import 'leaflet/dist/leaflet.css'
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css'
import type { WaterPoint } from '@/api/waterPoints'
import type { Position } from '@/api/productionUnits'
import type { PolygonGeoJSON, ProductionUnit } from '@/api/productionUnits'

const props = defineProps<{
  selectedUnitId?: number | null
  selectedWaterId?: number | null
  waterPoints?: WaterPoint[]
  waterMode?: boolean
  editingWaterId?: number | null
  waterPosition?: Position | null
  units: ProductionUnit[]
  // Contorno dibujado que todavía no se guardó
  draft: PolygonGeoJSON | null
  // Sector con el contorno en edición, o null si no se edita ninguno
  editingId: number | null
}>()

const emit = defineEmits<{
  selectUnit: [id: number]
  selectWater: [id: number]
  locate: [position: Position]
  draw: [polygon: PolygonGeoJSON]
  reshape: [polygon: PolygonGeoJSON]
}>()

function focusUnit(id: number) {
  const unit = props.units.find((u) => u.id === id)
  if (unit && map)
    map.fitBounds(toLayer(unit.polygon).getBounds(), { padding: [35, 35], maxZoom: 14 })
}
function startDraw() {
  map?.pm.enableDraw('Polygon', { snappable: true })
}
function cancelDraw() {
  map?.pm.disableDraw()
}
function undoDraw() {
  const draw = map?.pm.Draw.Polygon as unknown as { _removeLastVertex: () => void }
  draw?._removeLastVertex()
}
defineExpose({ focusUnit, startDraw, cancelDraw, undoDraw })
watch(
  () => props.waterMode,
  (active) => {
    if (active && props.editingWaterId == null)
      map?.pm.enableDraw('Marker', { snappable: true, snapDistance: 20 })
    else map?.pm.disableDraw()
  },
)
// Permite volver a ubicar el punto después de un rechazo de validación.
watch(
  () => props.waterPosition,
  (position) => {
    if (!position && props.waterMode && props.editingWaterId == null)
      map?.pm.enableDraw('Marker', { snappable: true, snapDistance: 20 })
  },
)
// Vista inicial cuando todavía no hay sectores: la provincia de Mendoza
const MENDOZA_CENTER: L.LatLngTuple = [-34.6, -68.5]
const MENDOZA_ZOOM = 7

const container = ref<HTMLElement>()
let map: L.Map | null = null
const unitsLayer = L.featureGroup()
const waterLayer = L.featureGroup()
const coverageLayer = L.featureGroup()
const draftLayer = L.featureGroup()

function toLayer(polygon: PolygonGeoJSON, options: L.PolylineOptions = {}): L.Polygon {
  return L.polygon(L.GeoJSON.coordsToLatLngs(polygon.coordinates, 1), options)
}

function toPolygon(layer: L.Polygon): PolygonGeoJSON {
  return layer.toGeoJSON().geometry as PolygonGeoJSON
}

// Leaflet trata el texto como HTML; así el nombre se muestra tal cual
function textTooltip(text: string): HTMLElement {
  const element = document.createElement('span')
  element.textContent = text
  return element
}

// Contorno movido que todavía no se guardó
let reshapedPolygon: PolygonGeoJSON | null = null

function showUnits() {
  coverageLayer.clearLayers()
  for (const unit of props.units) {
    if (unit.usable_geometry)
      L.geoJSON(unit.usable_geometry, {
        style: { color: '#22c55e', weight: 1, fillOpacity: 0.25, interactive: false },
        pmIgnore: true,
      } as L.GeoJSONOptions).addTo(coverageLayer)
  }
  unitsLayer.clearLayers()
  for (const unit of props.units) {
    const editing = unit.id === props.editingId
    const layer = toLayer((editing && reshapedPolygon) || unit.polygon, {
      color: unit.id === props.selectedUnitId ? '#4ade80' : '#3b82f6',
      fillColor: unit.id === props.selectedUnitId ? '#22c55e' : '#3b82f6',
      weight: unit.id === props.selectedUnitId ? 4 : 2,
    })
    layer.on('click', (event: L.LeafletMouseEvent) => {
      if (props.waterMode || props.editingId !== null || map?.pm.globalDrawModeEnabled()) return
      L.DomEvent.stopPropagation(event)
      emit('selectUnit', unit.id)
    })
    layer.bindTooltip(
      textTooltip(
        `${unit.name} (${unit.area_ha ? Math.round((unit.usable_area_ha / unit.area_ha) * 100) : 0}%)`,
      ),
      { permanent: true, direction: 'center', className: 'lote-map-badge' },
    )
    unitsLayer.addLayer(layer)
    if (editing) {
      // Geoman solo edita capas que ya están en el mapa
      layer.pm.enable()
      layer.on('pm:edit', () => {
        reshapedPolygon = toPolygon(layer)
        emit('reshape', reshapedPolygon)
      })
    }
  }
}

function showDraft() {
  draftLayer.clearLayers()
  if (props.draft) draftLayer.addLayer(toLayer(props.draft, { dashArray: '6' }))
}

function showWater() {
  waterLayer.clearLayers()
  for (const point of props.waterPoints ?? []) {
    const editing = point.id === props.editingWaterId
    const coordinates =
      editing && props.waterPosition ? props.waterPosition : point.location.coordinates
    const marker = L.marker([coordinates[1], coordinates[0]], {
      draggable: false,
      icon: L.divIcon({
        className: 'water-point-marker',
        html: '<span class="aguada-pin" style="display:block;background:#087fbb;border:2px solid white;border-radius:50%;width:16px;height:16px;box-shadow:0 1px 4px #333"></span>',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      }),
    })
    marker.on('click', () => {
      if (!props.waterMode) emit('selectWater', point.id)
    })
    if (point.id === props.selectedWaterId) marker.setZIndexOffset(1000)
    marker.bindTooltip(textTooltip(point.name))
    waterLayer.addLayer(marker)
    if (editing) marker.pm.enable({ snappable: true, snapDistance: 20 })
    marker.on('pm:dragend', () => {
      const pos = marker.getLatLng()
      emit('locate', [pos.lng, pos.lat])
    })
  }
  if (props.waterPosition && props.editingWaterId == null) {
    const marker = L.marker([props.waterPosition[1], props.waterPosition[0]], {
      icon: L.divIcon({
        className: 'water-point-marker',
        html: '<span class="aguada-pin" style="display:block;width:16px;height:16px;border-radius:50%"></span>',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      }),
    }).addTo(waterLayer)
    marker.pm.enable({ snappable: true, snapDistance: 20 })
    marker.on('pm:dragend', () => {
      const pos = marker.getLatLng()
      emit('locate', [pos.lng, pos.lat])
    })
  }
}
watch(
  () => [props.waterPoints, props.editingWaterId, props.waterPosition, props.selectedWaterId],
  showWater,
)
onMounted(() => {
  map = L.map(container.value!)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)
  coverageLayer.addTo(map)
  waterLayer.addTo(map)
  unitsLayer.addTo(map)
  draftLayer.addTo(map)

  map.pm.setLang('es')
  map.on('pm:create', (event) => {
    // El contorno pasa a mostrarse como borrador hasta que se guarde
    event.layer.remove()
    if (event.shape === 'Marker') {
      const pos = (event.layer as L.Marker).getLatLng()
      map?.pm.disableDraw()
      emit('locate', [pos.lng, pos.lat])
    }
    if (event.shape === 'Polygon') emit('draw', toPolygon(event.layer as L.Polygon))
  })

  showUnits()
  showWater()
  showDraft()
  if (props.units.length > 0) map.fitBounds(unitsLayer.getBounds())
  else map.setView(MENDOZA_CENTER, MENDOZA_ZOOM)
})

onBeforeUnmount(() => map?.remove())

watch(
  () => [props.units, props.editingId, props.selectedUnitId] as const,
  ([, editingId], [, previousId]) => {
    // Otro sector o fin de la edición: se descarta el contorno movido
    if (editingId !== previousId) reshapedPolygon = null
    showUnits()
  },
)
watch(() => props.draft, showDraft)
</script>

<template>
  <div ref="container" class="units-map"></div>
</template>

<style scoped>
.units-map {
  height: 310px;
  background: #181c18;
  z-index: 0;
}
@media (min-width: 640px) {
  .units-map {
    height: 390px;
  }
}
:deep(.leaflet-bar a) {
  background: #141714eb;
  color: #e5e7eb;
  border-color: #2e382e;
  width: 34px;
  height: 34px;
  line-height: 34px;
}
:deep(.leaflet-bar) {
  border: 1px solid #2e382e;
  border-radius: 10px;
  overflow: hidden;
}
:deep(.lote-map-badge) {
  background: #141714eb;
  border: 1px solid #4ade80;
  color: #f3f4f6;
  border-radius: 8px;
  font-size: 11px;
  padding: 3px 8px;
}
:deep(.lote-map-badge:before) {
  display: none;
}
:deep(.aguada-pin) {
  background: #38bdf8 !important;
  box-shadow: 0 0 0 4px #38bdf855 !important;
}
</style>

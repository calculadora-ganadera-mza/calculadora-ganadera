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
  readOnly?: boolean
  showLabels?: boolean
  selectedUnitId?: number | null
  selectedWaterId?: number | null
  waterPoints?: WaterPoint[]
  sharedWaterPoints?: WaterPoint[]
  waterMode?: boolean
  editingWaterId?: number | null
  waterPosition?: Position | null
  referenceUnits?: ProductionUnit[]
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

// Encuadra los sectores, por ejemplo después de cambiar un contorno
function fitUnits() {
  if (map && unitsLayer.getLayers().length > 0) map.fitBounds(unitsLayer.getBounds())
}
defineExpose({ fitUnits })
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
const referenceLayer = L.featureGroup()
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

// Los demás sectores son una referencia visual; Geoman no puede editarlos.
function showReferenceUnits() {
  referenceLayer.clearLayers()
  for (const unit of props.referenceUnits ?? []) {
    L.geoJSON(unit.polygon, {
      style: {
        color: '#376a32',
        weight: 2,
        opacity: 0.45,
        dashArray: '6 6',
        fill: false,
      },
      interactive: false,
      pmIgnore: true,
      // Los vecinos no se editan, pero las esquinas se pegan a sus bordes
      snapIgnore: false,
    } as L.GeoJSONOptions).addTo(referenceLayer)
  }
}

function showUnits() {
  coverageLayer.clearLayers()
  for (const unit of props.units) {
    if (unit.usable_geometry)
      L.geoJSON(unit.usable_geometry, {
        style: { color: '#90b889', weight: 1, fillOpacity: 0.25, interactive: false },
        pmIgnore: true,
      } as L.GeoJSONOptions).addTo(coverageLayer)
  }
  // El servidor entrega el aporte de cada aguada propia en los sectores vecinos.
  for (const point of props.waterPoints ?? []) {
    if (!point.shared || !point.shared_coverage_geometry) continue
    L.geoJSON(point.shared_coverage_geometry, {
      style: {
        color: '#2678a7',
        weight: 2,
        opacity: 0.5,
        dashArray: '6 6',
        fillColor: '#2678a7',
        fillOpacity: 0.12,
      },
      interactive: false,
      pmIgnore: true,
    } as L.GeoJSONOptions).addTo(coverageLayer)
  }
  unitsLayer.clearLayers()
  for (const unit of props.units) {
    const editing = unit.id === props.editingId
    const layer = toLayer((editing && reshapedPolygon) || unit.polygon, {
      color: '#376a32',
      fillColor: '#90b889',
      weight: unit.id === props.selectedUnitId ? 4 : 2,
    })
    layer.on('click', (event: L.LeafletMouseEvent) => {
      if (props.waterMode || props.editingId !== null || map?.pm.globalDrawModeEnabled()) return
      L.DomEvent.stopPropagation(event)
      emit('selectUnit', unit.id)
    })
    layer.bindTooltip(textTooltip(unit.name), {
      permanent: props.showLabels,
      direction: 'center',
      className: 'sector-label',
    })
    unitsLayer.addLayer(layer)
    if (editing) {
      // Geoman solo edita capas que ya están en el mapa
      layer.pm.enable({ allowSelfIntersection: false })
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
  // Referencia de aguadas vecinas: sin manejadores de edición ni selección.
  for (const point of props.sharedWaterPoints ?? []) {
    const [lng, lat] = point.location.coordinates
    L.circleMarker([lat, lng], {
      radius: 8,
      color: '#2678a7',
      weight: 2,
      opacity: 0.5,
      dashArray: '3 3',
      fillColor: '#2678a7',
      fillOpacity: 0.12,
      pmIgnore: true,
    } as L.CircleMarkerOptions)
      .bindTooltip(textTooltip(`${point.name} · Compartida desde otro sector`))
      .addTo(waterLayer)
  }
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
  () => [
    props.waterPoints,
    props.sharedWaterPoints,
    props.editingWaterId,
    props.waterPosition,
    props.selectedWaterId,
  ],
  showWater,
)
onMounted(() => {
  map = L.map(container.value!)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)
  referenceLayer.addTo(map)
  coverageLayer.addTo(map)
  waterLayer.addTo(map)
  unitsLayer.addTo(map)
  draftLayer.addTo(map)

  map.pm.setLang('es')
  map.pm.setGlobalOptions({ allowSelfIntersection: false })
  if (!props.readOnly)
    map.pm.addControls({
      position: 'topleft',
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawRectangle: false,
      drawCircle: false,
      drawText: false,
      editControls: false,
    })
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

  showReferenceUnits()
  showUnits()
  showWater()
  showDraft()
  // Al dibujar un sector nuevo solo hay vecinos: la vista se centra en ellos
  if (props.units.length > 0) fitUnits()
  else if (referenceLayer.getLayers().length > 0) map.fitBounds(referenceLayer.getBounds())
  else map.setView(MENDOZA_CENTER, MENDOZA_ZOOM)
  // La pantalla de ubicar aguada abre el mapa ya listo para marcar el punto
  if (props.waterMode && props.editingWaterId == null)
    map.pm.enableDraw('Marker', { snappable: true, snapDistance: 20 })
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
watch(() => props.waterPoints, showUnits)
watch(() => props.referenceUnits, showReferenceUnits)
watch(() => props.draft, showDraft)
</script>

<template>
  <div ref="container" class="units-map"></div>
</template>

<style scoped>
.units-map {
  height: 430px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  z-index: 0;
}
:deep(.sector-label) {
  background: var(--color-surface);
  border: 1px solid var(--color-primary);
  border-radius: 8px;
  color: var(--color-text);
  font: inherit;
  font-weight: 600;
  padding: 6px 12px;
}
:deep(.sector-label::before) {
  display: none;
}
@media (max-width: 700px) {
  .units-map {
    height: 310px;
  }
}
:deep(.aguada-pin) {
  background: #087fbb;
  border: 2px solid white;
  box-shadow: 0 1px 4px #333;
}
</style>

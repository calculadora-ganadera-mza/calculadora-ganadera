<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import '@geoman-io/leaflet-geoman-free'
import 'leaflet/dist/leaflet.css'
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css'
import type { PolygonGeoJSON, ProductionUnit } from '@/api/productionUnits'

const props = defineProps<{
  units: ProductionUnit[]
  // Contorno dibujado que todavía no se guardó
  draft: PolygonGeoJSON | null
  // Sector con el contorno en edición, o null si no se edita ninguno
  editingId: number | null
}>()

const emit = defineEmits<{
  draw: [polygon: PolygonGeoJSON]
  reshape: [polygon: PolygonGeoJSON]
}>()

// Vita inicial cuando todavía no hay sectores: la provincia de Mendoza
const MENDOZA_CENTER: L.LatLngTuple = [-34.6, -68.5]
const MENDOZA_ZOOM = 7

const container = ref<HTMLElement>()
let map: L.Map | null = null
const unitsLayer = L.featureGroup()
const draftLayer = L.featureGroup()

function toLayer(polygon: PolygonGeoJSON, options: L.PolylineOptions = {}): L.Polygon {
  return L.polygon(L.GeoJSON.coordsToLatLngs(polygon.coordinates, 1), options)
}

function toPolygon(layer: L.Polygon): PolygonGeoJSON {
  return layer.toGeoJSON().geometry as PolygonGeoJSON
}

function showUnits() {
  unitsLayer.clearLayers()
  for (const unit of props.units) {
    const layer = toLayer(unit.polygon)
    layer.bindTooltip(unit.name)
    unitsLayer.addLayer(layer)
    if (unit.id === props.editingId) {
      // Geoman solo edita capas que ya están en el mapa
      layer.pm.enable()
      layer.on('pm:edit', () => emit('reshape', toPolygon(layer)))
    }
  }
}

function showDraft() {
  draftLayer.clearLayers()
  if (props.draft) draftLayer.addLayer(toLayer(props.draft, { dashArray: '6' }))
}

onMounted(() => {
  map = L.map(container.value!)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)
  unitsLayer.addTo(map)
  draftLayer.addTo(map)

  map.pm.setLang('es')
  map.pm.addControls({
    position: 'topleft',
    drawMaker: false,
    drawCircleMarker: false,
    drawPolyline: false,
    drawRectangle: false,
    drawCircle: false,
    drawText: false,
    editControls: false,
  })
  map.on('pm:create', (event) => {
    // El contorno pasa a mostrarse como borrador hasta que se guarde
    emit('draw', toPolygon(event.layer as L.Polygon))
    event.layer.remove()
  })

  showUnits()
  showDraft()
  if (props.units.length > 0) map.fitBounds(unitsLayer.getBounds())
  else map.setView(MENDOZA_CENTER, MENDOZA_ZOOM)
})

onBeforeUnmount(() => map?.remove())

watch(() => [props.units, props.editingId], showUnits)
watch(() => props.draft, showDraft)
</script>

<template>
  <div ref="container" class="units-map"></div>
</template>

<style scoped>
.units-map {
  height: 420px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
</style>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import FarmBreadcrumb from '@/components/FarmBreadcrumb.vue'
import UnitsMap from '@/components/UnitsMap.vue'
import { loadScenarioMap, type ScenarioMap } from '@/api/farm'
import {
  ApiError,
  createProductionUnit,
  type PolygonGeoJSON,
  type ProductionUnit,
} from '@/api/productionUnits'
import { routeId } from '@/utils/farm'

// El sector nuevo todavía no existe: el mapa solo muestra los vecinos
const NO_UNITS: ProductionUnit[] = []
const route = useRoute()
const router = useRouter()
const data = ref<ScenarioMap>()
const loading = ref(true)
// La carga falló y se puede reintentar
const error = ref('')
// La dirección trae un escenario que no existe: reintentar no sirve
const missing = ref('')
// Contorno dibujado que todavía no se guardó
const draft = ref<PolygonGeoJSON | null>(null)
const name = ref('')
const saving = ref(false)
const saveError = ref('')
let loadVersion = 0

async function load() {
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  missing.value = ''
  data.value = undefined
  const scenarioId = routeId(route.params.scenarioId)
  try {
    const loaded = scenarioId === null ? null : await loadScenarioMap(scenarioId)
    if (version !== loadVersion) return
    if (!loaded) missing.value = 'No se encontró el escenario.'
    else data.value = loaded
  } catch {
    if (version === loadVersion) error.value = 'No se pudo cargar el escenario. Intentá de nuevo.'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

function onDraw(polygon: PolygonGeoJSON) {
  draft.value = polygon
  saveError.value = ''
}

async function save() {
  if (!data.value) return
  const trimmed = name.value.trim()
  if (!draft.value) {
    saveError.value = 'Dibujá el contorno del sector en el mapa.'
    return
  }
  if (!trimmed) {
    saveError.value = 'Falta el nombre del sector.'
    return
  }
  saving.value = true
  saveError.value = ''
  try {
    const scenarioId = data.value.scenario.id
    const unit = await createProductionUnit(scenarioId, { name: trimmed, polygon: draft.value })
    await router.push({ name: 'sector', params: { scenarioId, unitId: unit.id } })
  } catch (err) {
    saveError.value = err instanceof ApiError ? err.message : 'No se pudo guardar el sector.'
  } finally {
    saving.value = false
  }
}

watch(() => route.params.scenarioId, load, { immediate: true })
</script>

<template>
  <section class="new-sector-page">
    <FarmBreadcrumb
      :steps="[
        {
          label: data?.scenario.name ?? 'Escenario',
          to: { name: 'scenario', params: { scenarioId: route.params.scenarioId } },
        },
        { label: 'Nuevo sector' },
      ]"
    />
    <h1>Nuevo sector</h1>
    <p v-if="loading">Cargando escenario…</p>
    <p v-else-if="missing" class="error" role="alert">{{ missing }}</p>
    <div v-else-if="error" role="alert">
      <p class="error">{{ error }}</p>
      <button type="button" class="btn" @click="load">Reintentar</button>
    </div>
    <div v-else-if="data" class="layout">
      <div class="map-box panel">
        <p class="hint">
          Tocá el ícono del polígono y marcá en el mapa cada esquina. Para cerrar, tocá la primera.
        </p>
        <UnitsMap
          :units="NO_UNITS"
          :reference-units="data.units"
          :draft="draft"
          :editing-id="null"
          @draw="onDraw"
        />
      </div>
      <form class="panel side" novalidate @submit.prevent="save">
        <div class="field">
          <label for="unit-name">Nombre</label>
          <input id="unit-name" v-model="name" maxlength="100" autocomplete="off" />
        </div>
        <p v-if="saveError" class="error" role="alert">{{ saveError }}</p>
        <div class="actions">
          <button class="btn btn-primary" :disabled="saving">
            {{ saving ? 'Guardando…' : 'Guardar sector' }}
          </button>
          <RouterLink
            class="text-button"
            :to="{ name: 'scenario', params: { scenarioId: data.scenario.id } }"
          >
            Cancelar
          </RouterLink>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.new-sector-page {
  max-width: 1100px;
}

h1 {
  font-size: 1.6rem;
  letter-spacing: -0.025em;
  margin-bottom: 16px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(240px, 1fr);
  gap: 16px;
  align-items: start;
}

.map-box {
  display: grid;
  gap: 10px;
}

.side {
  display: grid;
  gap: 14px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

@media (max-width: 800px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import ScenarioUnits from '@/components/ScenarioUnits.vue'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'

const route = useRoute()
const router = useRouter()
const scenario = ref<Scenario>()
const season = ref<Season>()
const unitId = ref<number>()
const loading = ref(true)
const error = ref('')
let loadVersion = 0

async function load() {
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  scenario.value = undefined
  const scenarioId = Number(route.params.scenarioId)
  const requestedUnitId = Number(route.params.unitId)
  if (
    !Number.isSafeInteger(scenarioId) ||
    scenarioId <= 0 ||
    !Number.isSafeInteger(requestedUnitId) ||
    requestedUnitId <= 0
  ) {
    error.value = 'El sector solicitado no es válido.'
    loading.value = false
    return
  }
  try {
    const scenarios = await listScenarios()
    const found = scenarios.find((item) => item.id === scenarioId)
    if (!found) {
      if (version === loadVersion) error.value = 'No se encontró el establecimiento.'
      return
    }
    const seasons = await listSeasons(scenarioId)
    if (version !== loadVersion) return
    scenario.value = found
    season.value = seasons.find((item) => item.is_current)
    unitId.value = requestedUnitId
  } catch {
    if (version === loadVersion) error.value = 'No se pudo cargar el sector. Intentá de nuevo.'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

watch(() => [route.params.scenarioId, route.params.unitId], load, { immediate: true })
</script>

<template>
  <section class="sector-page">
    <nav class="breadcrumb" aria-label="Ubicación">
      <RouterLink to="/farm">Mi campo</RouterLink>
      <span aria-hidden="true">›</span>
      <span v-if="scenario">{{ scenario.name }}</span>
      <span aria-hidden="true">›</span>
      <span>Administrar sector</span>
    </nav>
    <p v-if="loading">Cargando sector…</p>
    <div v-else-if="error" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="load">Reintentar</button>
    </div>
    <template v-else-if="scenario && unitId">
      <div class="heading">
        <p class="subtitle">
          Administrá el contorno, las aguadas y los datos de la campaña de este sector.
        </p>
        <RouterLink
          v-if="season"
          class="calculate"
          :to="{
            name: 'carrying-capacity',
            query: { scenario: scenario.id, unit: unitId, season: season.id },
          }"
        >
          Calcular
        </RouterLink>
      </div>
      <ScenarioUnits
        :key="scenario.id + ':' + unitId"
        :scenario-id="scenario.id"
        :unit-id="unitId"
        :season-id="season?.id"
        @removed="router.push('/farm')"
      />
    </template>
  </section>
</template>

<style scoped>
.sector-page {
  max-width: 1100px;
}
.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}
.breadcrumb a {
  color: var(--color-primary);
}
.heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.calculate {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 8px;
  background: var(--color-primary);
  color: var(--color-surface);
  text-decoration: none;
}
.subtitle {
  color: var(--color-text-muted);
}
</style>

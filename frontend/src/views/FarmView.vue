<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AppModal from '@/components/AppModal.vue'
import ScenarioForm from '@/components/ScenarioForm.vue'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'
import { listProductionUnits } from '@/api/productionUnits'
import { hectares } from '@/utils/farm'
import { seasonName } from '@/utils/season'

interface ScenarioRow extends Scenario {
  unitCount: number
  areaHa: number
  lastSeason?: Season
}

const router = useRouter()
const rows = ref<ScenarioRow[]>([])
const loading = ref(true)
const loadError = ref('')
const creating = ref(false)

async function toRow(scenario: Scenario): Promise<ScenarioRow> {
  const [units, seasons] = await Promise.all([
    listProductionUnits(scenario.id),
    listSeasons(scenario.id),
  ])
  return {
    ...scenario,
    unitCount: units.length,
    areaHa: units.reduce((total, unit) => total + unit.area_ha, 0),
    // El servidor las devuelve ordenadas por año
    lastSeason: seasons[seasons.length - 1],
  }
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    rows.value = await Promise.all((await listScenarios()).map(toRow))
  } catch {
    loadError.value = 'No se pudieron cargar tus escenarios.'
  } finally {
    loading.value = false
  }
}

function onCreated(scenario: Scenario) {
  void router.push({ name: 'scenario', params: { scenarioId: scenario.id } })
}

onMounted(load)
</script>

<template>
  <section class="farm-page">
    <h1>Mi campo</h1>
    <p v-if="loading">Cargando…</p>
    <div v-else-if="loadError" role="alert">
      <p class="error">{{ loadError }}</p>
      <button type="button" class="btn" @click="load">Reintentar</button>
    </div>
    <template v-else-if="rows.length">
      <h2>Escenarios</h2>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Escenario</th>
              <th class="number">Sectores</th>
              <th class="number">Superficie</th>
              <th>Última campaña</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>
                <RouterLink :to="{ name: 'scenario', params: { scenarioId: row.id } }">
                  {{ row.name }}
                </RouterLink>
              </td>
              <td class="number">{{ row.unitCount }}</td>
              <td class="number">{{ hectares(row.areaHa) }} ha</td>
              <td>
                {{
                  row.lastSeason
                    ? seasonName(row.lastSeason.start_date, row.lastSeason.end_date)
                    : '—'
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <div v-else class="empty panel">
      <p>Creá un escenario para empezar a cargar sus sectores y campañas.</p>
      <button type="button" class="btn btn-primary" @click="creating = true">
        Nuevo escenario
      </button>
    </div>
    <AppModal v-if="creating" title="Nuevo escenario" @close="creating = false">
      <ScenarioForm @created="onCreated" />
    </AppModal>
  </section>
</template>

<style scoped>
.farm-page {
  max-width: 1100px;
}

h1 {
  font-size: 1.6rem;
  letter-spacing: -0.025em;
  margin-bottom: 20px;
}

h2 {
  margin: 0 0 10px;
  font-size: 0.95rem;
}

.empty {
  display: grid;
  justify-items: start;
  gap: 12px;
}

.empty p {
  margin: 0;
}
</style>

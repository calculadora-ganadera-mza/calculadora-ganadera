<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppModal from '@/components/AppModal.vue'
import ScenarioForm from '@/components/ScenarioForm.vue'
import { ApiError } from '@/api/errors'
import {
  listScenarios,
  listSeasons,
  updateScenario,
  type Scenario,
  type Season,
} from '@/api/scenarios'
import { listProductionUnits } from '@/api/productionUnits'
import { hectares } from '@/utils/farm'
import { seasonName } from '@/utils/season'

interface ScenarioRow extends Scenario {
  unitCount: number
  areaHa: number
  lastSeason?: Season
}

const route = useRoute()
const router = useRouter()
const rows = ref<ScenarioRow[]>([])
const loading = ref(true)
const loadError = ref('')
const actionError = ref('')
const creating = ref(false)
const markingId = ref<number | null>(null)
let loadVersion = 0

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
  const version = ++loadVersion
  loading.value = true
  loadError.value = ''
  actionError.value = ''
  try {
    const scenarios = await listScenarios()
    if (version !== loadVersion) return
    // Al entrar a Mi campo, se abre directamente el escenario principal
    if (route.name === 'farm' && scenarios.length > 0) {
      const main = scenarios.find((scenario) => scenario.is_main) ?? scenarios[0]!
      await router.replace({ name: 'scenario', params: { scenarioId: main.id } })
      return
    }
    const loadedRows = await Promise.all(scenarios.map(toRow))
    if (version !== loadVersion) return
    rows.value = loadedRows
  } catch {
    if (version === loadVersion) loadError.value = 'No se pudieron cargar tus escenarios.'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

async function markAsMain(row: ScenarioRow) {
  markingId.value = row.id
  actionError.value = ''
  try {
    const updated = await updateScenario(row.id, { is_main: true })
    rows.value = rows.value.map((item) => ({
      ...item,
      is_main: item.id === updated.id,
    }))
  } catch (err) {
    actionError.value =
      err instanceof ApiError ? err.message : 'No se pudo marcar el escenario como principal.'
  } finally {
    markingId.value = null
  }
}

function onCreated(scenario: Scenario) {
  creating.value = false
  void router.push({ name: 'scenario', params: { scenarioId: scenario.id } })
}

watch(() => route.name, load, { immediate: true })
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
      <div class="section-heading">
        <h2>Escenarios</h2>
        <button type="button" class="btn" @click="creating = true">Nuevo escenario</button>
      </div>
      <p v-if="actionError" class="error action-error" role="alert">{{ actionError }}</p>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Escenario</th>
              <th class="number">Sectores</th>
              <th class="number">Superficie</th>
              <th>Última campaña</th>
              <th><span class="visually-hidden">Acciones</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>
                <RouterLink :to="{ name: 'scenario', params: { scenarioId: row.id } }">
                  {{ row.name }}
                </RouterLink>
                <span v-if="row.is_main" class="main-badge">Principal</span>
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
              <td class="row-actions">
                <button
                  v-if="!row.is_main"
                  type="button"
                  class="text-button"
                  :disabled="markingId !== null"
                  @click="markAsMain(row)"
                >
                  {{ markingId === row.id ? 'Guardando…' : 'Marcar como principal' }}
                </button>
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
      <ScenarioForm @created="onCreated">
        <template #actions>
          <button type="button" class="btn" @click="creating = false">Cancelar</button>
        </template>
      </ScenarioForm>
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

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 10px;
}

h2 {
  margin: 0;
  font-size: 0.95rem;
}

.action-error {
  margin-bottom: 10px;
}

.main-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 400;
}

.row-actions {
  text-align: right;
  white-space: nowrap;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
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

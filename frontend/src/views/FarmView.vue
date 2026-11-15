<script setup lang="ts">
import { onMounted, ref } from 'vue'
import ScenarioForm from '@/components/ScenarioForm.vue'
import ScenarioUnits from '@/components/ScenarioUnits.vue'
import SeasonRainfall from '@/components/SeasonRainfall.vue'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'
import { formatDate, seasonLabel } from '@/utils/season'

interface ScenarioWithSeasons extends Scenario {
  seasons: Season[]
  // La campaña que se abre: la que contiene la fecha de hoy o la más cercana
  current?: Season
}

const scenarios = ref<ScenarioWithSeasons[]>([])
const loading = ref(true)
const loadError = ref('')

async function withSeasons(scenario: Scenario): Promise<ScenarioWithSeasons> {
  const seasons = await listSeasons(scenario.id)
  return { ...scenario, seasons, current: seasons.find((season) => season.is_current) }
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    scenarios.value = await Promise.all((await listScenarios()).map(withSeasons))
  } catch {
    loadError.value = 'No se pudieron cargar tus establecimientos.'
  } finally {
    loading.value = false
  }
}

async function onCreated(scenario: Scenario) {
  try {
    scenarios.value = [...scenarios.value, await withSeasons(scenario)]
  } catch {
    // El establecimiento ya se guardó: se recarga la lista completa
    await load()
  }
}

onMounted(load)
</script>

<template>
  <section class="farm-page">
    <h1 v-if="loading || loadError || !scenarios.length">Mi campo</h1>
    <p v-if="loading">Cargando…</p>
    <div v-else-if="loadError" class="load-error" role="alert">
      <p>{{ loadError }}</p>
      <button type="button" @click="load">Reintentar</button>
    </div>
    <template v-else-if="scenarios.length > 0">
      <article v-for="scenario in scenarios" :key="scenario.id" class="scenario">
        <h1>{{ scenario.name }}</h1>
        <p class="subtitle">Administrá los sectores y la campaña de tu establecimiento.</p>
        <section v-if="scenario.current" class="campaign" aria-label="Campaña actual">
          <div class="campaign-dates">
            <h2>
              Campaña {{ scenario.current.start_date.slice(0, 4) }}/{{
                scenario.current.end_date.slice(2, 4)
              }}
              <span class="current">actual</span>
            </h2>
            <p>
              Del {{ formatDate(scenario.current.start_date) }} al
              {{ formatDate(scenario.current.end_date) }}
            </p>
          </div>
          <SeasonRainfall
            :key="scenario.current.id"
            :season-id="scenario.current.id"
            :rainfall-mm="scenario.current.rainfall_mm"
          />
        </section>
        <details v-if="scenario.seasons.some((season) => !season.is_current)" class="past-seasons">
          <summary>Otras campañas</summary>
          <ul>
            <li
              v-for="season in scenario.seasons.filter((item) => !item.is_current)"
              :key="season.id"
            >
              Campaña {{ seasonLabel(season.start_date, season.end_date) }}
            </li>
          </ul>
        </details>
        <ScenarioUnits :scenario-id="scenario.id" overview />
      </article>
    </template>
    <template v-else>
      <p>Registrá tu establecimiento para empezar a cargar sus sectores y campañas.</p>
      <ScenarioForm @created="onCreated" />
    </template>
  </section>
</template>

<style scoped>
.farm-page {
  max-width: 1100px;
}
.scenario + .scenario {
  margin-top: 32px;
}
h1 {
  font-size: 1.6rem;
  letter-spacing: -0.025em;
}
.subtitle {
  margin-bottom: 18px;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}
.campaign {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 16px;
  padding: 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 11px;
}
.campaign h2 {
  margin: 0;
  font-size: 0.95rem;
}
.campaign-dates p {
  margin: 8px 0 0;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}
.campaign :deep(.rainfall) {
  margin-top: 0;
}
.current {
  display: inline-block;
  margin-left: 6px;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 400;
}
.past-seasons {
  margin: 16px 0;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}
.load-error button {
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  cursor: pointer;
}
@media (max-width: 700px) {
  .campaign {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }
}
</style>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import ScenarioForm from '@/components/ScenarioForm.vue'
import { listScenarios, listSeasons, type Scenario, type Season } from '@/api/scenarios'
import { seasonLabel } from '@/utils/season'

interface ScenarioWithSeasons extends Scenario {
  seasons: Season[]
}

const scenarios = ref<ScenarioWithSeasons[]>([])
const loading = ref(true)
const loadError = ref('')

async function withSeasons(scenario: Scenario): Promise<ScenarioWithSeasons> {
  return { ...scenario, seasons: await listSeasons(scenario.id) }
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
  <section>
    <h1>Mi campo</h1>

    <p v-if="loading">Cargando…</p>

    <div v-else-if="loadError" class="load-error" role="alert">
      <p>{{ loadError }}</p>
      <button type="button" @click="load">Reintentar</button>
    </div>

    <template v-else-if="scenarios.length > 0">
      <article v-for="scenario in scenarios" :key="scenario.id" class="scenario">
        <h2>{{ scenario.name }}</h2>
        <ul>
          <li v-for="season in scenario.seasons" :key="season.id">
            Campaña {{ seasonLabel(season.start_date, season.end_date) }}
            <span v-if="season.is_current" class="current">actual</span>
          </li>
        </ul>
      </article>
    </template>

    <template v-else>
      <p>Registrá tu establecimiento para empezar a cargar sus sectores y campañas.</p>
      <ScenarioForm @created="onCreated" />
    </template>
  </section>
</template>

<style scoped>
.scenario {
  max-width: 480px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
}

.scenario h2 {
  margin: 0 0 8px;
  font-size: 1.1rem;
}

.scenario ul {
  margin: 0;
  padding-left: 20px;
}

.current {
  margin-left: 6px;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.8rem;
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
</style>

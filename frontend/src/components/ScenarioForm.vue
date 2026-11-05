<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  createScenario,
  fetchFirstSeasonYears,
  type ScenarioRead,
  type SeasonYearOption,
} from '@/api/scenarios'

const emit = defineEmits<{ created: [scenario: ScenarioRead] }>()

const name = ref('')
const year = ref<number | null>(null)
const options = ref<SeasonYearOption[]>([])
const nameError = ref('')
const formError = ref('')
const saving = ref(false)

// "2026-07-01" → "1/7/2026", sin pasar por Date para no correr el día por la zona horaria
function formatDate(isoDate: string): string {
  const [y, m, d] = isoDate.split('-')
  return `${Number(d)}/${Number(m)}/${y}`
}

function optionLabel(option: SeasonYearOption): string {
  const nextYear = String(option.start_year + 1).slice(-2)
  return `${option.start_year}/${nextYear} (del ${formatDate(option.start_date)} al ${formatDate(option.end_date)})`
}

onMounted(async () => {
  try {
    options.value = await fetchFirstSeasonYears()
    year.value = options.value[0]?.start_year ?? null
  } catch {
    formError.value = 'No se pudieron cargar los años de campaña. Probá de nuevo más tarde.'
  }
})

async function submit() {
  nameError.value = ''
  formError.value = ''
  const trimmed = name.value.trim()
  if (!trimmed) {
    nameError.value = 'Ingresá el nombre del establecimiento.'
    return
  }
  if (year.value === null) return

  saving.value = true
  try {
    const scenario = await createScenario({ name: trimmed, first_season_year: year.value })
    emit('created', scenario)
  } catch {
    formError.value = 'No se pudo registrar el establecimiento. Probá de nuevo.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="scenario-form" novalidate @submit.prevent="submit">
    <div class="field">
      <label for="scenario-name">Nombre del establecimiento</label>
      <input id="scenario-name" v-model="name" type="text" autocomplete="off" />
      <p v-if="nameError" class="error">{{ nameError }}</p>
    </div>

    <div class="field">
      <label for="first-season-year">Primera campaña</label>
      <select id="first-season-year" v-model="year" :disabled="options.length === 0">
        <option v-for="option in options" :key="option.start_year" :value="option.start_year">
          {{ optionLabel(option) }}
        </option>
      </select>
    </div>

    <p v-if="formError" class="error" role="alert">{{ formError }}</p>

    <button type="submit" :disabled="saving || options.length === 0">
      {{ saving ? 'Guardando…' : 'Registrar establecimiento' }}
    </button>
  </form>
</template>

<style scoped>
.scenario-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 480px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

label {
  font-weight: 600;
}

input,
select {
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
}

.error {
  margin: 0;
  color: var(--color-danger);
  font-size: 0.9rem;
}

button {
  align-self: flex-start;
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  background: var(--color-primary);
  color: var(--color-surface);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>

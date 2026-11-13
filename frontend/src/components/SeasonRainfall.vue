<script setup lang="ts">
import { ref } from 'vue'
import { ApiError } from '@/api/errors'
import { updateSeasonRainfall } from '@/api/seasons'

const props = defineProps<{ seasonId: number; rainfallMm: number | null }>()

const rainfall = ref<number | ''>(props.rainfallMm ?? '')
const saving = ref(false)
const error = ref('')
const saved = ref(false)

async function save() {
  saved.value = false
  error.value = ''
  if (rainfall.value !== '' && rainfall.value < 0) {
    error.value = 'La lluvia no puede ser negativa.'
    return
  }
  saving.value = true
  try {
    await updateSeasonRainfall(props.seasonId, rainfall.value === '' ? null : rainfall.value)
    saved.value = true
  } catch (err) {
    error.value =
      err instanceof ApiError ? err.message : 'No se pudo guardar la lluvia. Probá de nuevo.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="rainfall" novalidate @submit.prevent="save">
    <label :for="`rainfall-${seasonId}`"
      >Lluvia de la campaña anterior (julio a junio, en mm)</label
    >
    <div class="row">
      <input
        :id="`rainfall-${seasonId}`"
        v-model.number="rainfall"
        type="number"
        min="0"
        step="1"
        inputmode="numeric"
      />
      <button type="submit" :disabled="saving">{{ saving ? 'Guardando…' : 'Guardar' }}</button>
    </div>
    <p class="hint">Es opcional: la calculadora la pide al calcular.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="saved" class="saved" role="status">Lluvia guardada.</p>
  </form>
</template>

<style scoped>
.rainfall {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
}

label {
  font-weight: 600;
}

.row {
  display: flex;
  gap: 8px;
}

input {
  width: 120px;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
}

.hint {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.error {
  margin: 0;
  color: var(--color-danger);
}

.saved {
  margin: 0;
  color: var(--color-success);
}
</style>

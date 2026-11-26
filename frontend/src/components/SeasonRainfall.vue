<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter, type RouteLocationRaw } from 'vue-router'
import { ApiError } from '@/api/errors'
import { updateSeasonRainfall } from '@/api/seasons'
import type { Season } from '@/api/scenarios'

const props = defineProps<{
  seasonId: number
  rainfallMm: number | null
  // Si se llegó desde la calculadora: el sector que espera la lluvia y a dónde
  // se vuelve al guardar o sin guardar
  calculator?: { unitName: string; afterSave: RouteLocationRaw; back: RouteLocationRaw }
}>()
const emit = defineEmits<{ saved: [season: Season] }>()

const rainfall = ref<number | ''>(props.rainfallMm ?? '')
const saving = ref(false)
const error = ref('')
const saved = ref(false)
const router = useRouter()

async function save() {
  saved.value = false
  error.value = ''
  if (rainfall.value !== '' && rainfall.value < 0) {
    error.value = 'La lluvia no puede ser negativa.'
    return
  }
  // La calculadora necesita una lluvia mayor que 0: volver sin ella no sirve
  if (props.calculator && (rainfall.value === '' || rainfall.value <= 0)) {
    error.value = 'Ingresá una lluvia mayor que 0 para poder calcular.'
    return
  }
  saving.value = true
  try {
    const season = await updateSeasonRainfall(
      props.seasonId,
      rainfall.value === '' ? null : rainfall.value,
    )
    emit('saved', season)
    if (props.calculator) {
      await router.push(props.calculator.afterSave)
      return
    }
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
    <div v-if="calculator" class="notice" role="status">
      <strong>Falta la lluvia para calcular la receptividad de {{ calculator.unitName }}.</strong>
      Al guardarla, se vuelve a la calculadora.
    </div>
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
      <button v-if="!calculator" type="submit" :disabled="saving">
        {{ saving ? 'Guardando…' : 'Guardar' }}
      </button>
    </div>
    <div v-if="calculator" class="actions">
      <button class="btn btn-primary" type="submit" :disabled="saving">
        {{ saving ? 'Guardando…' : 'Guardar y volver a la calculadora' }}
      </button>
      <RouterLink :to="calculator.back">Volver sin guardar</RouterLink>
    </div>
    <p v-else class="hint">Es opcional: la calculadora la pide al calcular.</p>
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

.notice {
  margin-bottom: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-warning-soft);
  color: var(--color-warning);
  font-size: 0.9rem;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: center;
  margin-top: 4px;
}

.actions a {
  color: var(--color-primary);
  font-size: 0.9rem;
}
</style>

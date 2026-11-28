<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError } from '@/api/errors'
import { createSeason } from '@/api/seasons'
import type { Season } from '@/api/scenarios'

// previous: ofrece el año anterior a la primera campaña, como en Seguimiento
const props = defineProps<{ scenarioId: number; seasons: Season[]; previous?: boolean }>()
const emit = defineEmits<{ created: [season: Season] }>()

// Solo se ofrece el año pegado a la última campaña (o a la primera): así nunca
// se repite un año. Mi campo agrega posteriores y Seguimiento, anteriores
const nextYear = computed(() => {
  if (!props.seasons.length) return null
  const years = props.seasons.map((s) => s.start_year)
  return props.previous ? Math.min(...years) - 1 : Math.max(...years) + 1
})
const label = computed(() =>
  nextYear.value === null ? '' : `${nextYear.value}/${String(nextYear.value + 1).slice(-2)}`,
)

const saving = ref(false)
const error = ref('')

async function add() {
  if (nextYear.value === null) return
  saving.value = true
  error.value = ''
  try {
    emit('created', await createSeason(props.scenarioId, nextYear.value))
  } catch (err) {
    error.value =
      err instanceof ApiError ? err.message : 'No se pudo agregar la campaña. Volver a intentar.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="nextYear !== null" class="add-season">
    <button type="button" :disabled="saving" @click="add">
      {{ saving ? 'Agregando…' : `Agregar campaña ${label}` }}
    </button>
    <!-- Otros botones de quien usa el componente, como «Cancelar» en una ventana -->
    <slot name="actions" />
    <p class="hint">Nace sin datos. Las demás campañas no cambian.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.add-season {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
  margin: 0 0 16px;
}

button {
  padding: 8px 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
  cursor: pointer;
}

.hint,
.error {
  margin: 0;
  font-size: 0.85rem;
}

.hint {
  color: var(--color-text-muted);
}

.error {
  flex-basis: 100%;
  color: var(--color-danger);
}
</style>

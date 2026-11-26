<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  deleteCarryingCapacityCalculation,
  listUserCarryingCapacityCalculations,
  type CarryingCapacityCalculationSummary,
} from '@/api/carryingCapacity'
import { ApiError } from '@/api/errors'
import AppModal from '@/components/AppModal.vue'
import { oneDecimal, upToOneDecimal } from '@/utils/format'
import { seasonName } from '@/utils/season'

const history = ref<CarryingCapacityCalculationSummary[]>([])
const loading = ref(true)
const error = ref('')
const pendingDelete = ref<CarryingCapacityCalculationSummary | null>(null)
const deletingId = ref<number | null>(null)
const deleteError = ref('')

const dateTimeFormat = new Intl.DateTimeFormat('es-AR', {
  dateStyle: 'short',
  timeStyle: 'short',
})

function itemContext(item: CarryingCapacityCalculationSummary): string {
  const season = seasonName(item.season_start_date, item.season_end_date)
  return `${item.scenario_name}, ${item.production_unit_name}, campaña ${season}`
}

async function loadHistory() {
  loading.value = true
  error.value = ''
  deleteError.value = ''
  try {
    history.value = await listUserCarryingCapacityCalculations()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'No se pudo cargar el historial.'
  } finally {
    loading.value = false
  }
}

function askDelete(item: CarryingCapacityCalculationSummary) {
  if (deletingId.value !== null) return
  deleteError.value = ''
  pendingDelete.value = item
}

function cancelDelete() {
  if (deletingId.value !== null) return
  pendingDelete.value = null
}

async function confirmDelete() {
  const target = pendingDelete.value
  if (!target || deletingId.value !== null) return
  deletingId.value = target.id
  deleteError.value = ''
  try {
    await deleteCarryingCapacityCalculation(target.id)
    history.value = history.value.filter((item) => item.id !== target.id)
    pendingDelete.value = null
  } catch (err) {
    deleteError.value = err instanceof ApiError ? err.message : 'No se pudo borrar el cálculo.'
  } finally {
    deletingId.value = null
  }
}

onMounted(loadHistory)
</script>

<template>
  <section class="calculators-page">
    <h1>Calculadoras</h1>
    <article class="card">
      <div>
        <h2>Receptividad</h2>
        <p>Cuántos animales soporta un sector según su pasto.</p>
      </div>
      <RouterLink class="button" :to="{ name: 'carrying-capacity' }">
        Calcular receptividad
      </RouterLink>
    </article>

    <section class="history" aria-labelledby="history-heading">
      <h2 id="history-heading">Cálculos guardados</h2>
      <p v-if="loading" class="hint">Cargando cálculos guardados…</p>
      <div v-else-if="error" class="error-box" role="alert">
        <p class="error">{{ error }}</p>
        <button class="btn" type="button" @click="loadHistory">Reintentar</button>
      </div>
      <p v-else-if="!history.length" class="hint">Todavía no guardaste cálculos de receptividad.</p>
      <template v-else>
        <p v-if="deleteError && !pendingDelete" class="error" role="alert">{{ deleteError }}</p>
        <ul class="history-list">
          <li v-for="item in history" :key="item.id" class="history-item">
            <div class="history-main">
              <div class="history-title">
                <strong>{{ item.scenario_name }} · {{ item.production_unit_name }}</strong>
                <span class="muted">
                  · campaña {{ seasonName(item.season_start_date, item.season_end_date) }}
                </span>
                <span class="tag" :class="{ result: item.kind === 'result' }">
                  {{ item.kind === 'result' ? 'Resultado de la campaña' : 'Simulación' }}
                </span>
              </div>
              <p class="history-meta">
                {{ dateTimeFormat.format(new Date(item.created_at)) }} · Rodeo máximo:
                {{ oneDecimal.format(item.max_herd_cow_equivalents) }} EV · Receptividad:
                {{ oneDecimal.format(item.carrying_capacity_ha_per_cow_equivalent) }}
                ha/EV · Lluvia:
                {{ upToOneDecimal.format(item.rainfall_mm) }} mm
              </p>
            </div>
            <div class="history-actions">
              <RouterLink
                class="btn"
                :to="{
                  name: 'carrying-capacity-saved',
                  params: { calculationId: item.id },
                }"
              >
                Ver <span class="visually-hidden">cálculo de {{ itemContext(item) }}</span>
              </RouterLink>
              <button
                class="text-button danger delete-action"
                type="button"
                :disabled="deletingId !== null"
                @click="askDelete(item)"
              >
                {{ deletingId === item.id ? 'Borrando…' : 'Borrar' }}
                <span class="visually-hidden">cálculo de {{ itemContext(item) }}</span>
              </button>
            </div>
          </li>
        </ul>
      </template>
    </section>

    <AppModal v-if="pendingDelete" title="Borrar cálculo guardado" @close="cancelDelete">
      <p>
        ¿Querés borrar
        {{ pendingDelete.kind === 'result' ? 'este resultado de la campaña' : 'esta simulación' }}
        de
        <strong
          >{{ pendingDelete.scenario_name }} · {{ pendingDelete.production_unit_name }}</strong
        >
        (campaña {{ seasonName(pendingDelete.season_start_date, pendingDelete.season_end_date) }})?
        Esta acción no se puede deshacer.
      </p>
      <p v-if="deleteError" class="error modal-error" role="alert">{{ deleteError }}</p>
      <div class="modal-actions">
        <button class="btn" type="button" :disabled="deletingId !== null" @click="cancelDelete">
          Cancelar
        </button>
        <button
          class="btn danger-button"
          type="button"
          :disabled="deletingId !== null"
          @click="confirmDelete"
        >
          {{ deletingId !== null ? 'Borrando…' : 'Borrar' }}
        </button>
      </div>
    </AppModal>
  </section>
</template>

<style scoped>
.calculators-page {
  max-width: 1100px;
}
.card {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}
.card h2 {
  margin: 0;
  font-size: 1.05rem;
}
.card p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}
.button {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 8px;
  background: var(--color-primary);
  color: var(--color-surface);
  text-decoration: none;
}
.history {
  margin-top: 24px;
}
.history h2 {
  margin: 0 0 12px;
  font-size: 1rem;
}
.error-box {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.history-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.history-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 16px;
  padding: 14px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}
.history-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.muted {
  color: var(--color-text-muted);
}
.tag.result {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.history-meta {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
}
.history-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.history-actions .btn,
.delete-action {
  min-height: 44px;
}
.delete-action {
  padding: 0 8px;
}
.modal-error {
  margin-bottom: 12px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}
.danger-button {
  border-color: var(--color-danger);
  color: var(--color-danger);
}
</style>

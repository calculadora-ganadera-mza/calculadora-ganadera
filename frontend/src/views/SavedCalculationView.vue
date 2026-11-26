<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  deleteCarryingCapacityCalculation,
  getCarryingCapacityCalculation,
  type CarryingCapacityCalculation,
} from '@/api/carryingCapacity'
import { ApiError } from '@/api/errors'
import { listParameters, type Parameter } from '@/api/referenceData'
import AppModal from '@/components/AppModal.vue'
import CalculationDetails from '@/components/CalculationDetails.vue'
import CarryingCapacityResults from '@/components/CarryingCapacityResults.vue'
import { oneDecimal, upToOneDecimal } from '@/utils/format'
import { seasonLabel } from '@/utils/season'

const route = useRoute()
const router = useRouter()
const calculation = ref<CarryingCapacityCalculation>()
const parametersByKey = ref<Map<string, Parameter>>(new Map())
const parametersError = ref(false)
const loading = ref(true)
const error = ref('')
const confirmingDelete = ref(false)
const deleting = ref(false)
const deleteError = ref('')

const dateTimeFormat = new Intl.DateTimeFormat('es-AR', {
  dateStyle: 'short',
  timeStyle: 'short',
})
const parameterFormat = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 4 })

const kindLabel = computed(() =>
  calculation.value?.kind === 'result' ? 'Resultado de la campaña' : 'Simulación',
)

const contextLabel = computed(() => {
  const saved = calculation.value
  if (!saved) return ''
  const season = seasonLabel(saved.season_start_date, saved.season_end_date)
  return `${saved.scenario_name} · ${saved.production_unit_name} · campaña ${season}`
})

const savedAtLabel = computed(() =>
  calculation.value ? dateTimeFormat.format(new Date(calculation.value.created_at)) : '',
)

const parameterRows = computed(() => {
  if (!calculation.value) return []
  return Object.entries(calculation.value.reference_values.parameters)
    .map(([key, value]) => {
      const meta = parametersByKey.value.get(key)
      const formatted =
        value === null
          ? 'Sin valor'
          : meta?.unit
            ? `${parameterFormat.format(value)} ${meta.unit}`
            : parameterFormat.format(value)
      return { key, description: meta?.description ?? key, formatted }
    })
    .sort((a, b) => a.description.localeCompare(b.description, 'es'))
})

async function load() {
  loading.value = true
  error.value = ''
  deleteError.value = ''
  parametersError.value = false
  calculation.value = undefined
  const id = Number(route.params.calculationId)
  if (!Number.isInteger(id) || id <= 0) {
    error.value = 'No se encontró el cálculo guardado.'
    loading.value = false
    return
  }
  try {
    const [saved, parameters] = await Promise.all([
      getCarryingCapacityCalculation(id),
      listParameters().catch(() => {
        parametersError.value = true
        return [] as Parameter[]
      }),
    ])
    calculation.value = saved
    parametersByKey.value = new Map(parameters.map((parameter) => [parameter.key, parameter]))
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'No se pudo cargar el cálculo guardado.'
  } finally {
    loading.value = false
  }
}

function askDelete() {
  if (deleting.value) return
  deleteError.value = ''
  confirmingDelete.value = true
}

function cancelDelete() {
  if (deleting.value) return
  confirmingDelete.value = false
}

async function confirmDelete() {
  if (!calculation.value || deleting.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await deleteCarryingCapacityCalculation(calculation.value.id)
    confirmingDelete.value = false
    await router.push({ name: 'calculators' })
  } catch (err) {
    deleteError.value = err instanceof ApiError ? err.message : 'No se pudo borrar el cálculo.'
  } finally {
    deleting.value = false
  }
}

onMounted(load)
watch(
  () => route.params.calculationId,
  () => {
    load()
  },
)
</script>

<template>
  <section class="saved-page">
    <nav class="breadcrumb" aria-label="Ubicación">
      <RouterLink to="/calculators">Calculadoras</RouterLink>
      <span aria-hidden="true">›</span>
      <span>Cálculo guardado</span>
    </nav>

    <p v-if="loading">Cargando cálculo guardado…</p>
    <div v-else-if="error" class="error" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="load">Reintentar</button>
    </div>
    <template v-else-if="calculation">
      <header class="saved-header">
        <div>
          <div class="title-row">
            <h1>Receptividad</h1>
            <span class="tag" :class="{ result: calculation.kind === 'result' }">
              {{ kindLabel }}
            </span>
          </div>
          <p class="subtitle">{{ contextLabel }}</p>
          <p class="subtitle">Guardado el {{ savedAtLabel }}</p>
        </div>
        <button class="btn danger-button" type="button" :disabled="deleting" @click="askDelete">
          Borrar cálculo
        </button>
      </header>
      <p v-if="deleteError && !confirmingDelete" class="error" role="alert">{{ deleteError }}</p>

      <CarryingCapacityResults
        :result="calculation.result"
        :rainfall-mm="calculation.input.rainfall_mm"
      />
      <CalculationDetails
        :result="calculation.result"
        :rainfall-mm="calculation.input.rainfall_mm"
        :herd="calculation.input"
        :categories="calculation.reference_values.animal_categories"
        :bulls-per100-cows="calculation.input.bulls_per_100_cows"
      />

      <details class="reference-values">
        <summary>Valores de referencia usados</summary>
        <div class="reference-body">
          <div class="table-wrap">
            <table class="data-table">
              <caption>
                Categorías animales
              </caption>
              <thead>
                <tr>
                  <th scope="col">Categoría</th>
                  <th scope="col" class="number">EV</th>
                  <th scope="col" class="number">Agua verano (L/día)</th>
                  <th scope="col" class="number">Agua invierno (L/día)</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="category in calculation.reference_values.animal_categories"
                  :key="category.id"
                >
                  <td>{{ category.name }}</td>
                  <td class="number">{{ oneDecimal.format(category.cow_equivalent) }}</td>
                  <td class="number">{{ upToOneDecimal.format(category.summer_water_l_day) }}</td>
                  <td class="number">{{ upToOneDecimal.format(category.winter_water_l_day) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="parameterRows.length" class="table-wrap">
            <p v-if="parametersError" class="hint" role="status">
              No se pudieron cargar las descripciones de los parámetros.
            </p>
            <table class="data-table">
              <caption>
                Parámetros
              </caption>
              <thead>
                <tr>
                  <th scope="col">Parámetro</th>
                  <th scope="col" class="number">Valor</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in parameterRows" :key="row.key">
                  <td>{{ row.description }}</td>
                  <td class="number">{{ row.formatted }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </details>

      <AppModal v-if="confirmingDelete" title="Borrar cálculo guardado" @close="cancelDelete">
        <p>
          ¿Querés borrar
          {{ calculation.kind === 'result' ? 'este resultado de la campaña' : 'esta simulación' }}?
          Esta acción no se puede deshacer.
        </p>
        <p v-if="deleteError" class="error modal-error" role="alert">{{ deleteError }}</p>
        <div class="modal-actions">
          <button class="btn" type="button" :disabled="deleting" @click="cancelDelete">
            Cancelar
          </button>
          <button
            class="btn danger-button"
            type="button"
            :disabled="deleting"
            @click="confirmDelete"
          >
            {{ deleting ? 'Borrando…' : 'Borrar' }}
          </button>
        </div>
      </AppModal>
    </template>
  </section>
</template>

<style scoped>
.saved-page {
  max-width: 1100px;
}
.breadcrumb {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}
.breadcrumb a {
  color: var(--color-primary);
}
.saved-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 24px;
  margin-bottom: 16px;
}
.title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.title-row h1 {
  margin: 0;
}
.tag.result {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.subtitle {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}
.danger-button {
  min-height: 44px;
  border-color: var(--color-danger);
  color: var(--color-danger);
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
.reference-values {
  margin-top: 24px;
}
.reference-values summary {
  font-weight: 600;
  cursor: pointer;
}
.reference-body {
  display: grid;
  gap: 16px;
  margin-top: 12px;
}
.reference-body caption {
  padding: 0 0 6px;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: left;
}
</style>

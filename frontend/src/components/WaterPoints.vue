<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import {
  confirmSharing,
  waterRequest,
  type WaterPoint,
  type WaterPointInput,
} from '@/api/waterPoints'
import type { Position } from '@/api/productionUnits'
const props = defineProps<{
  savedPoints?: WaterPoint[]
  globalCreation?: boolean
  unitName?: string
  unitId: number
  position: Position | null
  selectedPointId?: number | null
}>()
const emit = defineEmits<{
  createRequested: []
  select: [id: number | null]
  mode: [active: boolean]
  points: [points: WaterPoint[]]
  changed: []
  reload: []
  edit: [id: number | null]
}>()
const points = ref<WaterPoint[]>([])
// Las altas desde el mapa actualizan la misma lista que muestra cada tarjeta.
watch(
  () => props.savedPoints,
  (value) => {
    if (value) points.value = value
  },
  { immediate: true },
)
const creating = ref(false)
const loading = ref(props.savedPoints === undefined)
const editing = ref<number | null>(null)
const shared = ref(false)
const name = ref('')
const refill = ref<number | ''>('')
const error = ref('')
const saving = ref(false)
const pendingSharing = ref<WaterPoint | null>(null)
async function load() {
  if (props.savedPoints !== undefined) {
    error.value = ''
    return
  }
  loading.value = true
  error.value = ''
  try {
    points.value = await waterRequest<WaterPoint[]>(
      `/production-units/${props.unitId}/water-points`,
    )
    emit('points', points.value)
  } catch {
    error.value = 'No se pudieron cargar las aguadas.'
  } finally {
    loading.value = false
  }
}
function cancel() {
  creating.value = false
  emit('mode', false)
  error.value = ''
  editing.value = null
  name.value = ''
  refill.value = ''
  emit('edit', null)
}
function create() {
  if (props.globalCreation) {
    emit('createRequested')
    return
  }
  cancel()
  creating.value = true
  name.value = `Aguada ${points.value.length + 1}`
  emit('mode', true)
}
async function edit(point: WaterPoint) {
  if (pendingSharing.value?.id === point.id) pendingSharing.value = null
  emit('select', point.id)
  await nextTick()
  emit('mode', false)
  editing.value = point.id
  shared.value = point.shared
  name.value = point.name
  refill.value = point.refill_l_day ?? ''
  emit('edit', point.id)
}
async function save() {
  const existing = points.value.find((p) => p.id === editing.value)
  const coordinates = props.position ?? existing?.location.coordinates
  if (!coordinates || !name.value.trim()) {
    error.value = 'Marcá una ubicación y completá el nombre.'
    return
  }
  if (
    refill.value !== '' &&
    (!Number.isFinite(Number(refill.value)) || Number(refill.value) <= 0)
  ) {
    error.value = 'Los litros deben ser mayores que cero.'
    return
  }
  saving.value = true
  error.value = ''
  const data: WaterPointInput = {
    shared: props.position || creating.value ? false : shared.value,
    name: name.value.trim(),
    location: { type: 'Point', coordinates },
    refill_l_day: refill.value === '' ? null : Number(refill.value),
  }
  try {
    const saved = await waterRequest<WaterPoint>(
      existing ? `/water-points/${existing.id}` : `/production-units/${props.unitId}/water-points`,
      existing ? 'PUT' : 'POST',
      data,
    )
    let sharingError = ''
    if (props.position || creating.value) {
      try {
        await confirmSharing(saved)
        pendingSharing.value = null
      } catch {
        pendingSharing.value = saved
        sharingError = 'La aguada se guardó, pero no se pudo confirmar el uso compartido.'
      }
    }
    cancel()
    await load()
    emit('changed')
    if (sharingError) error.value = sharingError
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo guardar la aguada.'
  } finally {
    saving.value = false
  }
}
async function retrySharing() {
  const point = pendingSharing.value
  if (!point) return
  saving.value = true
  try {
    await waterRequest(`/water-points/${point.id}`, 'PUT', {
      name: point.name,
      location: point.location,
      refill_l_day: point.refill_l_day,
      shared: true,
    })
    pendingSharing.value = null
    await load()
    emit('changed')
  } catch {
    error.value = 'No se pudo confirmar el uso compartido. La aguada sigue guardada.'
  } finally {
    saving.value = false
  }
}
async function remove(point: WaterPoint) {
  if (!window.confirm(`¿Eliminar la aguada «${point.name}»?`)) return
  saving.value = true
  try {
    await waterRequest(`/water-points/${point.id}`, 'DELETE')
    if (pendingSharing.value?.id === point.id) pendingSharing.value = null
    cancel()
    await load()
    emit('changed')
  } catch {
    error.value = 'No se pudo eliminar la aguada.'
  } finally {
    saving.value = false
  }
}
watch(
  () => props.selectedPointId,
  () => {
    if (!creating.value) cancel()
  },
)
function confirmPosition() {
  emit('mode', false)
  void save()
}
defineExpose({ create, cancel, confirmPosition, load })
watch(
  () => props.unitId,
  () => {
    cancel()
    void load()
  },
  { immediate: true },
)
</script>
<template>
  <section class="water-points">
    <header>
      <h4>AGUADAS ({{ points.length }})</h4>
      <button class="quick" :disabled="saving" @click="create">+ Ubicar aguada</button>
    </header>
    <p v-if="loading">Cargando aguadas…</p>
    <ul v-else-if="points.length" class="point-list">
      <li
        v-for="point in points"
        :key="point.id"
        :class="{ selected: selectedPointId === point.id }"
      >
        <div class="point-row">
          <button class="point-choice" @click="emit('select', point.id)">
            <span class="water-dot"></span>{{ point.name }}
            <small>({{ point.refill_l_day?.toLocaleString('es-AR') ?? '—' }} L/día)</small></button
          ><button :disabled="saving" @click="edit(point)">Editar</button
          ><button :disabled="saving" @click="remove(point)">Eliminar</button>
        </div>
        <p v-if="point.shared && !point.neighbor_unit_ids.length" role="status">
          Esta aguada ya no está en el límite con otro sector y no se está compartiendo.
        </p>
        <form v-if="editing === point.id" @submit.prevent="save">
          <label>Nombre<input v-model="name" required maxlength="100" :disabled="saving" /></label
          ><label
            >Litros que repone por día<input
              v-model="refill"
              type="number"
              min="0"
              step="any"
              :disabled="saving"
          /></label>

          <label
            ><input v-model="shared" type="checkbox" :disabled="saving" />Compartida con los
            sectores vecinos</label
          >
          <div class="actions">
            <button type="button" class="move" @click="emit('mode', true)">Mover punto</button
            ><button type="button" :disabled="saving" @click="cancel">Cancelar</button
            ><button class="quick" :disabled="saving">Guardar aguada</button>
          </div>
        </form>
      </li>
    </ul>
    <div v-else class="empty">
      <p>Este lote no tiene ninguna aguada asignada</p>
      <button class="quick" @click="create">Agregar aguada en {{ unitName ?? 'este lote' }}</button>
    </div>
    <form v-if="creating" @submit.prevent="save">
      <label>Nombre<input v-model="name" required maxlength="100" :disabled="saving" /></label
      ><label
        >Litros que repone por día (opcional)<input
          v-model="refill"
          type="number"
          min="0"
          step="any"
          :disabled="saving"
      /></label>
      <div class="actions">
        <button class="quick" :disabled="saving">Guardar aguada</button
        ><button type="button" :disabled="saving" @click="cancel">Cancelar</button>
      </div>
    </form>
    <button v-if="pendingSharing" :disabled="saving" @click="retrySharing">
      Reintentar uso compartido
    </button>
    <p v-if="error" role="alert">
      {{ error }}
      <button :disabled="saving" @click="savedPoints === undefined ? load() : emit('reload')">
        Reintentar carga
      </button>
    </p>
  </section>
</template>
<style scoped>
.water-points,
form {
  display: grid;
  gap: 10px;
  min-width: 0;
}
header,
.point-row,
.actions {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}
header {
  justify-content: space-between;
}
h4,
p {
  margin: 0;
}
h4 {
  font-size: 11px;
  letter-spacing: 0.06em;
  color: #d1d5db;
}
button,
input {
  font: inherit;
  border: 1px solid #344034;
  border-radius: 7px;
  padding: 5px 7px;
  color: #e5e7eb;
  background: #222822;
  font-size: 11px;
}
button {
  cursor: pointer;
}
button:disabled {
  opacity: 0.5;
  cursor: default;
}
.point-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}
li {
  background: #1c201c;
  border: 1px solid #2e382e;
  border-radius: 12px;
  padding: 10px;
  min-width: 0;
}
li.selected {
  border-color: #38bdf8;
}
.point-choice {
  border: 0;
  background: none;
  padding: 0;
  text-align: left;
  flex: 1;
  min-width: 100px;
  font-weight: 700;
  overflow-wrap: anywhere;
}
small {
  color: #9ca3af;
  font-weight: 400;
}
.water-dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #38bdf8;
  margin-right: 6px;
}
.quick {
  color: #4ade80;
  background: #1f3824;
  border-color: #2f5738;
}
header .quick {
  border: 0;
  background: none;
}
.empty {
  border: 1px dashed #344034;
  border-radius: 12px;
  text-align: center;
  padding: 12px;
  color: #9ca3af;
  font-size: 11px;
  display: grid;
  gap: 8px;
}
.empty button {
  width: 100%;
}
label {
  display: grid;
  gap: 4px;
  color: #9ca3af;
  font-size: 11px;
}
input[type='checkbox'] {
  width: auto;
}
input {
  width: 100%;
  min-width: 0;
  background: #141714;
}
form {
  padding-top: 8px;
  border-top: 1px solid #2e382e;
}
.move {
  color: #7dd3fc;
  border-color: #38bdf866;
}
[role='alert'] {
  color: #fca5a5;
  font-size: 12px;
}
</style>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import UnitsMap from './UnitsMap.vue'
import {
  ApiError,
  createProductionUnit,
  deleteProductionUnit,
  listProductionUnits,
  updateProductionUnit,
  type PolygonGeoJSON,
  type ProductionUnit,
} from '@/api/productionUnits'

const props = defineProps<{ scenarioId: number }>()

const units = ref<ProductionUnit[]>([])
const loading = ref(true)
const loadError = ref('')
const actionError = ref('')
const saving = ref(false)
// Contorno recién dibujado, a la espera de un nombre
const draft = ref<PolygonGeoJSON | null>(null)
const draftName = ref('')
//Sector con el contorno en edición y el contorno nuevo, si se movió
const editingId = ref<number | null>(null)
const reshaped = ref<PolygonGeoJSON | null>(null)

function hectares(value: number): string {
  return value.toLocaleString('es-AR', { maximumFractionDigits: 1 })
}

function messageOf(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    units.value = await listProductionUnits(props.scenarioId)
  } catch {
    loadError.value = 'No se pudieron cargar los sectores.'
  } finally {
    loading.value = false
  }
}

function onDraw(polygon: PolygonGeoJSON) {
  draft.value = polygon
  draftName.value = ''
  editingId.value = null
  actionError.value = ''
}

function cancelDraft() {
  draft.value = null
  actionError.value = ''
}

async function saveDraft() {
  const name = draftName.value.trim()
  if (!name) {
    actionError.value = 'Falta el nombre del sector.'
    return
  }
  const polygon = draft.value
  if (!polygon) return
  saving.value = true
  actionError.value = ''
  try {
    const unit = await createProductionUnit(props.scenarioId, { name, polygon })
    units.value = [...units.value, unit]
    // Solo se limpia si no se dibujó otro contorno mientras se guardaba
    if (draft.value === polygon) draft.value = null
  } catch (err) {
    actionError.value = messageOf(err, 'No se pudo guardar el sector.')
  } finally {
    saving.value = false
  }
}

function startEditing(unit: ProductionUnit) {
  editingId.value = unit.id
  reshaped.value = null
  draft.value = null
  actionError.value = ''
}

function cancelEditing() {
  // Al dejar de editar, el mapa vuelve a dibujar el contorno guardado
  editingId.value = null
  actionError.value = ''
}

async function saveShape(unit: ProductionUnit) {
  const polygon = reshaped.value
  if (!polygon) {
    cancelEditing()
    return
  }
  saving.value = true
  actionError.value = ''
  try {
    const updated = await updateProductionUnit(unit.id, {
      name: unit.name,
      polygon,
    })
    units.value = units.value.map((item) => (item.id === updated.id ? updated : item))
    // Solo se cierra si no se empezó otra edición mientras se guardaba
    if (editingId.value === unit.id && reshaped.value === polygon) editingId.value = null
  } catch (err) {
    actionError.value = messageOf(err, 'No se pudo guardar el contorno.')
  } finally {
    saving.value = false
  }
}

async function remove(unit: ProductionUnit) {
  const question = `¿Eliminar el sector «${unit.name}»? También se borran sus aguadas y rodeos.`
  if (!window.confirm(question)) return
  actionError.value = ''
  try {
    await deleteProductionUnit(unit.id)
    units.value = units.value.filter((item) => item.id !== unit.id)
    if (editingId.value === unit.id) editingId.value = null
  } catch (err) {
    actionError.value = messageOf(err, 'No se pudo eliminar el sector.')
  }
}

onMounted(load)
</script>

<template>
  <section class="units">
    <h3>Sectores</h3>

    <p v-if="loading">Cargando sectores…</p>

    <div v-else-if="loadError" role="alert">
      <p>{{ loadError }}</p>
      <button type="button" @click="load">Reintentar</button>
    </div>

    <template v-else>
      <p v-if="editingId !== null" class="hint">
        Para cambiar el contorno, mover sus vértices en el mapa.
      </p>
      <p v-else class="hint">
        Para agregar un sector, dibujar su contorno con la herramienta de polígono del mapa.
      </p>

      <UnitsMap
        :units="units"
        :draft="draft"
        :editing-id="editingId"
        @draw="onDraw"
        @reshape="reshaped = $event"
      />

      <form v-if="draft" class="draft" novalidate @submit.prevent="saveDraft">
        <label for="unit-name">Nombre del sector</label>
        <input id="unit-name" v-model="draftName" type="text" maxlength="100" autocomplete="off" />
        <button type="submit" :disabled="saving">Guardar</button>
        <button type="button" @click="cancelDraft">Cancelar</button>
      </form>

      <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>

      <ul v-if="units.length > 0" class="unit-list">
        <li v-for="unit in units" :key="unit.id">
          <span class="unit-name">{{ unit.name }}: {{ hectares(unit.area_ha) }} ha</span>
          <template v-if="editingId === unit.id">
            <button type="button" :disabled="saving" @click="saveShape(unit)">
              Guardar contorno
            </button>
            <button type="button" @click="cancelEditing">Cancelar</button>
          </template>
          <template v-else>
            <button type="button" @click="startEditing(unit)">Editar contorno</button>
            <button type="button" @click="remove(unit)">Eliminar</button>
          </template>
        </li>
      </ul>
      <p v-else-if="!draft">Todavía no hay sectores.</p>
    </template>
  </section>
</template>

<style scoped>
.units {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.units h3 {
  margin: 0;
  font-size: 1rem;
}

.hint {
  margin: 0;
  color: var(--color-text-muted);
}

.draft,
.unit-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.draft input {
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
}

.unit-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.unit-name {
  flex: 1;
}

.error {
  margin: 0;
  color: var(--color-danger);
}

button {
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  cursor: pointer;
}

button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ApiError } from '@/api/errors'
import {
  createHerd,
  listAnimalCategories,
  listHerds,
  updateHerd,
  type AnimalCategory,
  type HerdData,
  type Herd,
} from '@/api/herds'
import HerdDataForm from './HerdDataForm.vue'

const props = defineProps<{ seasonId: number; unitId: number }>()

const loading = ref(true)
// La carga falló: no se muestra el formulario y se puede reintentar
const loadError = ref('')
const saving = ref(false)
const error = ref('')
const saved = ref(false)

const categories = ref<AnimalCategory[]>([])
const herdId = ref<number>()
const initialHerd = ref<Herd>()

// El formulario se muestra abierto: la pantalla del sector tiene un solo rodeo
async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [loadedCategories, herds] = await Promise.all([
      listAnimalCategories(),
      listHerds(props.seasonId),
    ])
    categories.value = loadedCategories
    initialHerd.value = herds.find((herd) => herd.production_unit_id === props.unitId)
    herdId.value = initialHerd.value?.id
  } catch {
    loadError.value = 'No se pudieron cargar los datos del rodeo.'
  } finally {
    loading.value = false
  }
}

function clearStatus() {
  saved.value = false
  error.value = ''
}

async function save(data: HerdData) {
  saving.value = true
  try {
    const herd = herdId.value
      ? await updateHerd(herdId.value, data)
      : await createHerd(props.seasonId, { ...data, production_unit_id: props.unitId })
    herdId.value = herd.id
    saved.value = true
  } catch (err) {
    error.value =
      err instanceof ApiError ? err.message : 'No se pudieron guardar los datos. Probá de nuevo.'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="herd">
    <p v-if="loading">Cargando…</p>
    <div v-else-if="loadError" role="alert">
      <p class="error">{{ loadError }}</p>
      <button type="button" class="btn" @click="load">Reintentar</button>
    </div>
    <HerdDataForm
      v-else
      :categories="categories"
      :id-prefix="unitId"
      :initial="initialHerd"
      :busy="saving"
      :action="saving ? 'Guardando…' : 'Guardar rodeo'"
      :error="error"
      @attempt="clearStatus"
      @submit="save"
    >
      <template #status>
        <p v-if="saved" class="saved" role="status">Datos guardados.</p>
      </template>
    </HerdDataForm>
  </div>
</template>

<style scoped>
.saved {
  margin: 0;
  color: var(--color-success);
}

/* Botón principal, como lo hace la calculadora con el mismo formulario */
.herd :deep(button[type='submit']) {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid var(--color-primary);
  border-radius: 8px;
  background: var(--color-primary);
  color: var(--color-surface);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.herd :deep(button[type='submit']:disabled) {
  opacity: 0.6;
  cursor: default;
}
</style>

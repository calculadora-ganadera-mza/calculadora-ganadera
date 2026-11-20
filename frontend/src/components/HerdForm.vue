<script setup lang="ts">
import { ref } from 'vue'
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

const open = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const saved = ref(false)

const categories = ref<AnimalCategory[]>([])
const herdId = ref<number>()
const initialHerd = ref<Herd>()

async function toggle() {
  open.value = !open.value
  if (!open.value || loading.value || categories.value.length > 0) return
  loading.value = true
  error.value = ''
  try {
    const [loadedCategories, herds] = await Promise.all([
      listAnimalCategories(),
      listHerds(props.seasonId),
    ])
    categories.value = loadedCategories
    initialHerd.value = herds.find((herd) => herd.production_unit_id === props.unitId)
    herdId.value = initialHerd.value?.id
  } catch {
    error.value = 'No se pudieron cargar los datos del sector.'
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
</script>

<template>
  <div class="herd">
    <button type="button" :aria-expanded="open" @click="toggle">
      {{ open ? 'Ocultar animales y datos' : 'Animales y datos de la campaña' }}
    </button>

    <p v-if="open && loading">Cargando…</p>

    <HerdDataForm
      v-if="!loading && (open || categories.length > 0)"
      v-show="open"
      :categories="categories"
      :id-prefix="unitId"
      :initial="initialHerd"
      :busy="saving"
      :action="saving ? 'Guardando…' : 'Guardar'"
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
.herd {
  flex-basis: 100%;
}

.saved {
  margin: 0;
  color: var(--color-success);
}
</style>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ApiError } from '@/api/errors'
import { listAnimalCategories, type AnimalCategory } from '@/api/herds'
import { listParameters, updateAnimalCategory, updateParameter } from '@/api/referenceData'

// Cada fila guarda lo que se está editando y el resultado del último guardado
interface ParameterRow {
  key: string
  description: string
  unit: string
  draft: number | ''
  status: string
  error: string
}

interface CategoryRow {
  category: AnimalCategory
  name: string
  cowEquivalent: number | ''
  summerWater: number | ''
  winterWater: number | ''
  status: string
  error: string
}

const parameters = ref<ParameterRow[]>([])
const categories = ref<CategoryRow[]>([])
const loading = ref(true)
const loadError = ref('')

const toCategoryRow = (category: AnimalCategory): CategoryRow => ({
  category,
  name: category.name,
  cowEquivalent: category.cow_equivalent,
  summerWater: category.summer_water_l_day,
  winterWater: category.winter_water_l_day,
  status: '',
  error: '',
})

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [loadedParameters, loadedCategories] = await Promise.all([
      listParameters(),
      listAnimalCategories(),
    ])
    parameters.value = loadedParameters.map((p) => ({
      key: p.key,
      description: p.description,
      unit: p.unit,
      draft: p.value ?? '',
      status: '',
      error: '',
    }))
    categories.value = loadedCategories.map(toCategoryRow)
  } catch {
    loadError.value = 'No se pudieron cargar los valores de referencia.'
  } finally {
    loading.value = false
  }
}

const messageOf = (err: unknown, fallback: string) =>
  err instanceof ApiError ? err.message : fallback

async function saveParameter(row: ParameterRow) {
  row.status = ''
  row.error = ''
  if (row.draft !== '' && row.draft <= 0) {
    row.error = 'El valor tiene que ser mayor que 0.'
    return
  }
  try {
    const saved = await updateParameter(row.key, row.draft === '' ? null : row.draft)
    row.draft = saved.value ?? ''
    row.status = 'Guardado.'
  } catch (err) {
    row.error = messageOf(err, 'No se pudo guardar. Volver a intentar.')
  }
}

async function saveCategory(row: CategoryRow) {
  row.status = ''
  row.error = ''
  const numbers = [row.cowEquivalent, row.summerWater, row.winterWater]
  if (!row.name.trim()) {
    row.error = 'El nombre no puede quedar vacío.'
    return
  }
  if (numbers.some((value) => value === '' || value <= 0)) {
    row.error = 'El EV y el agua tienen que ser mayores que 0.'
    return
  }
  try {
    const saved = await updateAnimalCategory(row.category.id, {
      name: row.name.trim(),
      cow_equivalent: Number(row.cowEquivalent),
      summer_water_l_day: Number(row.summerWater),
      winter_water_l_day: Number(row.winterWater),
    })
    Object.assign(row, toCategoryRow(saved), { status: 'Guardado.' })
  } catch (err) {
    row.error = messageOf(err, 'No se pudo guardar. Volver a intentar.')
  }
}

onMounted(load)
</script>

<template>
  <section class="admin-page">
    <h1>Administración</h1>
    <p class="subtitle">
      Valores de referencia que usa la calculadora. Un cambio se aplica en el próximo cálculo.
    </p>

    <p v-if="loading">Cargando…</p>
    <div v-else-if="loadError" role="alert">
      <p>{{ loadError }}</p>
      <button type="button" @click="load">Reintentar</button>
    </div>

    <template v-else>
      <section class="card" aria-labelledby="parameters-title">
        <h2 id="parameters-title">Parámetros</h2>
        <p class="hint">Los índices pueden quedar vacíos hasta que se conozca su valor.</p>
        <table>
          <thead>
            <tr>
              <th scope="col">Parámetro</th>
              <th scope="col">Valor</th>
              <th scope="col">Unidad</th>
              <th scope="col"><span class="sr-only">Acciones</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in parameters" :key="row.key">
              <td>
                <label :for="`param-${row.key}`">{{ row.description }}</label>
                <code>{{ row.key }}</code>
              </td>
              <td>
                <input
                  :id="`param-${row.key}`"
                  v-model.number="row.draft"
                  type="number"
                  step="any"
                  min="0"
                  placeholder="Sin cargar"
                />
              </td>
              <td>{{ row.unit }}</td>
              <td>
                <button type="button" @click="saveParameter(row)">Guardar</button>
                <p v-if="row.error" class="error" role="alert">{{ row.error }}</p>
                <p v-if="row.status" class="saved" role="status">{{ row.status }}</p>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="card" aria-labelledby="categories-title">
        <h2 id="categories-title">Categorías de animales</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Nombre</th>
              <th scope="col">EV</th>
              <th scope="col">Agua en verano (l/día)</th>
              <th scope="col">Agua en invierno (l/día)</th>
              <th scope="col"><span class="sr-only">Acciones</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in categories" :key="row.category.id">
              <td>
                <input
                  v-model="row.name"
                  type="text"
                  maxlength="100"
                  :aria-label="`Nombre de ${row.category.code}`"
                />
                <code>{{ row.category.code }}</code>
              </td>
              <td>
                <input
                  v-model.number="row.cowEquivalent"
                  type="number"
                  step="any"
                  min="0"
                  :aria-label="`EV de ${row.category.name}`"
                />
              </td>
              <td>
                <input
                  v-model.number="row.summerWater"
                  type="number"
                  step="any"
                  min="0"
                  :aria-label="`Agua en verano de ${row.category.name}`"
                />
              </td>
              <td>
                <input
                  v-model.number="row.winterWater"
                  type="number"
                  step="any"
                  min="0"
                  :aria-label="`Agua en invierno de ${row.category.name}`"
                />
              </td>
              <td>
                <button type="button" @click="saveCategory(row)">Guardar</button>
                <p v-if="row.error" class="error" role="alert">{{ row.error }}</p>
                <p v-if="row.status" class="saved" role="status">{{ row.status }}</p>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </section>
</template>

<style scoped>
.admin-page {
  max-width: 1100px;
}

.subtitle,
.hint {
  color: var(--color-text-muted);
}

.hint {
  margin: 0 0 12px;
  font-size: 0.85rem;
}

.card {
  margin-top: 16px;
  padding: 18px;
  overflow-x: auto;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}

.card h2 {
  margin: 0 0 8px;
  font-size: 1rem;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 8px;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  vertical-align: top;
}

th {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-text-muted);
}

td label {
  display: block;
}

code {
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 0.75rem;
}

input {
  width: 100%;
  min-width: 80px;
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
}

.error,
.saved {
  margin: 4px 0 0;
  font-size: 0.8rem;
}

.error {
  color: var(--color-danger);
}

.saved {
  color: var(--color-success);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
</style>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError } from '@/api/errors'
import {
  createHerd,
  listAnimalCategories,
  listHerds,
  updateHerd,
  type AnimalCategory,
  type HerdData,
  type RangeCondition,
} from '@/api/herds'

const props = defineProps<{ seasonId: number; unitId: number }>()

// Aclaraciones de la issue #11 sobre qué animales entran en cada categoría
const HELP: Record<string, string> = {
  cow: 'Todas, con o sin ternero, incluidas las vaquillonas ya entoradas.',
  heifer: 'Las de más de un año que todavía no se entoraron.',
}

const RANGE_CONDITIONS: { value: RangeCondition; label: string }[] = [
  { value: 'fair', label: 'Regular' },
  { value: 'good', label: 'Bueno' },
  { value: 'very_good', label: 'Muy bueno' },
]

const open = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const saved = ref(false)

const categories = ref<AnimalCategory[]>([])
const herdId = ref<number | null>(null)
const quantities = ref<Record<number, number | ''>>({})
const rangeCondition = ref<RangeCondition | ''>('')
const replacementPct = ref<number | ''>('')
const weaningPct = ref<number | ''>('')
const earlyWeaning = ref(false)
const supplemented = ref(false)
const breedingStart = ref('')
const breedingEnd = ref('')

// Los terneros no se cargan: los calcula la aplicación
const formCategories = computed(() => categories.value.filter((c) => c.code !== 'calf'))

// 0,6 → 60 y al revés, sin decimales de más
const toPct = (rate: number | null) => (rate === null ? '' : Math.round(rate * 1000) / 10)
const toRate = (pct: number | '') => (pct === '' ? null : Math.round(pct * 10) / 1000)

async function toggle() {
  open.value = !open.value
  if (!open.value || categories.value.length > 0) return
  loading.value = true
  error.value = ''
  try {
    const [loadedCategories, herds] = await Promise.all([
      listAnimalCategories(),
      listHerds(props.seasonId),
    ])
    categories.value = loadedCategories
    const herd = herds.find((h) => h.production_unit_id === props.unitId)
    if (herd) {
      herdId.value = herd.id
      for (const item of herd.categories) quantities.value[item.animal_category_id] = item.quantity
      rangeCondition.value = herd.range_condition
      replacementPct.value = toPct(herd.replacement_rate)
      weaningPct.value = toPct(herd.weaning_rate)
      earlyWeaning.value = herd.early_weaning
      supplemented.value = herd.supplemented
      breedingStart.value = herd.breeding_start ?? ''
      breedingEnd.value = herd.breeding_end ?? ''
    }
  } catch {
    error.value = 'No se pudieron cargar los datos del sector.'
  } finally {
    loading.value = false
  }
}

// Revisa el formulario; devuelve el primer problema o '' si está bien
function validate(): string {
  const counts = formCategories.value.map((c) => quantities.value[c.id])
  if (counts.some((q) => q !== '' && q !== undefined && (q < 0 || !Number.isInteger(q))))
    return 'Las cantidades tienen que ser números enteros, sin negativos.'
  if (!rangeCondition.value) return 'Elegí el estado del campo.'
  for (const pct of [replacementPct.value, weaningPct.value])
    if (pct !== '' && (pct < 0 || pct > 100)) return 'Los porcentajes van de 0 a 100.'
  if (Boolean(breedingStart.value) !== Boolean(breedingEnd.value))
    return 'El entore se carga con inicio y fin, o sin ninguno.'
  if (breedingStart.value && breedingEnd.value <= breedingStart.value)
    return 'El fin del entore tiene que ser posterior al inicio.'
  const cow = formCategories.value.find((c) => c.code === 'cow')
  const cows = cow ? Number(quantities.value[cow.id] || 0) : 0
  if (cows > 0 && (replacementPct.value === '' || weaningPct.value === '' || !breedingStart.value))
    return 'Si hay vacas, hacen falta el porcentaje de reposición, el de destete y el período de entore.'
  return ''
}

async function save() {
  saved.value = false
  error.value = validate()
  if (error.value || !rangeCondition.value) return

  const data: HerdData = {
    categories: formCategories.value
      .filter((c) => quantities.value[c.id] !== '' && quantities.value[c.id] !== undefined)
      .map((c) => ({ animal_category_id: c.id, quantity: Number(quantities.value[c.id]) })),
    range_condition: rangeCondition.value,
    replacement_rate: toRate(replacementPct.value),
    weaning_rate: toRate(weaningPct.value),
    early_weaning: earlyWeaning.value,
    supplemented: supplemented.value,
    breeding_start: breedingStart.value || null,
    breeding_end: breedingEnd.value || null,
  }
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

    <form v-else-if="open" class="herd-form" novalidate @submit.prevent="save">
      <fieldset>
        <legend>Animales</legend>
        <p class="hint">Los terneros no se cargan: los calcula la aplicación.</p>
        <div v-for="category in formCategories" :key="category.id" class="field">
          <label :for="`qty-${unitId}-${category.id}`">{{ category.name }}</label>
          <input
            :id="`qty-${unitId}-${category.id}`"
            v-model.number="quantities[category.id]"
            type="number"
            min="0"
            step="1"
            inputmode="numeric"
          />
          <p v-if="HELP[category.code]" class="hint">{{ HELP[category.code] }}</p>
        </div>
      </fieldset>

      <fieldset>
        <legend>Datos de la campaña</legend>
        <div class="field">
          <label :for="`range-${unitId}`">Estado del campo</label>
          <select :id="`range-${unitId}`" v-model="rangeCondition">
            <option value="" disabled>Elegir…</option>
            <option v-for="option in RANGE_CONDITIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="field">
          <label :for="`replacement-${unitId}`">Reposición (%)</label>
          <input
            :id="`replacement-${unitId}`"
            v-model.number="replacementPct"
            type="number"
            min="0"
            max="100"
            step="0.1"
          />
        </div>
        <div class="field">
          <label :for="`weaning-${unitId}`">Destete (%)</label>
          <input
            :id="`weaning-${unitId}`"
            v-model.number="weaningPct"
            type="number"
            min="0"
            max="100"
            step="0.1"
          />
        </div>
        <label class="check">
          <input v-model="earlyWeaning" type="checkbox" />
          Destete precoz <span class="hint">(si no se marca, el destete es a los 6 meses)</span>
        </label>
        <label class="check">
          <input v-model="supplemented" type="checkbox" />
          Suplementación
        </label>
        <div class="field">
          <label :for="`breeding-start-${unitId}`">Inicio del entore</label>
          <input :id="`breeding-start-${unitId}`" v-model="breedingStart" type="date" />
        </div>
        <div class="field">
          <label :for="`breeding-end-${unitId}`">Fin del entore</label>
          <input :id="`breeding-end-${unitId}`" v-model="breedingEnd" type="date" />
        </div>
      </fieldset>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="saved" class="saved" role="status">Datos guardados.</p>
      <button type="submit" :disabled="saving">{{ saving ? 'Guardando…' : 'Guardar' }}</button>
    </form>

    <p v-else-if="error" class="error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.herd {
  flex-basis: 100%;
}

.herd-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 480px;
  margin-top: 8px;
}

fieldset {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

legend {
  padding: 0 4px;
  font-weight: 600;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field label {
  font-weight: 600;
}

input:not([type='checkbox']),
select {
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
}

.check {
  display: flex;
  align-items: center;
  gap: 8px;
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

button {
  align-self: flex-start;
}
</style>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AnimalCategory, HerdData, RangeCondition } from '@/api/herds'
import { RANGE_CONDITION_LABELS } from '@/utils/herd'

const props = defineProps<{
  categories: AnimalCategory[]
  idPrefix: number | string
  initial?: HerdData
  busy: boolean
  disabled?: boolean
  error: string
  action: string
}>()
const emit = defineEmits<{ attempt: []; submit: [data: HerdData] }>()

// Aclaraciones de la issue #11 sobre qué animales entran en cada categoría
const HELP: Record<string, string> = {
  cow: 'Todas, con o sin ternero, incluidas las vaquillonas ya entoradas.',
  heifer: 'Las de más de un año que todavía no se entoraron.',
}

const RANGE_CONDITIONS = Object.entries(RANGE_CONDITION_LABELS).map(([value, label]) => ({
  value: value as RangeCondition,
  label,
}))

const validationError = ref('')
const initial = props.initial
const quantities = ref<Record<number, number | ''>>(
  Object.fromEntries(
    initial?.categories.map((item) => [item.animal_category_id, item.quantity]) ?? [],
  ),
)
const toPct = (rate?: number | null) => (rate == null ? '' : Number((rate * 100).toPrecision(15)))
const rangeCondition = ref<RangeCondition | ''>(initial?.range_condition ?? '')
const replacementPct = ref<number | ''>(toPct(initial?.replacement_rate))
const weaningPct = ref<number | ''>(toPct(initial?.weaning_rate))
const earlyWeaning = ref(initial?.early_weaning ?? false)
const supplemented = ref(initial?.supplemented ?? false)
const breedingStart = ref(initial?.breeding_start ?? '')
const breedingEnd = ref(initial?.breeding_end ?? '')

const formCategories = computed(() => props.categories.filter((c) => c.code !== 'calf'))

function toRate(pct: number | '', original?: number | null) {
  if (pct === '') return null
  return original != null && pct === toPct(original) ? original : pct / 100
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

function submit() {
  if (props.busy || props.disabled) return
  emit('attempt')
  validationError.value = validate()
  if (validationError.value || !rangeCondition.value) return

  const data: HerdData = {
    categories: formCategories.value
      .filter((c) => quantities.value[c.id] !== '' && quantities.value[c.id] !== undefined)
      .map((c) => ({ animal_category_id: c.id, quantity: Number(quantities.value[c.id]) })),
    range_condition: rangeCondition.value,
    replacement_rate: toRate(replacementPct.value, initial?.replacement_rate),
    weaning_rate: toRate(weaningPct.value, initial?.weaning_rate),
    early_weaning: earlyWeaning.value,
    supplemented: supplemented.value,
    breeding_start: breedingStart.value || null,
    breeding_end: breedingEnd.value || null,
  }
  emit('submit', data)
}
</script>

<template>
  <form class="herd-form" novalidate @submit.prevent="submit">
    <slot />
    <fieldset :disabled="busy">
      <legend>Animales</legend>
      <p class="hint">Los terneros no se cargan: los calcula la aplicación.</p>
      <div v-for="category in formCategories" :key="category.id" class="field">
        <label :for="`qty-${idPrefix}-${category.id}`">{{ category.name }}</label>
        <input
          :id="`qty-${idPrefix}-${category.id}`"
          v-model.number="quantities[category.id]"
          type="number"
          min="0"
          step="1"
          inputmode="numeric"
        />
        <p v-if="HELP[category.code]" class="hint">{{ HELP[category.code] }}</p>
      </div>
    </fieldset>

    <fieldset :disabled="busy">
      <legend>Datos de la campaña</legend>
      <div class="field">
        <label :for="`range-${idPrefix}`">Estado del campo</label>
        <select :id="`range-${idPrefix}`" v-model="rangeCondition">
          <option value="" disabled>Elegir…</option>
          <option v-for="option in RANGE_CONDITIONS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </div>
      <div class="field">
        <label :for="`replacement-${idPrefix}`">Reposición (%)</label>
        <input
          :id="`replacement-${idPrefix}`"
          v-model.number="replacementPct"
          type="number"
          min="0"
          max="100"
          step="any"
        />
      </div>
      <div class="field">
        <label :for="`weaning-${idPrefix}`">Destete (%)</label>
        <input
          :id="`weaning-${idPrefix}`"
          v-model.number="weaningPct"
          type="number"
          min="0"
          max="100"
          step="any"
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
        <label :for="`breeding-start-${idPrefix}`">Inicio del entore</label>
        <input :id="`breeding-start-${idPrefix}`" v-model="breedingStart" type="date" />
      </div>
      <div class="field">
        <label :for="`breeding-end-${idPrefix}`">Fin del entore</label>
        <input :id="`breeding-end-${idPrefix}`" v-model="breedingEnd" type="date" />
      </div>
    </fieldset>

    <p v-if="validationError || error" class="error" role="alert">{{ validationError || error }}</p>
    <slot name="status" />
    <button type="submit" :disabled="busy || disabled">{{ action }}</button>
  </form>
</template>

<style scoped>
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

button {
  align-self: flex-start;
}
</style>

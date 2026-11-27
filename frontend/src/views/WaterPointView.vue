<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import FarmBreadcrumb from '@/components/FarmBreadcrumb.vue'
import UnitsMap from '@/components/UnitsMap.vue'
import { loadScenarioMap, type ScenarioMap } from '@/api/farm'
import type { Position } from '@/api/productionUnits'
import {
  confirmSharing,
  waterRequest,
  type WaterPoint,
  type WaterPointInput,
} from '@/api/waterPoints'
import { keepSeason, routeId } from '@/utils/farm'

// Una sola pantalla para ubicar una aguada nueva y para editar una existente
const route = useRoute()
const router = useRouter()
const data = ref<ScenarioMap>()
const loading = ref(true)
// La carga falló y se puede reintentar
const error = ref('')
// La dirección trae un escenario, sector o aguada que no existe: reintentar no sirve
const missing = ref('')
const name = ref('')
const refill = ref<number | ''>('')
const shared = ref(false)
// Ubicación marcada o movida en el mapa; null mientras no se toca
const position = ref<Position | null>(null)
const saving = ref(false)
const saveError = ref('')
// La aguada ya se guardó pero falló la confirmación del uso compartido
const savedWithWarning = ref(false)
let loadVersion = 0

const isNew = computed(() => route.name === 'new-water-point')
const unitId = computed(() => routeId(route.params.unitId))
const unit = computed(() => data.value?.units.find((item) => item.id === unitId.value))
const unitList = computed(() => (unit.value ? [unit.value] : []))
const neighbors = computed(() => (data.value?.units ?? []).filter((item) => item !== unit.value))
const ownPoints = computed<WaterPoint[]>(() =>
  (data.value?.waterPoints ?? []).filter((point) => point.production_unit_id === unitId.value),
)
const point = computed(() =>
  ownPoints.value.find((item) => item.id === routeId(route.params.waterPointId)),
)
const sectorRoute = computed(() => ({
  name: 'sector',
  params: { scenarioId: route.params.scenarioId, unitId: route.params.unitId },
  query: keepSeason(route.query),
}))

async function load() {
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  missing.value = ''
  data.value = undefined
  position.value = null
  saveError.value = ''
  savedWithWarning.value = false
  const scenarioId = routeId(route.params.scenarioId)
  try {
    const loaded = scenarioId === null ? null : await loadScenarioMap(scenarioId)
    if (version !== loadVersion) return
    data.value = loaded ?? undefined
    if (!loaded) missing.value = 'No se encontró el escenario.'
    else if (!unit.value) missing.value = 'No se encontró este sector en el escenario.'
    else if (!isNew.value && !point.value)
      missing.value = 'No se encontró la aguada en este sector.'
    else if (point.value) {
      name.value = point.value.name
      refill.value = point.value.refill_l_day ?? ''
      shared.value = point.value.shared
    } else {
      name.value = `Aguada ${ownPoints.value.length + 1}`
      refill.value = ''
    }
  } catch {
    if (version === loadVersion) error.value = 'No se pudo cargar la aguada. Volver a intentar.'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

function validate(coordinates: Position | undefined): string {
  if (!coordinates) return 'Falta marcar la ubicación de la aguada en el sector.'
  if (!name.value.trim()) return 'Falta el nombre de la aguada.'
  if (refill.value !== '' && (!Number.isFinite(Number(refill.value)) || Number(refill.value) <= 0))
    return 'Los litros deben ser mayores que cero.'
  return ''
}

async function save() {
  if (!unit.value) return
  const coordinates = position.value ?? point.value?.location.coordinates
  saveError.value = validate(coordinates)
  if (saveError.value || !coordinates) return
  const moved = position.value !== null
  const body: WaterPointInput = {
    // Una aguada nueva o movida se guarda sin compartir: el uso compartido
    // se confirma después con los vecinos de su ubicación
    shared: moved || isNew.value ? false : shared.value,
    name: name.value.trim(),
    location: { type: 'Point', coordinates },
    refill_l_day: refill.value === '' ? null : Number(refill.value),
  }
  saving.value = true
  try {
    const saved = isNew.value
      ? await waterRequest<WaterPoint>(
          `/production-units/${unit.value.id}/water-points`,
          'POST',
          body,
        )
      : await waterRequest<WaterPoint>(`/water-points/${point.value!.id}`, 'PUT', body)
    if (moved) {
      try {
        await confirmSharing(saved)
      } catch {
        saveError.value = 'La aguada se guardó, pero no se pudo confirmar el uso compartido.'
        savedWithWarning.value = true
        return
      }
    }
    await router.push(sectorRoute.value)
  } catch (err) {
    // El punto vuelve a marcarse: lo más común es que haya quedado fuera del sector
    position.value = null
    saveError.value = err instanceof Error ? err.message : 'No se pudo guardar la aguada.'
  } finally {
    saving.value = false
  }
}

watch(() => [route.params.scenarioId, route.params.unitId, route.params.waterPointId], load, {
  immediate: true,
})
</script>

<template>
  <section class="water-page">
    <FarmBreadcrumb
      :steps="[
        {
          label: data?.scenario.name ?? 'Escenario',
          to: {
            name: 'scenario',
            params: { scenarioId: route.params.scenarioId },
            query: keepSeason(route.query),
          },
        },
        { label: unit?.name ?? 'Sector', to: sectorRoute },
        { label: isNew ? 'Nueva aguada' : (point?.name ?? 'Aguada') },
      ]"
    />
    <h1>{{ isNew ? 'Nueva aguada' : 'Editar aguada' }}</h1>
    <p v-if="loading">Cargando…</p>
    <p v-else-if="missing" class="error" role="alert">{{ missing }}</p>
    <div v-else-if="error" role="alert">
      <p class="error">{{ error }}</p>
      <button type="button" class="btn" @click="load">Reintentar</button>
    </div>
    <div v-else-if="unit" class="layout">
      <div class="map-box panel">
        <p class="hint">
          {{
            isNew
              ? 'Tocar el mapa dentro del sector. Después se puede arrastrar el punto para ajustarlo.'
              : 'Arrastrar el punto para mover la aguada.'
          }}
        </p>
        <UnitsMap
          :units="unitList"
          :reference-units="neighbors"
          :draft="null"
          :editing-id="null"
          :water-points="ownPoints"
          :water-mode="isNew"
          :editing-water-id="point?.id ?? null"
          :water-position="position"
          read-only
          @locate="position = $event"
        />
      </div>
      <form class="panel side" novalidate @submit.prevent="save">
        <div class="field">
          <label for="water-name">Nombre</label>
          <input id="water-name" v-model="name" maxlength="100" autocomplete="off" />
        </div>
        <div class="field">
          <label for="water-refill">Litros que repone por día (opcional)</label>
          <p class="hint">Lo que repone, no lo que almacena.</p>
          <input
            id="water-refill"
            v-model="refill"
            type="number"
            min="0"
            step="any"
            inputmode="decimal"
          />
        </div>
        <label v-if="!isNew" class="check">
          <input v-model="shared" type="checkbox" :disabled="position !== null" />
          Compartida con los sectores vecinos
        </label>
        <p v-if="!isNew && position !== null" class="hint">
          Al moverla, se vuelve a preguntar si la comparte con los vecinos de la nueva ubicación.
        </p>
        <p v-if="saveError" class="error" role="alert">{{ saveError }}</p>
        <div class="actions">
          <RouterLink v-if="savedWithWarning" class="btn btn-primary" :to="sectorRoute">
            Volver al sector
          </RouterLink>
          <template v-else>
            <button class="btn btn-primary" :disabled="saving">
              {{ saving ? 'Guardando…' : 'Guardar aguada' }}
            </button>
            <RouterLink class="text-button" :to="sectorRoute">Cancelar</RouterLink>
          </template>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.water-page {
  max-width: 1100px;
}

h1 {
  font-size: 1.6rem;
  letter-spacing: -0.025em;
  margin-bottom: 16px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(240px, 1fr);
  gap: 16px;
  align-items: start;
}

.map-box {
  display: grid;
  gap: 10px;
}

.side {
  display: grid;
  gap: 14px;
}

.check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

.actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

@media (max-width: 800px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>

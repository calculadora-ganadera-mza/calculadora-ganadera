<script setup lang="ts">
import { computed } from 'vue'
import type { LoadThermometer } from '@/api/carryingCapacity'

const props = defineProps<{
  load: LoadThermometer
  // Rodeo máximo del resultado: la carga se compara con él
  maxCowEquivalents: number
}>()

const LABELS = { below: 'Por debajo', within: 'Dentro', above: 'Por encima' }

const oneDecimal = new Intl.NumberFormat('es-AR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})
const tickNumber = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 })

const current = computed(() => oneDecimal.format(props.load.current_cow_equivalents))
const max = computed(() => oneDecimal.format(props.maxCowEquivalents))

// Parte del rodeo máximo que ocupa el rodeo actual
const percent = computed(() =>
  Math.round((props.load.current_cow_equivalents / props.maxCowEquivalents) * 100),
)

// Qué significa el estado, con los EV que lo separan de los otros dos
const statusHint = computed(() => {
  const below = oneDecimal.format(props.load.below_cow_equivalents)
  return {
    below: `Menos de ${below} EV.`,
    within: `Entre ${below} y ${max.value} EV, el rodeo máximo.`,
    above: `Más de ${max.value} EV, el rodeo máximo.`,
  }[props.load.status]
})

const TICK_COUNT = 4
const ROUND_FACTORS = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]

// Eje del gráfico: va de 0 a un número redondo apenas mayor que el mayor de
// los dos valores, para que ni la barra ni la línea queden pegadas al borde.
// Solo ubica elementos en pantalla.
const scale = computed(() => {
  const top = Math.max(props.load.current_cow_equivalents, props.maxCowEquivalents) * 1.1
  const rawStep = top / TICK_COUNT
  const magnitude = 10 ** Math.floor(Math.log10(rawStep))
  const factor = ROUND_FACTORS.find((value) => value * magnitude >= rawStep) ?? 10
  const step = factor * magnitude
  return {
    end: step * TICK_COUNT,
    ticks: Array.from({ length: TICK_COUNT + 1 }, (_, index) => index * step),
  }
})

const position = (value: number) => `${(value / scale.value.end) * 100}%`
</script>

<template>
  <section class="load" aria-labelledby="load-heading">
    <h2 id="load-heading">Carga del sector</h2>
    <div class="chart" :class="load.status">
      <span class="label">Rodeo actual</span>
      <p class="value">{{ current }} <span class="unit">EV</span></p>
      <p class="sub">
        <span class="percent">{{ percent }} % del rodeo máximo</span>
        <span class="term">
          <button type="button" aria-describedby="tip-load-status">
            <span class="tag status">{{ LABELS[load.status] }}</span>
          </button>
          <span id="tip-load-status" class="tip" role="tooltip">{{ statusHint }}</span>
        </span>
      </p>
      <div
        class="meter"
        role="meter"
        aria-label="Rodeo actual"
        aria-valuemin="0"
        :aria-valuemax="scale.end"
        :aria-valuenow="load.current_cow_equivalents"
        :aria-valuetext="`${current} EV de un rodeo máximo de ${max} EV (${percent} %)`"
      >
        <div class="track"></div>
        <div class="fill" :style="{ width: position(load.current_cow_equivalents) }"></div>
        <div class="line" :style="{ left: position(maxCowEquivalents) }"></div>
        <span class="line-label" :style="{ left: position(maxCowEquivalents) }">
          Rodeo máximo {{ max }}
        </span>
        <div class="axis">
          <span
            v-for="(tick, index) in scale.ticks"
            :key="tick"
            class="tick"
            :style="{ left: position(tick) }"
          >
            {{ tickNumber.format(tick) }}<template v-if="index === TICK_COUNT"> EV</template>
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.load {
  margin-top: 24px;
}

h2 {
  margin: 0 0 8px;
  font-size: 1rem;
}

/* Color de cada estado: lo usan la etiqueta y la barra */
.below {
  --status-color: var(--color-warning);
  --status-soft: var(--color-warning-soft);
}

.within {
  --status-color: var(--color-primary);
  --status-soft: var(--color-primary-soft);
}

.above {
  --status-color: var(--color-danger);
  --status-soft: color-mix(in srgb, var(--color-danger) 12%, var(--color-surface));
}

.chart {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 20px 24px 16px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
}

.chart p {
  margin: 0;
}

.label {
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 500;
}

.value {
  font-size: 2rem;
  font-weight: 600;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.unit {
  color: var(--color-text-muted);
  font-size: 0.95rem;
  font-weight: 500;
}

.sub {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}

.status {
  background: var(--status-soft);
  color: var(--status-color);
}

.meter {
  position: relative;
  height: 60px;
  margin-top: 8px;
  font-variant-numeric: tabular-nums;
}

.track,
.fill {
  position: absolute;
  top: 22px;
  left: 0;
  height: 10px;
  border-radius: 0 4px 4px 0;
}

.track {
  right: 0;
  background: var(--color-border);
}

.fill {
  background: var(--status-color);
}

.line {
  position: absolute;
  top: 15px;
  width: 2px;
  height: 24px;
  margin-left: -1px;
  background: var(--color-text);
}

.line-label,
.tick {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  line-height: 1.2;
  white-space: nowrap;
}

.line-label {
  font-size: 0.75rem;
  font-weight: 500;
}

.axis {
  position: absolute;
  inset: 44px 0 0;
}

.tick {
  color: var(--color-text-muted);
  font-size: 0.7rem;
}

.tick:first-child {
  transform: none;
}

.tick:last-child {
  transform: translateX(-100%);
}
</style>

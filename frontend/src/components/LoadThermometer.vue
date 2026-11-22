<script setup lang="ts">
import { computed } from 'vue'
import type { LoadThermometer } from '@/api/carryingCapacity'

const props = defineProps<{ load: LoadThermometer }>()

const labels = {
  below: 'Por debajo',
  within: 'Dentro',
  above: 'Por encima',
}

const oneDecimal = new Intl.NumberFormat('es-AR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

// La escala solo posiciona los elementos del gráfico con los EV que entrega la API.
const trackStyle = computed(() => {
  const load = props.load
  const end = Math.max(load.current_cow_equivalents, load.max_cow_equivalents) * 1.1
  const position = (value: number) => `${end > 0 ? (value / end) * 100 : 0}%`
  return {
    '--below': position(load.below_cow_equivalents),
    '--limit': position(load.max_cow_equivalents),
    '--current': position(load.current_cow_equivalents),
  }
})
</script>

<template>
  <section class="load" aria-labelledby="sector-load">
    <header>
      <h2 id="sector-load">Carga del sector</h2>
      <span class="status" :class="load.status">{{ labels[load.status] }} de la capacidad</span>
    </header>
    <div class="chart">
      <div class="track" :style="trackStyle" aria-hidden="true">
        <div class="current"></div>
        <div class="limit"></div>
      </div>
      <ul class="legend">
        <li class="current-key">
          Rodeo actual <strong>{{ oneDecimal.format(load.current_cow_equivalents) }} EV</strong>
        </li>
        <li class="limit-key">
          Límite de mi rodeo <strong>{{ oneDecimal.format(load.max_cow_equivalents) }} EV</strong>
        </li>
        <li v-for="(label, status) in labels" :key="status" :class="status">{{ label }}</li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.load {
  --below-color: var(--color-hover);
  --within-color: var(--color-primary-soft);
  --above-color: color-mix(in srgb, var(--color-danger) 9%, var(--color-surface));
  margin-top: 24px;
}

header,
.legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

header {
  justify-content: space-between;
  gap: 8px 16px;
  margin-bottom: 8px;
}

h2 {
  margin: 0;
  font-size: 1rem;
}

.status {
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--zone-color);
  font-size: 0.8rem;
  font-weight: 600;
}

.below {
  --zone-color: var(--below-color);
}

.within {
  --zone-color: var(--within-color);
}

.above {
  --zone-color: var(--above-color);
}

.status.within {
  color: var(--color-primary);
}

.status.above {
  color: var(--color-danger);
}

.chart {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
}

.track {
  position: relative;
  display: flex;
  align-items: center;
  height: 26px;
  border-radius: 4px;
  background: linear-gradient(
    to right,
    var(--below-color) 0 var(--below),
    var(--within-color) var(--below) var(--limit),
    var(--above-color) var(--limit) 100%
  );
}

.current {
  width: var(--current);
  height: 10px;
  border-radius: 2px;
  background: var(--color-text);
}

.limit {
  position: absolute;
  inset-block: 1px;
  left: var(--limit);
  width: 2px;
  background: var(--color-primary);
}

.legend {
  gap: 6px 16px;
  margin: 12px 0 0;
  padding: 0;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  list-style: none;
}

.legend li::before {
  display: inline-block;
  width: 10px;
  height: 7px;
  margin-right: 6px;
  border: 1px solid var(--color-border);
  background: var(--zone-color);
  content: '';
}

.legend .current-key::before {
  border-color: var(--color-text);
  background: var(--color-text);
}

.legend .limit-key::before {
  width: 2px;
  height: 10px;
  border: 0;
  background: var(--color-primary);
}

strong {
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}
</style>

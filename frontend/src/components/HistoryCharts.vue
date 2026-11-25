<script setup lang="ts">
import { computed } from 'vue'
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  type ChartOptions,
} from 'chart.js'
import { Bar, Line } from 'vue-chartjs'
import type { HistoryEntry } from '@/api/history'
import { headCount, historyCategories, percent } from '@/utils/history'

ChartJS.register(BarElement, CategoryScale, Legend, LinearScale, LineElement, PointElement, Tooltip)

// labels: el nombre de cada campaña, en el mismo orden que entries
const props = defineProps<{ entries: HistoryEntry[]; labels: string[] }>()

// Un color por categoría, en el orden en que aparecen
const PALETTE = ['#3d6b35', '#2678a7', '#c47a2c', '#8a6bb0', '#b8434e', '#6b8e23']
const WEANING_COLOR = '#2678a7'
const REPLACEMENT_COLOR = '#c47a2c'
const RAIN_COLOR = '#5b9bd5'

// Chart.js dibuja en un canvas y no lee el CSS: los colores del tema se leen al abrir
const theme = getComputedStyle(document.documentElement)
const textColor = theme.getPropertyValue('--color-text-muted').trim() || '#6b665d'
const gridColor = theme.getPropertyValue('--color-border').trim() || '#ddd8cd'

// Opciones comunes de los tres gráficos; sirven tanto para barras como para líneas
// max: tope del eje, como 100 en los porcentajes
function options(yTitle: string, stacked = false, max?: number) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' as const, labels: { color: textColor } } },
    scales: {
      x: { stacked, ticks: { color: textColor }, grid: { display: false } },
      y: {
        stacked,
        beginAtZero: true,
        max,
        title: { display: true, text: yTitle, color: textColor },
        ticks: { color: textColor, precision: 0 },
        grid: { color: gridColor },
      },
    },
  }
}

const hasHerds = computed(() => props.entries.some((entry) => entry.categories.length > 0))

const animals = computed(() => ({
  labels: props.labels,
  datasets: historyCategories(props.entries).map((category, index) => ({
    label: category.name,
    data: props.entries.map((entry) => headCount(entry, category.id)),
    backgroundColor: PALETTE[index % PALETTE.length],
  })),
}))

const rates = computed(() => ({
  labels: props.labels,
  datasets: [
    {
      label: 'Destete',
      data: props.entries.map((entry) => percent(entry.weaning_rate)),
      borderColor: WEANING_COLOR,
      backgroundColor: WEANING_COLOR,
    },
    {
      label: 'Reposición',
      data: props.entries.map((entry) => percent(entry.replacement_rate)),
      borderColor: REPLACEMENT_COLOR,
      backgroundColor: REPLACEMENT_COLOR,
    },
  ],
}))

const rainfall = computed(() => ({
  labels: props.labels,
  datasets: [
    {
      label: 'Lluvia de la campaña anterior',
      data: props.entries.map((entry) => entry.rainfall_mm),
      backgroundColor: RAIN_COLOR,
    },
  ],
}))

const animalOptions: ChartOptions<'bar'> = options('Cabezas', true)
const rateOptions: ChartOptions<'line'> = options('%', false, 100)
const rainOptions: ChartOptions<'bar'> = options('mm')
</script>

<template>
  <div class="charts">
    <section class="panel chart-panel wide">
      <h2>Animales por campaña</h2>
      <p v-if="!hasHerds" class="hint">Todavía no hay rodeos cargados en este sector.</p>
      <div class="chart">
        <Bar
          :data="animals"
          :options="animalOptions"
          aria-label="Animales por categoría en cada campaña"
        />
      </div>
    </section>
    <section class="panel chart-panel">
      <h2>Destete y reposición</h2>
      <div class="chart">
        <Line
          :data="rates"
          :options="rateOptions"
          aria-label="Porcentaje de destete y de reposición en cada campaña"
        />
      </div>
    </section>
    <section class="panel chart-panel">
      <h2>Lluvia</h2>
      <div class="chart">
        <Bar :data="rainfall" :options="rainOptions" aria-label="Lluvia de cada campaña" />
      </div>
      <p class="hint">
        La lluvia de cada campaña es la de la campaña anterior, de julio a junio: la que se cargó
        para calcular.
      </p>
    </section>
  </div>
</template>

<style scoped>
.charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.wide {
  grid-column: 1 / -1;
}

.chart-panel {
  display: grid;
  gap: 8px;
}

h2 {
  margin: 0;
  font-size: 0.95rem;
}

.chart {
  position: relative;
  height: 260px;
}

.wide .chart {
  height: 300px;
}

@media (max-width: 800px) {
  .charts {
    grid-template-columns: 1fr;
  }
}
</style>

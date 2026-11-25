import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import HistoryCharts from '../HistoryCharts.vue'
import type { HistoryEntry } from '@/api/history'

// jsdom no tiene canvas: los gráficos se reemplazan por piezas que guardan sus datos
vi.mock('vue-chartjs', async () => {
  const { defineComponent, h } = await import('vue')
  const chart = (name: string) =>
    defineComponent({ name, props: ['data', 'options'], render: () => h('div') })
  return { Bar: chart('Bar'), Line: chart('Line') }
})

const ENTRIES: HistoryEntry[] = [
  {
    season_id: 1,
    start_year: 2025,
    categories: [],
    replacement_rate: null,
    weaning_rate: null,
    rainfall_mm: 260,
  },
  {
    season_id: 2,
    start_year: 2026,
    categories: [
      { animal_category_id: 1, name: 'Vaca', quantity: 80 },
      { animal_category_id: 2, name: 'Toro', quantity: 3 },
    ],
    replacement_rate: 0.2,
    weaning_rate: 0.65,
    rainfall_mm: null,
  },
]

function open() {
  return mount(HistoryCharts, { props: { entries: ENTRIES, labels: ['2025/26', '2026/27'] } })
}

describe('HistoryCharts', () => {
  it('apila los animales por categoría y deja sin barra la campaña sin rodeo', () => {
    const [animals] = open().findAllComponents({ name: 'Bar' })

    expect(animals!.props('data')).toMatchObject({
      labels: ['2025/26', '2026/27'],
      datasets: [
        { label: 'Vaca', data: [null, 80] },
        { label: 'Toro', data: [null, 3] },
      ],
    })
    expect(animals!.props('options')).toMatchObject({
      scales: { x: { stacked: true }, y: { stacked: true } },
    })
  })

  it('muestra destete y reposición en porcentaje y la lluvia en mm', () => {
    const wrapper = open()
    const rates = wrapper.getComponent({ name: 'Line' })
    const rainfall = wrapper.findAllComponents({ name: 'Bar' })[1]!

    expect(rates.props('data').datasets.map((d: { data: unknown }) => d.data)).toEqual([
      [null, 65],
      [null, 20],
    ])
    expect(rainfall.props('data').datasets[0].data).toEqual([260, null])
    expect(wrapper.text()).toContain('es la de la campaña anterior, de julio a junio')
  })

  it('avisa si el sector no tiene rodeos cargados', () => {
    const wrapper = mount(HistoryCharts, {
      props: { entries: [ENTRIES[0]!], labels: ['2025/26'] },
    })

    expect(wrapper.text()).toContain('Todavía no hay rodeos cargados en este sector.')
  })
})

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import CalculatorsView from '../CalculatorsView.vue'
import {
  deleteCarryingCapacityCalculation,
  listUserCarryingCapacityCalculations,
  type CarryingCapacityCalculationSummary,
} from '@/api/carryingCapacity'

vi.mock('@/api/carryingCapacity', () => ({
  listUserCarryingCapacityCalculations: vi.fn(),
  deleteCarryingCapacityCalculation: vi.fn(),
}))

function summary(
  id: number,
  kind: 'result' | 'simulation',
  createdAt: string,
): CarryingCapacityCalculationSummary {
  return {
    id,
    production_unit_id: 2,
    season_id: 12,
    scenario_name: 'La Esperanza',
    production_unit_name: 'Potrero Norte',
    season_start_date: '2026-07-01',
    season_end_date: '2027-06-30',
    kind,
    created_at: createdAt,
    rainfall_mm: 300,
    carrying_capacity_ha_per_cow_equivalent: 15.1,
    max_herd_cow_equivalents: 65,
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listUserCarryingCapacityCalculations).mockResolvedValue([
    summary(20, 'result', '2026-11-26T15:00:00Z'),
    summary(19, 'simulation', '2026-11-25T15:00:00Z'),
  ])
  vi.mocked(deleteCarryingCapacityCalculation).mockResolvedValue()
})

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/calculators', name: 'calculators', component: CalculatorsView },
      { path: '/calculators/carrying-capacity', name: 'carrying-capacity', component: {} },
      {
        path: '/calculators/carrying-capacity/calculations/:calculationId',
        name: 'carrying-capacity-saved',
        component: {},
      },
    ],
  })
  await router.push('/calculators')
  const wrapper = mount(RouterView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('Calculadoras', () => {
  it('muestra el historial de cálculos guardados debajo de la tarjeta y pide confirmación al borrar', async () => {
    const wrapper = await open()

    expect(listUserCarryingCapacityCalculations).toHaveBeenCalledTimes(1)
    const items = wrapper.findAll('.history-item')
    expect(items).toHaveLength(2)
    expect(items[0]!.text()).toContain('La Esperanza · Potrero Norte')
    expect(items[0]!.text()).toContain('campaña 2026/27')
    expect(items[0]!.text()).toContain('Resultado de la campaña')
    expect(items[0]!.get('a').attributes('href')).toBe(
      '/calculators/carrying-capacity/calculations/20',
    )
    expect(items[0]!.get('a').text()).toContain(
      'cálculo de La Esperanza, Potrero Norte, campaña 2026/27',
    )
    expect(items[1]!.text()).toContain('Simulación')

    // Al pulsar Borrar abre un único diálogo de confirmación sin borrar todavía
    await items[0]!.get('button').trigger('click')
    expect(deleteCarryingCapacityCalculation).not.toHaveBeenCalled()
    const dialogs = document.body.querySelectorAll('[role="dialog"]')
    expect(dialogs).toHaveLength(1)
    const dialog = dialogs[0]!
    expect(dialog.textContent).toContain('este resultado de la campaña')

    // Al confirmar borra el cálculo y cierra el diálogo
    const confirmButton = [...dialog.querySelectorAll('button')].find(
      (button) => button.textContent?.trim() === 'Borrar',
    )!
    confirmButton.click()
    await flushPromises()

    expect(deleteCarryingCapacityCalculation).toHaveBeenCalledWith(20)
    expect(wrapper.findAll('.history-item')).toHaveLength(1)
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
  })
})

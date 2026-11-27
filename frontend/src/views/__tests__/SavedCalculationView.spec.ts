import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import SavedCalculationView from '../SavedCalculationView.vue'
import {
  deleteCarryingCapacityCalculation,
  getCarryingCapacityCalculation,
  type CarryingCapacityCalculation,
} from '@/api/carryingCapacity'
import { ApiError } from '@/api/errors'
import { listParameters } from '@/api/referenceData'

vi.mock('@/api/carryingCapacity', () => ({
  getCarryingCapacityCalculation: vi.fn(),
  deleteCarryingCapacityCalculation: vi.fn(),
}))
vi.mock('@/api/referenceData', () => ({
  listParameters: vi.fn(),
}))

const saved: CarryingCapacityCalculation = {
  id: 20,
  production_unit_id: 2,
  season_id: 12,
  scenario_name: 'La Esperanza',
  production_unit_name: 'Potrero Norte',
  season_start_date: '2026-07-01',
  season_end_date: '2027-06-30',
  kind: 'result',
  created_at: '2026-11-26T15:00:00Z',
  season_updated: false,
  input: {
    categories: [{ animal_category_id: 1, quantity: 40 }],
    range_condition: 'good',
    replacement_rate: 0.2,
    weaning_rate: 0.7,
    early_weaning: false,
    supplemented: false,
    breeding_start: '2026-11-01',
    breeding_end: '2027-01-31',
    rainfall_mm: 300,
  },
  reference_values: {
    parameters: { cow_equivalent_dm_intake_kg_year: 3285, water_point_radius_km: 2.5 },
    animal_categories: [
      {
        id: 1,
        code: 'cow',
        name: 'Vaca histórica',
        cow_equivalent: 1,
        summer_water_l_day: 70,
        winter_water_l_day: 37.5,
      },
    ],
  },
  result: {
    area_ha: 1000,
    usable_area_ha: 980,
    carrying_capacity_ha_per_cow_equivalent: 15.1,
    pasture_limit_cow_equivalents: 65,
    pasture_breakdown: {
      cow_equivalent_dm_intake_kg_year: 3285,
      consumable_forage_kg_ha_year: 217.8,
      base_carrying_capacity_ha_per_cow_equivalent: 15.1,
      indices: [],
    },
    water: {
      evaluated: false,
      limit_cow_equivalents: null,
      refill_l_day: null,
      summer_need_l_day: null,
      winter_need_l_day: null,
    },
    max_herd: { cow_equivalents: 65, limited_by: 'pasture' },
    max_breeding_herd: null,
    scaled_herd: null,
    load_thermometer: {
      status: 'below',
      current_cow_equivalents: 40,
      below_cow_equivalents: 58.5,
    },
    warnings: [],
  },
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getCarryingCapacityCalculation).mockResolvedValue(saved)
  vi.mocked(deleteCarryingCapacityCalculation).mockResolvedValue()
  vi.mocked(listParameters).mockResolvedValue([
    {
      key: 'cow_equivalent_dm_intake_kg_year',
      description: 'Consumo anual de materia seca de un EV',
      value: 3285,
      unit: 'kg MS/año',
      producer_editable: false,
    },
    {
      key: 'water_point_radius_km',
      description: 'Alcance de una aguada',
      value: 2.5,
      unit: 'km',
      producer_editable: false,
    },
  ])
})

describe('Cálculo guardado', () => {
  it('muestra el resultado y los valores de referencia en español tal como se guardaron', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/calculators', name: 'calculators', component: {} },
        {
          path: '/calculators/carrying-capacity/calculations/:calculationId',
          component: SavedCalculationView,
        },
      ],
    })
    await router.push('/calculators/carrying-capacity/calculations/20')
    const wrapper = mount(RouterView, { global: { plugins: [router] } })
    await flushPromises()

    expect(getCarryingCapacityCalculation).toHaveBeenCalledWith(20)
    expect(wrapper.text()).toContain('Resultado de la campaña')
    expect(wrapper.text()).toContain('La Esperanza')
    expect(wrapper.text()).toContain('Potrero Norte')
    expect(wrapper.text()).toContain('2026/27')
    expect(wrapper.text()).toContain('Vaca histórica')

    const refText = wrapper.get('details.reference-values').text()
    expect(refText).toContain('Consumo anual de materia seca de un EV')
    expect(refText).toContain('3.285 kg MS/año')
    expect(refText).toContain('Alcance de una aguada')
    expect(refText).toContain('2,5 km')
    expect(refText).not.toContain('cow_equivalent_dm_intake_kg_year')

    await wrapper.get('.danger-button').trigger('click')
    expect(deleteCarryingCapacityCalculation).not.toHaveBeenCalled()
    const dialogs = document.body.querySelectorAll('[role="dialog"]')
    expect(dialogs).toHaveLength(1)
    const dialog = dialogs[0]!
    const confirmButton = [...dialog.querySelectorAll('button')].find(
      (button) => button.textContent?.trim() === 'Borrar',
    )!
    confirmButton.click()
    await flushPromises()

    expect(deleteCarryingCapacityCalculation).toHaveBeenCalledWith(20)
    expect(router.currentRoute.value.name).toBe('calculators')
  })

  it('si falla el borrado muestra un único role="alert" dentro del modal', async () => {
    vi.mocked(deleteCarryingCapacityCalculation).mockRejectedValue(
      new ApiError('No se pudo borrar.'),
    )
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/calculators', name: 'calculators', component: {} },
        {
          path: '/calculators/carrying-capacity/calculations/:calculationId',
          component: SavedCalculationView,
        },
      ],
    })
    await router.push('/calculators/carrying-capacity/calculations/20')
    const wrapper = mount(RouterView, { global: { plugins: [router] } })
    await flushPromises()

    await wrapper.get('.danger-button').trigger('click')
    const dialog = document.body.querySelector('[role="dialog"]')!
    const confirmButton = [...dialog.querySelectorAll('button')].find(
      (button) => button.textContent?.trim() === 'Borrar',
    )!
    confirmButton.click()
    await flushPromises()

    expect(wrapper.findAll('[role="alert"]')).toHaveLength(0)
    const alerts = document.body.querySelectorAll('[role="alert"]')
    expect(alerts).toHaveLength(1)
    expect(alerts[0]!.textContent).toBe('No se pudo borrar.')
    expect(confirmButton.hasAttribute('disabled')).toBe(false)
    wrapper.unmount()
  })
})

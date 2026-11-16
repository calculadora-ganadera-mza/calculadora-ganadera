import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import CarryingCapacityResultView from '../CarryingCapacityResultView.vue'
import { calculateCarryingCapacity } from '@/api/carryingCapacity'
import { ApiError } from '@/api/errors'
import { listHerds } from '@/api/herds'
import { listProductionUnits } from '@/api/productionUnits'
import { listScenarios, listSeasons } from '@/api/scenarios'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', () => ({ listProductionUnits: vi.fn() }))
vi.mock('@/api/herds', () => ({ listHerds: vi.fn() }))
vi.mock('@/api/carryingCapacity', () => ({ calculateCarryingCapacity: vi.fn() }))

const season = {
  id: 12,
  start_year: 2026,
  start_date: '2026-07-01',
  end_date: '2027-06-30',
  rainfall_mm: 300,
  is_current: true,
}
const herd = {
  id: 30,
  season_id: 12,
  production_unit_id: 2,
  categories: [],
  range_condition: 'good' as const,
  replacement_rate: null,
  weaning_rate: null,
  early_weaning: false,
  supplemented: false,
  breeding_start: null,
  breeding_end: null,
}
const result = {
  area_ha: 1000,
  usable_area_ha: 981.8,
  carrying_capacity_ha_per_cow_equivalent: 15.1,
  pasture_limit_cow_equivalents: 65.02,
  recommended_herd: null,
  warnings: [],
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([{ id: 7, name: 'La Esperanza', is_main: true }])
  vi.mocked(listSeasons).mockResolvedValue([season])
  vi.mocked(listProductionUnits).mockResolvedValue([
    {
      id: 2,
      name: 'Sector 1',
      area_ha: 1000,
      usable_area_ha: 981.8,
      polygon: { type: 'Polygon', coordinates: [] },
    },
  ])
  vi.mocked(listHerds).mockResolvedValue([herd])
  vi.mocked(calculateCarryingCapacity).mockResolvedValue(result)
})

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/calc/:scenarioId/:unitId/:seasonId', component: CarryingCapacityResultView },
      { path: '/farm/:scenarioId/sectors/:unitId', name: 'sector', component: {} },
      { path: '/:other(.*)', component: {} },
    ],
  })
  await router.push('/calc/7/2/12')
  const wrapper = mount(RouterView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('Resultado de receptividad', () => {
  it('calcula con el rodeo y la lluvia de la campaña y muestra receptividad y límite por pasto', async () => {
    const wrapper = await open()

    expect(calculateCarryingCapacity).toHaveBeenCalledWith(2, { ...herd, rainfall_mm: 300 })
    expect(wrapper.find('.subtitle').text()).toContain('La Esperanza · Sector 1 · campaña 2026/27')
    expect(wrapper.findAll('.kpi .value').map((value) => value.text())).toEqual([
      '15,1 ha/EV',
      '65,0 EV',
    ])
    expect(wrapper.findAll('.kpi .sub').map((sub) => sub.text())).toEqual([
      '300 mm de lluvia',
      '981,8 ha aprovechables',
    ])
    expect(wrapper.find('.tag').exists()).toBe(false)
  })

  it('marca la receptividad si se calculó sin algún índice', async () => {
    vi.mocked(calculateCarryingCapacity).mockResolvedValue({
      ...result,
      warnings: [
        {
          code: 'missing_index',
          message: 'Falta cargar algún índice de corrección: se calculó sin él.',
        },
      ],
    })

    const wrapper = await open()

    expect(wrapper.find('.tag').text()).toBe('Falta un índice')
  })

  it('explica cada término con un tooltip asociado a su botón', async () => {
    const wrapper = await open()
    const buttons = wrapper.findAll('.term button')

    expect(buttons.map((button) => button.text())).toEqual(['Receptividad', 'Límite por pasto'])
    for (const button of buttons) {
      const tip = wrapper.get(`#${button.attributes('aria-describedby')}`)
      expect(tip.attributes('role')).toBe('tooltip')
    }
  })

  it.each([null, 0])('pide la lluvia si es %s, sin calcular', async (rainfall) => {
    vi.mocked(listSeasons).mockResolvedValue([{ ...season, rainfall_mm: rainfall }])

    const wrapper = await open()

    expect(calculateCarryingCapacity).not.toHaveBeenCalled()
    expect(wrapper.find('[role="alert"]').text()).toContain('falta cargar la lluvia')
  })

  it('pide los datos de la campaña si el sector no tiene rodeo', async () => {
    vi.mocked(listHerds).mockResolvedValue([{ ...herd, production_unit_id: 99 }])

    const wrapper = await open()

    expect(calculateCarryingCapacity).not.toHaveBeenCalled()
    expect(wrapper.find('[role="alert"]').text()).toContain('falta cargar los datos de la campaña')
  })

  it('muestra el aviso del backend cuando no se puede calcular', async () => {
    const detail = 'El sector no tiene superficie aprovechable.'
    vi.mocked(calculateCarryingCapacity).mockRejectedValue(new ApiError(detail))

    const wrapper = await open()

    expect(wrapper.find('[role="alert"]').text()).toContain(detail)
    expect(wrapper.find('.kpis').exists()).toBe(false)
  })
})

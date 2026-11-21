import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { createPinia } from 'pinia'
import CarryingCapacityView from '../CarryingCapacityView.vue'
import CarryingCapacityResultView from '../CarryingCapacityResultView.vue'
import { listAnimalCategories, listHerds } from '@/api/herds'
import { listProductionUnits } from '@/api/productionUnits'
import { listScenarios, listSeasons } from '@/api/scenarios'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', () => ({ listProductionUnits: vi.fn() }))
vi.mock('@/api/herds', () => ({ listAnimalCategories: vi.fn(), listHerds: vi.fn() }))

const season = {
  id: 12,
  start_year: 2026,
  start_date: '2026-07-01',
  end_date: '2027-06-30',
  rainfall_mm: 300,
  is_current: true,
}
const unit = {
  id: 2,
  name: 'Sector 1',
  area_ha: 100,
  usable_area_ha: 60,
  polygon: { type: 'Polygon' as const, coordinates: [] },
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listHerds).mockResolvedValue([])
  vi.mocked(listScenarios).mockResolvedValue([
    { id: 7, name: 'La Esperanza', is_main: true },
    { id: 8, name: 'El Molle', is_main: false },
  ])
  vi.mocked(listSeasons).mockResolvedValue([
    { ...season, id: 11, start_date: '2025-07-01', end_date: '2026-06-30', is_current: false },
    season,
  ])
  vi.mocked(listProductionUnits).mockResolvedValue([unit, { ...unit, id: 3, name: 'Sector 2' }])
})
afterEach(() => vi.unstubAllGlobals())

const EmptyView = { render: () => null }

async function open(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/calc', name: 'carrying-capacity', component: CarryingCapacityView },
      {
        path: '/calc/:scenarioId/:unitId/:seasonId',
        name: 'carrying-capacity-result',
        component: CarryingCapacityResultView,
      },
      { path: '/farm/:scenarioId/sectors/:unitId', name: 'sector', component: EmptyView },
      { path: '/:other(.*)', component: EmptyView },
    ],
  })
  await router.push(path)
  const wrapper = mount(RouterView, { global: { plugins: [router, createPinia()] } })
  await flushPromises()
  return { router, wrapper }
}

describe('Elegir qué calcular', () => {
  it('arranca con el escenario principal y la campaña actual, y pide el sector', async () => {
    const { wrapper } = await open('/calc')
    const [scenario, unitSelect, seasonSelect] = wrapper.findAll('select')

    expect(listSeasons).toHaveBeenCalledWith(7)
    expect((scenario!.element as HTMLSelectElement).value).toBe('7')
    expect((unitSelect!.element as HTMLSelectElement).value).toBe('')
    expect((seasonSelect!.element as HTMLSelectElement).value).toBe('12')
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })

  it('llega con todo elegido desde el sector y abre el resultado', async () => {
    const { router, wrapper } = await open('/calc?scenario=8&unit=3&season=11')

    expect(listSeasons).toHaveBeenCalledWith(8)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/calc/8/3/11')
  })

  it('al cambiar de escenario vuelve a pedir el sector', async () => {
    const { wrapper } = await open('/calc?scenario=7&unit=2&season=12')

    await wrapper.findAll('select')[0]!.setValue(8)
    await flushPromises()

    expect(listProductionUnits).toHaveBeenLastCalledWith(8)
    expect((wrapper.findAll('select')[1]!.element as HTMLSelectElement).value).toBe('')
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })

  it('simula en la pantalla del resultado y permite volver al cálculo de la campaña', async () => {
    vi.mocked(listAnimalCategories).mockResolvedValue([
      {
        id: 1,
        code: 'cow',
        name: 'Vaca',
        cow_equivalent: 1,
        summer_water_l_day: 60,
        winter_water_l_day: 40,
      },
    ])
    vi.mocked(listHerds).mockResolvedValue([
      {
        id: 35,
        season_id: 11,
        production_unit_id: 2,
        categories: [{ animal_category_id: 1, quantity: 20 }],
        range_condition: 'good',
        replacement_rate: 0.2,
        weaning_rate: 0.65432,
        early_weaning: false,
        supplemented: false,
        breeding_start: '2025-11-01',
        breeding_end: '2026-01-31',
      },
    ])
    const resultResponse = (capacity: number) =>
      new Response(
        JSON.stringify({
          area_ha: 100,
          carrying_capacity_ha_per_cow_equivalent: capacity,
          usable_area_ha: 60,
          pasture_limit_cow_equivalents: 4,
          water: { evaluated: false, limit_cow_equivalents: null, refill_l_day: null },
          max_herd: { cow_equivalents: 4, limited_by: 'pasture', categories: [] },
          recommended_herd: null,
          scaled_herd: null,
          warnings: [],
        }),
      )
    let resolveCalculation!: (response: Response) => void
    const calculation = new Promise<Response>((resolve) => {
      resolveCalculation = resolve
    })
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(calculation)
      .mockImplementation(() => resultResponse(12.9))
    vi.stubGlobal('fetch', fetchMock)
    const { router, wrapper } = await open('/calc?scenario=7&unit=2&season=11')
    expect(wrapper.find('.simulate-button').exists()).toBe(false)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/calc/7/2/11')
    expect(fetchMock.mock.calls[0]?.[0]).toMatch(/\/production-units\/2\/carrying-capacity$/)
    expect(wrapper.find('.simulate-button').exists()).toBe(false)
    resolveCalculation(resultResponse(15.1))
    await flushPromises()

    const simulateButton = wrapper.get('header .simulate-button')
    expect(simulateButton.text()).toBe('Simular otros valores')
    await simulateButton.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/calc/7/2/11')
    expect(wrapper.get('.simulation-notice').text()).toContain('Modo simulación')
    expect(wrapper.get('#simulation-title').text()).toBe('Valores simulados')
    expect(wrapper.get('button[type="submit"]').text()).toBe('Recalcular')
    expect(wrapper.findAll('form select')).toHaveLength(1)
    expect(listHerds).toHaveBeenCalledWith(11)
    expect(listHerds).toHaveBeenCalledTimes(1)
    expect(wrapper.get<HTMLInputElement>('#qty-simulation-1').element.value).toBe('20')
    expect(wrapper.get<HTMLInputElement>('#replacement-simulation').element.value).toBe('20')

    const [rainfall, bulls] = wrapper.findAll<HTMLInputElement>('.simulation-inputs input')
    expect(rainfall?.element.value).toBe('300')
    for (const invalidRainfall of ['', 0, -1]) {
      await rainfall!.setValue(invalidRainfall)
      await wrapper.get('form').trigger('submit')
      expect(wrapper.get('[role="alert"]').text()).toContain('lluvia mayor que cero')
    }
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await rainfall!.setValue(350.5)
    await bulls!.setValue(4)
    await wrapper.get('#replacement-simulation').setValue(25)
    await wrapper.get('#qty-simulation-1').setValue(24)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    const [url, init] = fetchMock.mock.calls[1]!
    expect(url).toMatch(/\/production-units\/2\/carrying-capacity$/)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({
      categories: [{ animal_category_id: 1, quantity: 24 }],
      range_condition: 'good',
      replacement_rate: 0.25,
      weaning_rate: 0.65432,
      early_weaning: false,
      supplemented: false,
      breeding_start: '2025-11-01',
      breeding_end: '2026-01-31',
      rainfall_mm: 350.5,
      bulls_per_100_cows: 4,
    })
    expect(wrapper.findAll('.kpis')).toHaveLength(1)
    expect(wrapper.get('.kpi .value').text()).toBe('12,9 ha/EV')
    expect(wrapper.get('.kpi .sub').text()).toContain('350.5 mm de lluvia')

    const restoreButton = wrapper.get('.simulation-notice button')
    expect(restoreButton.text()).toBe('Volver a mis datos')
    await restoreButton.trigger('click')

    expect(wrapper.find('.simulation-notice').exists()).toBe(false)
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.get('.kpi .value').text()).toBe('15,1 ha/EV')
    expect(wrapper.get('.kpi .sub').text()).toContain('300 mm de lluvia')
    expect(fetchMock).toHaveBeenCalledTimes(2)

    await wrapper.get('header .simulate-button').trigger('click')
    await flushPromises()
    expect(wrapper.get<HTMLInputElement>('#qty-simulation-1').element.value).toBe('20')
    expect(wrapper.get<HTMLInputElement>('.simulation-inputs input').element.value).toBe('300')
  })
})

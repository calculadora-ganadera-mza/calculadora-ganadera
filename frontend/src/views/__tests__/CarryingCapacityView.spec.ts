import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import CarryingCapacityView from '../CarryingCapacityView.vue'
import { listProductionUnits } from '@/api/productionUnits'
import { listScenarios, listSeasons } from '@/api/scenarios'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', () => ({ listProductionUnits: vi.fn() }))

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

async function open(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/calc', component: CarryingCapacityView },
      {
        path: '/calc/:scenarioId/:unitId/:seasonId',
        name: 'carrying-capacity-result',
        component: {},
      },
      { path: '/:other(.*)', component: {} },
    ],
  })
  await router.push(path)
  const wrapper = mount(RouterView, { global: { plugins: [router] } })
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
})

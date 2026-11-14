import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import ScenarioUnits from '@/components/ScenarioUnits.vue'
import SectorView from '../SectorView.vue'
import { listScenarios, listSeasons } from '@/api/scenarios'
import { deleteProductionUnit, listProductionUnits } from '@/api/productionUnits'
import { waterRequest } from '@/api/waterPoints'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', async (original) => ({
  ...(await original<typeof import('@/api/productionUnits')>()),
  listProductionUnits: vi.fn(),
  deleteProductionUnit: vi.fn(),
}))
vi.mock('@/api/waterPoints', () => ({
  waterRequest: vi.fn(),
  confirmSharing: vi.fn(),
}))

const first = {
  id: 1,
  name: 'Sector Norte',
  area_ha: 100,
  usable_area_ha: 60,
  polygon: { type: 'Polygon' as const, coordinates: [] },
}
const second = { ...first, id: 2, name: 'Sector Sur' }

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([{ id: 7, name: 'Mi establecimiento', is_main: true }])
  vi.mocked(listSeasons).mockResolvedValue([
    {
      id: 12,
      start_year: 2026,
      start_date: '2026-07-01',
      end_date: '2027-06-30',
      rainfall_mm: null,
      is_current: true,
    },
  ])
  vi.mocked(listProductionUnits).mockResolvedValue([first, second])
  vi.mocked(waterRequest).mockResolvedValue([])
})

async function open(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/farm', component: ScenarioUnits, props: { scenarioId: 7, overview: true } },
      { path: '/farm/:scenarioId/sectors/:unitId', name: 'sector', component: SectorView },
    ],
  })
  await router.push(path)
  const wrapper = mount(RouterView, {
    global: { plugins: [router], stubs: { UnitsMap: true, WaterPoints: true, HerdForm: true } },
  })
  await flushPromises()
  return { router, wrapper }
}

describe('Navegación de sectores', () => {
  it('muestra solo nombres enlazados y abre la administración del sector elegido', async () => {
    const { wrapper, router } = await open('/farm')
    const links = wrapper.findAll('.sector-links a')
    expect(links).toHaveLength(2)
    expect(links[1]!.text()).toBe('Sector Sur›')
    expect(wrapper.findComponent({ name: 'WaterPoints' }).exists()).toBe(false)
    expect(wrapper.findComponent({ name: 'HerdForm' }).exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Editar contorno')
    await links[1]!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/farm/7/sectors/2')
    expect(wrapper.find('h1').text()).toBe('Sector Sur')
    const map = wrapper.findComponent({ name: 'UnitsMap' })
    expect(map.props('units')).toEqual([second])
    expect(map.props('referenceUnits')).toEqual([first])
    expect(wrapper.findAll('.unit-list > li')).toHaveLength(1)
    expect(wrapper.findComponent({ name: 'WaterPoints' }).props('unitId')).toBe(2)
    expect(wrapper.findComponent({ name: 'HerdForm' }).props()).toEqual({ seasonId: 12, unitId: 2 })
  })

  it('muestra como referencia solo las aguadas vecinas compartidas con el sector abierto', async () => {
    const point = {
      id: 10,
      production_unit_id: 1,
      name: 'Aguada del Norte',
      shared: true,
      neighbor_unit_ids: [2],
      location: { type: 'Point', coordinates: [-68, -34] },
      refill_l_day: null,
    }
    const own = { ...point, id: 11, production_unit_id: 2, name: 'Propia' }
    vi.mocked(waterRequest).mockResolvedValue([
      point,
      own,
      { ...point, id: 12, shared: false },
      { ...point, id: 13, neighbor_unit_ids: [] },
    ])
    const { wrapper } = await open('/farm/7/sectors/2')
    const map = wrapper.findComponent({ name: 'UnitsMap' })
    expect(map.props('sharedWaterPoints')).toEqual([point])
    expect(map.props('waterPoints')).toEqual([own])
    expect(wrapper.findComponent({ name: 'WaterPoints' }).props('savedPoints')).toEqual([own])
  })

  it('admite URL directa y recarga al navegar a otro sector', async () => {
    const { wrapper, router } = await open('/farm/7/sectors/2')
    expect(wrapper.find('h1').text()).toBe('Sector Sur')
    await router.push('/farm/7/sectors/1')
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe('Sector Norte')
    expect(wrapper.findComponent({ name: 'WaterPoints' }).props('unitId')).toBe(1)
  })

  it('informa que un sector no pertenece al escenario sin mostrar administración', async () => {
    const { wrapper } = await open('/farm/7/sectors/99')
    expect(wrapper.text()).toContain('No se encontró este sector')
    expect(wrapper.findComponent({ name: 'WaterPoints' }).exists()).toBe(false)
  })

  it('permite reintentar si falla la carga del establecimiento', async () => {
    vi.mocked(listScenarios).mockRejectedValueOnce(new Error('Sin red'))
    const { wrapper } = await open('/farm/7/sectors/2')
    expect(wrapper.find('[role="alert"]').text()).toContain('No se pudo cargar el sector')
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe('Sector Sur')
  })

  it('vuelve al campo después de eliminar el sector administrado', async () => {
    const { wrapper, router } = await open('/farm/7/sectors/2')
    vi.spyOn(window, 'confirm').mockReturnValueOnce(true)
    vi.mocked(deleteProductionUnit).mockResolvedValue()
    vi.mocked(listProductionUnits).mockResolvedValue([first])
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Eliminar')!
      .trigger('click')
    await flushPromises()
    expect(deleteProductionUnit).toHaveBeenCalledWith(2)
    expect(router.currentRoute.value.path).toBe('/farm')
  })
})

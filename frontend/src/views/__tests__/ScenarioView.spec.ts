import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { listScenarios, listSeasons } from '@/api/scenarios'
import { listProductionUnits } from '@/api/productionUnits'
import { listScenarioWaterPoints } from '@/api/waterPoints'
import { createSeason } from '@/api/seasons'
import { NORTH, SCENARIO, SOUTH, WELL, openAt, season } from './farmFixtures'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', async (original) => ({
  ...(await original<typeof import('@/api/productionUnits')>()),
  listProductionUnits: vi.fn(),
}))
vi.mock('@/api/waterPoints', () => ({ listScenarioWaterPoints: vi.fn() }))
vi.mock('@/api/seasons', () => ({ createSeason: vi.fn(), updateSeasonRainfall: vi.fn() }))

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([SCENARIO])
  vi.mocked(listProductionUnits).mockResolvedValue([NORTH, SOUTH])
  vi.mocked(listSeasons).mockResolvedValue([season(11, 2025), season(12, 2026, true)])
  vi.mocked(listScenarioWaterPoints).mockResolvedValue([WELL, { ...WELL, id: 11 }])
})

describe('Pantalla del escenario', () => {
  it('muestra el resumen, la campaña actual, las otras y la tabla de sectores', async () => {
    const { wrapper } = await openAt('/farm/7')

    expect(wrapper.get('h1').text()).toBe('La Aguada')
    expect(wrapper.get('.summary').text()).toBe('Sectores 2 · Superficie 150 ha')
    expect(wrapper.get('.campaign h2').text()).toBe('Campaña 2026/27 actual')
    expect(wrapper.find('#rainfall-12').exists()).toBe(true)
    expect(wrapper.get('.past-seasons').text()).toContain('Campaña 2025/26')
    const rows = wrapper.findAll('tbody tr').map((row) => row.findAll('td').map((c) => c.text()))
    expect(rows).toEqual([
      ['Potrero Norte', '100 ha', '60 ha', '2'],
      ['Potrero Sur', '50 ha', '50 ha', '0'],
    ])
    expect(wrapper.get('tbody a').attributes('href')).toBe('/farm/7/sectors/1')
    const map = wrapper.getComponent({ name: 'UnitsMap' })
    expect(map.props('units')).toEqual([NORTH, SOUTH])
    expect(map.props('readOnly')).toBe(true)
  })

  it('abre el sector tocado en el mapa', async () => {
    const { wrapper, router } = await openAt('/farm/7')
    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('selectUnit', 2)
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/farm/7/sectors/2')
  })

  it('crea una campaña desde la ventana y vuelve a cargar las campañas', async () => {
    vi.mocked(createSeason).mockResolvedValue(season(13, 2027))
    const { wrapper } = await openAt('/farm/7')

    const open = wrapper.findAll('button').find((b) => b.text() === 'Nueva campaña')!
    await open.trigger('click')
    const dialog = wrapper.get('[role="dialog"]')
    expect(dialog.text()).not.toContain('Lluvia')
    vi.mocked(listSeasons).mockResolvedValue([
      season(11, 2025),
      season(12, 2026, true),
      season(13, 2027),
    ])
    await dialog.get('.add-season button').trigger('click')
    await flushPromises()

    expect(createSeason).toHaveBeenCalledWith(7, 2027)
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(wrapper.get('.past-seasons').text()).toContain('Campaña 2027/28')
  })

  it('lleva a dibujar un sector', async () => {
    const { wrapper } = await openAt('/farm/7')
    const link = wrapper.findAll('a').find((a) => a.text() === 'Dibujar sector')!
    expect(link.attributes('href')).toBe('/farm/7/sectors/new')
  })

  it('avisa si el escenario no existe', async () => {
    const { wrapper } = await openAt('/farm/99')
    expect(wrapper.get('[role="alert"]').text()).toContain('No se encontró el escenario.')
    expect(wrapper.text()).not.toContain('Reintentar')
    expect(listProductionUnits).not.toHaveBeenCalled()
  })

  it('si falla la carga, deja reintentar', async () => {
    vi.mocked(listScenarios).mockRejectedValueOnce(new Error('Sin red'))
    const { wrapper } = await openAt('/farm/7')
    expect(wrapper.get('[role="alert"]').text()).toContain('No se pudo cargar el escenario')

    await wrapper.get('[role="alert"] button').trigger('click')
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('La Aguada')
  })
})

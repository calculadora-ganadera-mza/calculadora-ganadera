import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { listScenarios, listSeasons } from '@/api/scenarios'
import { listProductionUnits } from '@/api/productionUnits'
import { getUnitHistory, type HistoryEntry } from '@/api/history'
import { createSeason } from '@/api/seasons'
import { NORTH, SCENARIO, SOUTH, openAt, season } from './farmFixtures'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', () => ({ listProductionUnits: vi.fn() }))
vi.mock('@/api/history', () => ({ getUnitHistory: vi.fn() }))
vi.mock('@/api/seasons', () => ({ createSeason: vi.fn() }))

const entry = (seasonId: number, startYear: number, changes: Partial<HistoryEntry> = {}) => ({
  season_id: seasonId,
  start_year: startYear,
  categories: [],
  replacement_rate: null,
  weaning_rate: null,
  rainfall_mm: null,
  ...changes,
})

const HISTORY: HistoryEntry[] = [
  entry(11, 2025, { rainfall_mm: 260 }),
  entry(12, 2026, {
    categories: [
      { animal_category_id: 1, name: 'Vaca', quantity: 80 },
      { animal_category_id: 2, name: 'Toro', quantity: 3 },
    ],
    replacement_rate: 0.2,
    weaning_rate: 0.65,
    rainfall_mm: 300,
  }),
]

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([
    { id: 3, name: 'Otro campo', is_main: false },
    SCENARIO,
  ])
  vi.mocked(listProductionUnits).mockResolvedValue([NORTH, SOUTH])
  vi.mocked(listSeasons).mockResolvedValue([season(11, 2025), season(12, 2026, true)])
  vi.mocked(getUnitHistory).mockResolvedValue(HISTORY)
})

function rows(wrapper: Awaited<ReturnType<typeof openAt>>['wrapper']) {
  return wrapper.findAll('tbody tr').map((row) => row.findAll('td').map((cell) => cell.text()))
}

describe('Seguimiento', () => {
  it('muestra la evolución del primer sector del escenario principal', async () => {
    const { wrapper } = await openAt('/tracking')

    expect(listProductionUnits).toHaveBeenCalledWith(7)
    expect(wrapper.get('.summary').text()).toBe('La Aguada Principal')
    expect(getUnitHistory).toHaveBeenCalledWith(1)
    expect(wrapper.getComponent({ name: 'HistoryCharts' }).props()).toEqual({
      entries: HISTORY,
      labels: ['2025/26', '2026/27'],
    })
    expect(wrapper.findAll('thead th').map((th) => th.text())).toEqual([
      'Campaña',
      'Vaca',
      'Toro',
      'Destete',
      'Reposición',
      'Lluvia de la campaña anterior',
    ])
    expect(rows(wrapper)).toEqual([
      ['2025/26', '—', '—', '—', '—', '260 mm'],
      ['2026/27', '80', '3', '65 %', '20 %', '300 mm'],
    ])
    expect(wrapper.get('tbody a').attributes('href')).toBe('/farm/7/sectors/1?season=11')
  })

  it('al elegir otro sector lo deja en la dirección y carga su evolución', async () => {
    const { wrapper, router } = await openAt('/tracking')

    await wrapper.get('#unit-select').setValue('2')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/tracking?unit=2')
    expect(getUnitHistory).toHaveBeenLastCalledWith(2)
  })

  it('arranca en el sector de la dirección', async () => {
    await openAt('/tracking?unit=2')

    expect(getUnitHistory).toHaveBeenCalledWith(2)
  })

  it('carga una campaña anterior, la suma al historial y ofrece cargarle los datos', async () => {
    vi.mocked(createSeason).mockResolvedValue(season(10, 2024))
    const { wrapper } = await openAt('/tracking')
    vi.mocked(listSeasons).mockResolvedValue([
      season(10, 2024),
      season(11, 2025),
      season(12, 2026, true),
    ])
    vi.mocked(getUnitHistory).mockResolvedValue([entry(10, 2024), ...HISTORY])

    const add = wrapper.findAll('button').find((b) => b.text() === 'Agregar campaña 2024/25')!
    await add.trigger('click')
    await flushPromises()

    expect(createSeason).toHaveBeenCalledWith(7, 2024)
    expect(rows(wrapper).map((row) => row[0])).toEqual(['2024/25', '2025/26', '2026/27'])
    const status = wrapper.get('[role="status"]')
    expect(status.text()).toContain('Se agregó la campaña 2024/25.')
    expect(status.findAll('a').map((a) => a.attributes('href'))).toEqual([
      '/farm/7/sectors/1?season=10',
      '/farm/7?season=10',
    ])
  })

  it('sin escenario manda a crearlo en Mi campo', async () => {
    vi.mocked(listScenarios).mockResolvedValue([])
    const { wrapper } = await openAt('/tracking')

    expect(wrapper.text()).toContain('Todavía no hay un escenario.')
    expect(wrapper.get('main a, section a').attributes('href')).toBe('/farm')
    expect(listProductionUnits).not.toHaveBeenCalled()
  })

  it('sin sectores manda a dibujar uno en Mi campo', async () => {
    vi.mocked(listProductionUnits).mockResolvedValue([])
    const { wrapper } = await openAt('/tracking')

    expect(wrapper.text()).toContain('El escenario todavía no tiene sectores.')
    expect(getUnitHistory).not.toHaveBeenCalled()
  })

  it('si falla la evolución deja reintentar', async () => {
    vi.mocked(getUnitHistory).mockRejectedValueOnce(new Error('caído'))
    const { wrapper } = await openAt('/tracking')

    expect(wrapper.get('[role="alert"]').text()).toContain('No se pudo cargar la evolución')
    await wrapper.get('[role="alert"] button').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
  })
})

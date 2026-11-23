import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createScenario, fetchFirstSeasonYears, listScenarios, listSeasons } from '@/api/scenarios'
import { listProductionUnits } from '@/api/productionUnits'
import { listScenarioWaterPoints } from '@/api/waterPoints'
import { NORTH, SCENARIO, SOUTH, openAt, season } from './farmFixtures'

vi.mock('@/api/scenarios', () => ({
  fetchFirstSeasonYears: vi.fn(),
  createScenario: vi.fn(),
  listScenarios: vi.fn(),
  listSeasons: vi.fn(),
}))
vi.mock('@/api/productionUnits', async (original) => ({
  ...(await original<typeof import('@/api/productionUnits')>()),
  listProductionUnits: vi.fn(),
}))
vi.mock('@/api/waterPoints', () => ({ listScenarioWaterPoints: vi.fn() }))

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([SCENARIO])
  vi.mocked(listProductionUnits).mockResolvedValue([NORTH, SOUTH])
  vi.mocked(listSeasons).mockResolvedValue([season(1, 2026, true), season(2, 2027)])
  vi.mocked(listScenarioWaterPoints).mockResolvedValue([])
  vi.mocked(fetchFirstSeasonYears).mockResolvedValue([
    { start_year: 2026, start_date: '2026-07-01', end_date: '2027-06-30' },
  ])
})

describe('Mi campo', () => {
  it('muestra cada escenario con sus sectores, su superficie y la última campaña', async () => {
    const { wrapper } = await openAt('/farm')

    const cells = wrapper.findAll('tbody td').map((cell) => cell.text())
    expect(cells).toEqual(['La Aguada', '2', '150 ha', '2027/28'])
    expect(wrapper.find('tbody a').attributes('href')).toBe('/farm/7')
    expect(wrapper.text()).not.toContain('Nuevo escenario')
  })

  it('sin escenarios crea uno desde la ventana y abre su pantalla', async () => {
    vi.mocked(listScenarios).mockResolvedValueOnce([])
    vi.mocked(createScenario).mockResolvedValue(SCENARIO)
    const { wrapper, router } = await openAt('/farm')
    expect(wrapper.find('table').exists()).toBe(false)

    await wrapper.get('.empty button').trigger('click')
    await flushPromises()
    const dialog = wrapper.get('[role="dialog"]')
    expect(dialog.text()).toContain('Nuevo escenario')
    expect(dialog.text()).not.toContain('Lluvia')
    await dialog.get('#scenario-name').setValue('La Aguada')
    await dialog.get('form').trigger('submit')
    await flushPromises()

    expect(createScenario).toHaveBeenCalledWith({
      name: 'La Aguada',
      first_season_start_year: 2026,
    })
    expect(router.currentRoute.value.path).toBe('/farm/7')
  })

  it('Cancelar cierra la ventana sin crear el escenario', async () => {
    vi.mocked(listScenarios).mockResolvedValueOnce([])
    const { wrapper } = await openAt('/farm')

    await wrapper.get('.empty button').trigger('click')
    await flushPromises()
    const buttons = wrapper.get('[role="dialog"]').findAll('form button')
    expect(buttons.map((b) => b.text())).toEqual(['Crear escenario', 'Cancelar'])
    await buttons[1]!.trigger('click')

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(createScenario).not.toHaveBeenCalled()
  })

  it('avisa si no pudo cargar y deja reintentar', async () => {
    vi.mocked(listScenarios).mockRejectedValueOnce(new Error('Error 500'))
    const { wrapper } = await openAt('/farm')
    expect(wrapper.text()).toContain('No se pudieron cargar tus escenarios.')

    await wrapper.get('[role="alert"] button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('La Aguada')
  })
})

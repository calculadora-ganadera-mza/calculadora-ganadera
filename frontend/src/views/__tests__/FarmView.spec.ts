import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import {
  createScenario,
  fetchFirstSeasonYears,
  listScenarios,
  listSeasons,
  updateScenario,
} from '@/api/scenarios'
import { listProductionUnits } from '@/api/productionUnits'
import { listScenarioWaterPoints } from '@/api/waterPoints'
import { NORTH, SCENARIO, SOUTH, openAt, season } from './farmFixtures'

vi.mock('@/api/scenarios', () => ({
  fetchFirstSeasonYears: vi.fn(),
  createScenario: vi.fn(),
  listScenarios: vi.fn(),
  listSeasons: vi.fn(),
  updateScenario: vi.fn(),
}))
vi.mock('@/api/productionUnits', async (original) => ({
  ...(await original<typeof import('@/api/productionUnits')>()),
  listProductionUnits: vi.fn(),
}))
vi.mock('@/api/waterPoints', () => ({ listScenarioWaterPoints: vi.fn() }))

const SECOND_SCENARIO = { id: 8, name: 'El Puesto', is_main: false }

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([SCENARIO, SECOND_SCENARIO])
  vi.mocked(listProductionUnits).mockResolvedValue([NORTH, SOUTH])
  vi.mocked(listSeasons).mockResolvedValue([season(1, 2026, true), season(2, 2027)])
  vi.mocked(listScenarioWaterPoints).mockResolvedValue([])
  vi.mocked(fetchFirstSeasonYears).mockResolvedValue([
    { start_year: 2026, start_date: '2026-07-01', end_date: '2027-06-30' },
  ])
})

describe('Mi campo', () => {
  it('al entrar a /farm abre directamente el escenario principal', async () => {
    vi.mocked(listScenarios).mockResolvedValue([
      { ...SCENARIO, is_main: false },
      { ...SECOND_SCENARIO, is_main: true },
    ])
    const { router, wrapper } = await openAt('/farm')

    expect(router.currentRoute.value.path).toBe('/farm/8')
    expect(wrapper.get('h1').text()).toBe('El Puesto')
  })

  it('en /farm/scenarios muestra cada escenario, cuál es principal y permite crear otro', async () => {
    vi.mocked(listProductionUnits).mockImplementation(async (id) =>
      id === SCENARIO.id ? [NORTH, SOUTH] : [NORTH],
    )
    const { wrapper } = await openAt('/farm/scenarios')

    const rows = wrapper
      .findAll('tbody tr')
      .map((row) => row.findAll('td').map((cell) => cell.text()))
    expect(rows).toEqual([
      ['La AguadaPrincipal', '2', '150 ha', '2027/28', ''],
      ['El Puesto', '1', '100 ha', '2027/28', 'Marcar como principal'],
    ])
    expect(wrapper.findAll('tbody a').map((a) => a.attributes('href'))).toEqual([
      '/farm/7',
      '/farm/8',
    ])
    expect(wrapper.text()).toContain('Nuevo escenario')
  })

  it('crea un escenario adicional desde la lista y abre su pantalla', async () => {
    const created = { id: 9, name: 'San José', is_main: false }
    vi.mocked(createScenario).mockResolvedValue(created)
    const { wrapper, router } = await openAt('/farm/scenarios')

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Nuevo escenario')!
      .trigger('click')
    await flushPromises()
    const dialog = wrapper.get('[role="dialog"]')
    await dialog.get('#scenario-name').setValue('San José')
    await dialog.get('form').trigger('submit')
    await flushPromises()

    expect(createScenario).toHaveBeenCalledWith({
      name: 'San José',
      first_season_start_year: 2026,
    })
    expect(router.currentRoute.value.path).toBe('/farm/9')
  })

  it('marca otro escenario como principal desde la lista', async () => {
    vi.mocked(updateScenario).mockResolvedValue({ ...SECOND_SCENARIO, is_main: true })
    const { wrapper } = await openAt('/farm/scenarios')

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Marcar como principal')!
      .trigger('click')
    await flushPromises()

    expect(updateScenario).toHaveBeenCalledWith(8, { is_main: true })
    const rows = wrapper
      .findAll('tbody tr')
      .map((row) => row.findAll('td').map((cell) => cell.text()))
    expect(rows[0]![0]).toBe('La Aguada')
    expect(rows[0]![4]).toBe('Marcar como principal')
    expect(rows[1]![0]).toBe('El PuestoPrincipal')
    expect(rows[1]![4]).toBe('')
  })

  it('avisa si no pudo marcar como principal', async () => {
    vi.mocked(updateScenario).mockRejectedValueOnce(new Error('Error 500'))
    const { wrapper } = await openAt('/farm/scenarios')

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Marcar como principal')!
      .trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(
      'No se pudo marcar el escenario como principal.',
    )
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
    const { wrapper } = await openAt('/farm/scenarios')
    expect(wrapper.text()).toContain('No se pudieron cargar los escenarios.')

    await wrapper.get('[role="alert"] button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('La Aguada')
  })
})

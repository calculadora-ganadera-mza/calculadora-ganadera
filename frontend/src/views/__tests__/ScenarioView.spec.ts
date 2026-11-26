import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, type VueWrapper } from '@vue/test-utils'
import { listScenarios, listSeasons, updateScenario } from '@/api/scenarios'
import { listProductionUnits } from '@/api/productionUnits'
import { listScenarioWaterPoints } from '@/api/waterPoints'
import { createSeason, updateSeasonRainfall } from '@/api/seasons'
import { listAnimalCategories, listHerds } from '@/api/herds'
import { NORTH, SCENARIO, SOUTH, WELL, openAt, season } from './farmFixtures'

vi.mock('@/api/scenarios', () => ({
  listScenarios: vi.fn(),
  listSeasons: vi.fn(),
  updateScenario: vi.fn(),
}))
vi.mock('@/api/productionUnits', async (original) => ({
  ...(await original<typeof import('@/api/productionUnits')>()),
  listProductionUnits: vi.fn(),
}))
vi.mock('@/api/waterPoints', () => ({ listScenarioWaterPoints: vi.fn() }))
vi.mock('@/api/seasons', () => ({ createSeason: vi.fn(), updateSeasonRainfall: vi.fn() }))
// La calculadora se abre al volver: sin rodeos ni categorías
vi.mock('@/api/herds', () => ({ listAnimalCategories: vi.fn(), listHerds: vi.fn() }))

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([SCENARIO])
  vi.mocked(listProductionUnits).mockResolvedValue([NORTH, SOUTH])
  vi.mocked(listSeasons).mockResolvedValue([season(11, 2025), season(12, 2026, true)])
  vi.mocked(listScenarioWaterPoints).mockResolvedValue([WELL, { ...WELL, id: 11 }])
  vi.mocked(listAnimalCategories).mockResolvedValue([])
  vi.mocked(listHerds).mockResolvedValue([])
})

// Elige una campaña en el selector y espera a que cambie la dirección
async function choose(wrapper: VueWrapper, seasonId: number) {
  await wrapper.get('#season-select').setValue(String(seasonId))
  await flushPromises()
}

describe('Pantalla del escenario', () => {
  it('muestra el resumen, la campaña actual y la tabla de sectores', async () => {
    const { wrapper } = await openAt('/farm/7')

    expect(wrapper.get('h1').text()).toBe('La Aguada')
    expect(wrapper.get('.summary').text()).toBe('Sectores 2 · Superficie 150 ha')
    expect(wrapper.get('.campaign h2').text()).toBe('Campaña 2026/27 actual')
    expect(wrapper.find('#rainfall-12').exists()).toBe(true)
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

  it('lista las campañas de la más nueva a la más vieja y arranca en la actual', async () => {
    const { wrapper } = await openAt('/farm/7')

    const select = wrapper.get<HTMLSelectElement>('#season-select')
    expect(select.findAll('option').map((option) => option.text())).toEqual([
      '2026/27 (actual)',
      '2025/26',
    ])
    expect(select.element.value).toBe('12')
  })

  it('al elegir otra campaña la muestra y la pasa a los sectores', async () => {
    const { wrapper, router } = await openAt('/farm/7')
    await choose(wrapper, 11)

    expect(router.currentRoute.value.fullPath).toBe('/farm/7?season=11')
    expect(wrapper.get('.campaign h2').text()).toBe('Campaña 2025/26')
    expect(wrapper.find('#rainfall-11').exists()).toBe(true)
    expect(wrapper.get('tbody a').attributes('href')).toBe('/farm/7/sectors/1?season=11')
    const draw = wrapper.findAll('a').find((a) => a.text() === 'Dibujar sector')!
    expect(draw.attributes('href')).toBe('/farm/7/sectors/new?season=11')
  })

  it('toma la campaña de la dirección y, si no es del escenario, usa la actual', async () => {
    const chosen = await openAt('/farm/7?season=11')
    expect(chosen.wrapper.get('.campaign h2').text()).toBe('Campaña 2025/26')
    expect(chosen.wrapper.get<HTMLSelectElement>('#season-select').element.value).toBe('11')

    const unknown = await openAt('/farm/7?season=99')
    expect(unknown.wrapper.get('.campaign h2').text()).toBe('Campaña 2026/27 actual')
  })

  it('abre el sector tocado en el mapa con la campaña elegida', async () => {
    const { wrapper, router } = await openAt('/farm/7?season=11')
    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('selectUnit', 2)
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/farm/7/sectors/2?season=11')
  })

  it('crea una campaña desde la ventana y la deja elegida', async () => {
    vi.mocked(createSeason).mockResolvedValue(season(13, 2027))
    const { wrapper, router } = await openAt('/farm/7')

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
    expect(router.currentRoute.value.query.season).toBe('13')
    expect(wrapper.get('.campaign h2').text()).toBe('Campaña 2027/28')
  })

  it('al volver a una campaña muestra la lluvia que se guardó en ella', async () => {
    vi.mocked(updateSeasonRainfall).mockResolvedValue({ ...season(11, 2025), rainfall_mm: 250 })
    const { wrapper } = await openAt('/farm/7?season=11')

    await wrapper.get('#rainfall-11').setValue(250)
    await wrapper.get('.campaign form').trigger('submit')
    await flushPromises()
    await choose(wrapper, 12)
    await choose(wrapper, 11)

    expect(updateSeasonRainfall).toHaveBeenCalledWith(11, 250)
    expect(wrapper.get<HTMLInputElement>('#rainfall-11').element.value).toBe('250')
  })

  it('desde la calculadora avisa el sector y al guardar vuelve con los mismos ids', async () => {
    vi.mocked(updateSeasonRainfall).mockResolvedValue({ ...season(11, 2025), rainfall_mm: 250 })
    const { router, wrapper } = await openAt('/farm/7?season=11&calculate=2')

    expect(wrapper.get('.campaign .notice').text()).toContain('receptividad de Potrero Sur')
    expect(wrapper.get('.campaign a').attributes('href')).toBe(
      '/calculators/carrying-capacity?scenario=7&unit=2&season=11',
    )
    await wrapper.get('#rainfall-11').setValue(250)
    await wrapper.get('.campaign form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe(
      '/calculators/carrying-capacity?scenario=7&unit=2&season=11&rainfall=saved',
    )
  })

  it('no muestra el aviso si el sector no es de este escenario', async () => {
    const { wrapper } = await openAt('/farm/7?season=11&calculate=99')

    expect(wrapper.find('.campaign .notice').exists()).toBe(false)
    expect(wrapper.get('.campaign button[type="submit"]').text()).toBe('Guardar')
  })

  it('Cancelar cierra la ventana sin crear la campaña', async () => {
    const { wrapper } = await openAt('/farm/7')

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Nueva campaña')!
      .trigger('click')
    const buttons = wrapper.get('[role="dialog"] .add-season').findAll('button')
    expect(buttons.map((b) => b.text())).toEqual(['Agregar campaña 2027/28', 'Cancelar'])
    await buttons[1]!.trigger('click')

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(createSeason).not.toHaveBeenCalled()
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

  it('muestra si es principal', async () => {
    const { wrapper } = await openAt('/farm/7')

    expect(wrapper.get('.title').text()).toContain('Principal')
  })

  it('permite marcar como principal un escenario que no lo es', async () => {
    const secondary = { id: 8, name: 'El Puesto', is_main: false }
    vi.mocked(listScenarios).mockResolvedValue([SCENARIO, secondary])
    vi.mocked(updateScenario).mockResolvedValue({ ...secondary, is_main: true })
    const { wrapper } = await openAt('/farm/8')

    const markButton = wrapper.findAll('button').find((b) => b.text() === 'Marcar como principal')!
    await markButton.trigger('click')
    await flushPromises()

    expect(updateScenario).toHaveBeenCalledWith(8, { is_main: true })
    expect(wrapper.get('.title').text()).toContain('Principal')
    expect(wrapper.text()).not.toContain('Marcar como principal')
  })

  it('avisa si no pudo marcar el escenario como principal', async () => {
    const secondary = { id: 8, name: 'El Puesto', is_main: false }
    vi.mocked(listScenarios).mockResolvedValue([SCENARIO, secondary])
    vi.mocked(updateScenario).mockRejectedValueOnce(new Error('Sin red'))
    const { wrapper } = await openAt('/farm/8')

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Marcar como principal')!
      .trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(
      'No se pudo marcar el escenario como principal.',
    )
  })

  it('permite cambiar el nombre del escenario desde la ventana y valida que no quede vacío', async () => {
    vi.mocked(updateScenario).mockResolvedValue({ ...SCENARIO, name: 'San José' })
    const { wrapper } = await openAt('/farm/7')

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Editar')!
      .trigger('click')
    const dialog = wrapper.get('[role="dialog"]')
    expect(dialog.get<HTMLInputElement>('#scenario-new-name').element.value).toBe('La Aguada')

    await dialog.get('#scenario-new-name').setValue('   ')
    await dialog.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('[role="dialog"] [role="alert"]').text()).toBe(
      'Falta el nombre del escenario.',
    )
    expect(updateScenario).not.toHaveBeenCalled()

    await dialog.get('#scenario-new-name').setValue('  San José  ')
    await dialog.get('form').trigger('submit')
    await flushPromises()

    expect(updateScenario).toHaveBeenCalledWith(7, { name: 'San José' })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(wrapper.get('h1').text()).toBe('San José')
  })

  it('avisa si no pudo cambiar el nombre del escenario', async () => {
    vi.mocked(updateScenario).mockRejectedValueOnce(new Error('Error 500'))
    const { wrapper } = await openAt('/farm/7')

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Editar')!
      .trigger('click')
    await wrapper.get('#scenario-new-name').setValue('San José')
    await wrapper.get('[role="dialog"] form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="dialog"] [role="alert"]').text()).toBe(
      'No se pudo cambiar el nombre.',
    )
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

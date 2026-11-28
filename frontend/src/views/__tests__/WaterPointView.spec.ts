import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { listScenarios, listSeasons } from '@/api/scenarios'
import { listProductionUnits } from '@/api/productionUnits'
import { confirmSharing, listScenarioWaterPoints, waterRequest } from '@/api/waterPoints'
import { NORTH, SCENARIO, SOUTH, WELL, openAt, season } from './farmFixtures'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', async (original) => ({
  ...(await original<typeof import('@/api/productionUnits')>()),
  listProductionUnits: vi.fn(),
}))
vi.mock('@/api/waterPoints', () => ({
  listScenarioWaterPoints: vi.fn(),
  waterRequest: vi.fn(),
  confirmSharing: vi.fn(),
}))

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([SCENARIO])
  vi.mocked(listProductionUnits).mockResolvedValue([NORTH, SOUTH])
  vi.mocked(listSeasons).mockResolvedValue([season(12, 2026, true)])
  vi.mocked(listScenarioWaterPoints).mockResolvedValue([WELL])
})

describe('Ubicar aguada', () => {
  it('pide marcar el punto antes de guardar', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/1/water-points/new')

    expect(wrapper.get('h1').text()).toBe('Nueva aguada')
    expect(wrapper.get<HTMLInputElement>('#water-name').element.value).toBe('Aguada 2')
    expect(wrapper.text()).toContain('Lo que repone, no lo que almacena.')
    expect(wrapper.getComponent({ name: 'UnitsMap' }).props('waterMode')).toBe(true)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe(
      'Falta marcar la ubicación de la aguada en el sector.',
    )
    expect(waterRequest).not.toHaveBeenCalled()
  })

  it('guarda la aguada, pregunta si se comparte y vuelve al sector', async () => {
    const created = { ...WELL, id: 30, name: 'Aguada 2', refill_l_day: 3000 }
    vi.mocked(waterRequest).mockResolvedValue(created)
    vi.mocked(confirmSharing).mockResolvedValue(created)
    const { wrapper, router } = await openAt('/farm/7/sectors/1/water-points/new')

    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('locate', [-68.1, -34.1])
    await wrapper.get('#water-refill').setValue('3000')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(waterRequest).toHaveBeenCalledWith('/production-units/1/water-points', 'POST', {
      shared: false,
      name: 'Aguada 2',
      location: { type: 'Point', coordinates: [-68.1, -34.1] },
      refill_l_day: 3000,
    })
    expect(confirmSharing).toHaveBeenCalledWith(created)
    expect(router.currentRoute.value.path).toBe('/farm/7/sectors/1')
  })

  it('si falla la pregunta de compartir, avisa que se guardó y ofrece volver', async () => {
    vi.mocked(waterRequest).mockResolvedValue({ ...WELL, id: 30 })
    vi.mocked(confirmSharing).mockRejectedValue(new Error('Sin red'))
    const { wrapper, router } = await openAt('/farm/7/sectors/1/water-points/new')

    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('locate', [-68.1, -34.1])
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('La aguada se guardó')
    expect(router.currentRoute.value.path).toBe('/farm/7/sectors/1/water-points/new')
    expect(wrapper.findAll('a').some((a) => a.text() === 'Volver al sector')).toBe(true)
    expect(wrapper.text()).not.toContain('Guardar aguada')
  })

  it('no acepta litros en cero', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/1/water-points/new')

    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('locate', [-68.1, -34.1])
    await wrapper.get('#water-refill').setValue('0')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('Los litros deben ser mayores que cero.')
    expect(waterRequest).not.toHaveBeenCalled()
  })

  it('si el servidor rechaza el punto, avisa y pide marcarlo de nuevo', async () => {
    vi.mocked(waterRequest).mockRejectedValue(
      new Error('La aguada tiene que estar dentro del sector.'),
    )
    const { wrapper, router } = await openAt('/farm/7/sectors/1/water-points/new')
    const map = wrapper.getComponent({ name: 'UnitsMap' })

    map.vm.$emit('locate', [-70, -30])
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe(
      'La aguada tiene que estar dentro del sector.',
    )
    expect(map.props('waterPosition')).toBeNull()
    expect(router.currentRoute.value.path).toBe('/farm/7/sectors/1/water-points/new')
  })
})

describe('Editar aguada', () => {
  it('carga los datos y guarda la casilla de compartida sin volver a preguntar', async () => {
    vi.mocked(waterRequest).mockResolvedValue({ ...WELL, shared: true })
    const { wrapper, router } = await openAt('/farm/7/sectors/1/water-points/10')

    expect(wrapper.get('h1').text()).toBe('Editar aguada')
    expect(wrapper.get<HTMLInputElement>('#water-name').element.value).toBe('Aguada 1')
    expect(wrapper.getComponent({ name: 'UnitsMap' }).props('editingWaterId')).toBe(10)
    await wrapper.get('input[type="checkbox"]').setValue(true)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(waterRequest).toHaveBeenCalledWith('/water-points/10', 'PUT', {
      shared: true,
      name: 'Aguada 1',
      location: WELL.location,
      refill_l_day: 4200,
    })
    expect(confirmSharing).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/farm/7/sectors/1')
  })

  it('mantiene la campaña elegida en las migas, en Cancelar y al volver al sector', async () => {
    vi.mocked(waterRequest).mockResolvedValue(WELL)
    const { wrapper, router } = await openAt('/farm/7/sectors/1/water-points/10?season=11')

    const links = wrapper.findAll('.breadcrumb a').map((a) => a.attributes('href'))
    expect(links).toEqual(['/farm/scenarios', '/farm/7?season=11', '/farm/7/sectors/1?season=11'])
    const cancel = wrapper.findAll('a').find((a) => a.text() === 'Cancelar')!
    expect(cancel.attributes('href')).toBe('/farm/7/sectors/1?season=11')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/farm/7/sectors/1?season=11')
  })

  it('al moverla la guarda sin compartir y vuelve a preguntar', async () => {
    const coordinates: [number, number] = [-68.2, -34.2]
    const moved = { ...WELL, location: { type: 'Point' as const, coordinates } }
    vi.mocked(waterRequest).mockResolvedValue(moved)
    vi.mocked(confirmSharing).mockResolvedValue(moved)
    const { wrapper } = await openAt('/farm/7/sectors/1/water-points/10')

    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('locate', [-68.2, -34.2])
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(vi.mocked(waterRequest).mock.calls[0]![2]).toMatchObject({
      shared: false,
      location: moved.location,
    })
    expect(confirmSharing).toHaveBeenCalledWith(moved)
  })

  it('si el servidor rechaza el movimiento, la aguada vuelve a su lugar', async () => {
    vi.mocked(waterRequest).mockRejectedValue(
      new Error('La aguada tiene que estar dentro del sector.'),
    )
    const { wrapper } = await openAt('/farm/7/sectors/1/water-points/10')
    const map = wrapper.getComponent({ name: 'UnitsMap' })

    map.vm.$emit('locate', [-70, -30])
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe(
      'La aguada tiene que estar dentro del sector.',
    )
    expect(map.props('waterPosition')).toBeNull()
    expect(confirmSharing).not.toHaveBeenCalled()
  })

  it('avisa si la aguada no es de ese sector, sin ofrecer reintentar', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/2/water-points/10')
    expect(wrapper.get('[role="alert"]').text()).toContain('No se encontró la aguada')
    expect(wrapper.text()).not.toContain('Reintentar')
    expect(wrapper.find('form').exists()).toBe(false)
  })
})

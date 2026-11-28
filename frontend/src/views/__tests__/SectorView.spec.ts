import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, type VueWrapper } from '@vue/test-utils'
import { ApiError } from '@/api/errors'
import { listScenarios, listSeasons } from '@/api/scenarios'
import {
  deleteProductionUnit,
  listProductionUnits,
  updateProductionUnit,
} from '@/api/productionUnits'
import { listScenarioWaterPoints, waterRequest } from '@/api/waterPoints'
import { NORTH, SCENARIO, SOUTH, WELL, openAt, season } from './farmFixtures'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', async (original) => ({
  ...(await original<typeof import('@/api/productionUnits')>()),
  listProductionUnits: vi.fn(),
  updateProductionUnit: vi.fn(),
  deleteProductionUnit: vi.fn(),
}))
vi.mock('@/api/waterPoints', () => ({
  listScenarioWaterPoints: vi.fn(),
  waterRequest: vi.fn(),
}))

const polygon = { type: 'Polygon' as const, coordinates: [[[-68, -34]]] as [number, number][][] }

function button(wrapper: VueWrapper, text: string) {
  return wrapper.findAll('button').find((item) => item.text() === text)!
}

function href(wrapper: VueWrapper, text: string) {
  return wrapper
    .findAll('a')
    .find((item) => item.text() === text)!
    .attributes('href')
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([SCENARIO])
  vi.mocked(listProductionUnits).mockResolvedValue([NORTH, SOUTH])
  vi.mocked(listSeasons).mockResolvedValue([season(12, 2026, true)])
  vi.mocked(listScenarioWaterPoints).mockResolvedValue([WELL])
})

describe('Pantalla del sector', () => {
  it('muestra el título, la campaña, las tarjetas, el mapa y el rodeo', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/1')

    expect(wrapper.get('h1').text()).toBe('Potrero Norte')
    expect(wrapper.text()).toContain('Campaña 2026/27')
    const cards = wrapper.get('.cards').text()
    expect(cards).toContain('100 ha')
    expect(cards).toContain('60 ha')
    expect(cards).toContain('60 % del total')
    expect(cards).toContain('4.200 L/día')
    const map = wrapper.getComponent({ name: 'UnitsMap' })
    expect(map.props('units')).toEqual([NORTH])
    expect(map.props('referenceUnits')).toEqual([SOUTH])
    expect(map.props('waterPoints')).toEqual([WELL])
    expect(wrapper.getComponent({ name: 'HerdForm' }).props()).toEqual({
      season: season(12, 2026, true),
      unitId: 1,
    })
    const links = wrapper.findAll('.breadcrumb a').map((a) => a.attributes('href'))
    expect(links).toEqual(['/farm/scenarios', '/farm/7'])
  })

  it('lleva a calcular con el escenario, el sector y la campaña', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/1')
    const link = wrapper.findAll('a').find((a) => a.text() === 'Calcular')!
    expect(link.attributes('href')).toBe(
      '/calculators/carrying-capacity?scenario=7&unit=1&season=12',
    )
  })

  it('muestra la campaña elegida y la pasa al rodeo y a los enlaces', async () => {
    vi.mocked(listSeasons).mockResolvedValue([season(11, 2025), season(12, 2026, true)])
    const { wrapper } = await openAt('/farm/7/sectors/1?season=11')

    expect(wrapper.get('.season-meta').text()).toContain('Campaña 2025/26')
    expect(wrapper.getComponent({ name: 'HerdForm' }).props('season').id).toBe(11)
    const links = wrapper.findAll('.breadcrumb a').map((a) => a.attributes('href'))
    expect(links).toEqual(['/farm/scenarios', '/farm/7?season=11'])
    expect(href(wrapper, 'Cambiar campaña')).toBe('/farm/7?season=11')
    expect(href(wrapper, 'Calcular')).toBe(
      '/calculators/carrying-capacity?scenario=7&unit=1&season=11',
    )
    expect(href(wrapper, 'Ubicar aguada')).toBe('/farm/7/sectors/1/water-points/new?season=11')
    expect(wrapper.get('tbody a').attributes('href')).toBe(
      '/farm/7/sectors/1/water-points/10?season=11',
    )
  })

  it('si la campaña de la dirección no es del escenario, usa la actual', async () => {
    vi.mocked(listSeasons).mockResolvedValue([season(11, 2025), season(12, 2026, true)])
    const { wrapper } = await openAt('/farm/7/sectors/1?season=99')

    expect(wrapper.get('.season-meta').text()).toContain('Campaña 2026/27')
    expect(wrapper.getComponent({ name: 'HerdForm' }).props('season').id).toBe(12)
  })

  it('carga el rodeo de otra campaña al cambiar la dirección', async () => {
    vi.mocked(listSeasons).mockResolvedValue([season(11, 2025), season(12, 2026, true)])
    const { wrapper, router } = await openAt('/farm/7/sectors/1?season=11')

    await router.push('/farm/7/sectors/1?season=12')
    await flushPromises()

    expect(wrapper.getComponent({ name: 'HerdForm' }).props('season').id).toBe(12)
  })

  it('avisa si el sector no tiene aguadas o si alguna no tiene los litros', async () => {
    vi.mocked(listScenarioWaterPoints).mockResolvedValueOnce([])
    const empty = await openAt('/farm/7/sectors/1')
    expect(empty.wrapper.get('.cards').text()).toContain('El sector no tiene aguadas.')

    vi.mocked(listScenarioWaterPoints).mockResolvedValueOnce([
      WELL,
      { ...WELL, id: 11, refill_l_day: null },
    ])
    const some = await openAt('/farm/7/sectors/1')
    expect(some.wrapper.get('.cards').text()).toContain(
      'Falta cargar los litros de 1 de las 2 aguadas.',
    )

    vi.mocked(listScenarioWaterPoints).mockResolvedValueOnce([{ ...WELL, refill_l_day: null }])
    const single = await openAt('/farm/7/sectors/1')
    expect(single.wrapper.get('.cards').text()).toContain('Falta cargar los litros de la aguada.')
  })

  it('sin aguadas explica por qué no hay superficie aprovechable y no muestra su leyenda', async () => {
    vi.mocked(listScenarioWaterPoints).mockResolvedValue([])
    vi.mocked(listProductionUnits).mockResolvedValue([{ ...NORTH, usable_area_ha: 0 }, SOUTH])
    const { wrapper } = await openAt('/farm/7/sectors/1?season=12')

    const card = wrapper.findAll('.cards > div')[1]!
    expect(card.text()).toContain('Sin aguadas no hay superficie aprovechable')
    expect(card.get('a').text()).toBe('Ubicar aguada')
    expect(card.get('a').attributes('href')).toBe('/farm/7/sectors/1/water-points/new?season=12')
    expect(wrapper.get('.map-legend').text()).toBe('Sector vecino')
  })

  it('la leyenda no muestra «Aguada» si el sector solo tiene aguadas compartidas', async () => {
    const neighbor = {
      ...WELL,
      id: 20,
      production_unit_id: 2,
      shared: true,
      neighbor_unit_ids: [1],
    }
    vi.mocked(listScenarioWaterPoints).mockResolvedValue([neighbor])
    const { wrapper } = await openAt('/farm/7/sectors/1')

    expect(wrapper.get('.map-legend').text()).not.toContain('Aguada')
  })

  it('muestra las aguadas propias y como referencia las compartidas por vecinos', async () => {
    const neighbor = {
      ...WELL,
      id: 20,
      production_unit_id: 2,
      shared: true,
      neighbor_unit_ids: [1],
    }
    const lost = { ...WELL, id: 12, name: 'Vieja', shared: true, neighbor_unit_ids: [] }
    vi.mocked(listScenarioWaterPoints).mockResolvedValue([WELL, lost, neighbor])
    const { wrapper } = await openAt('/farm/7/sectors/1')

    const map = wrapper.getComponent({ name: 'UnitsMap' })
    expect(map.props('waterPoints')).toEqual([WELL, lost])
    expect(map.props('sharedWaterPoints')).toEqual([neighbor])
    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('4.200 L/día')
    expect(rows[1]!.text()).toContain('ya no está en el límite con otro sector')
    expect(rows[0]!.get('a').attributes('href')).toBe('/farm/7/sectors/1/water-points/10')
  })

  it('cambia el nombre desde la ventana sin tocar el contorno', async () => {
    vi.mocked(updateProductionUnit).mockResolvedValue({ ...NORTH, name: 'Potrero Este' })
    const { wrapper } = await openAt('/farm/7/sectors/1')

    await button(wrapper, 'Editar').trigger('click')
    await wrapper.get('#unit-new-name').setValue('Potrero Este')
    vi.mocked(listProductionUnits).mockResolvedValue([{ ...NORTH, name: 'Potrero Este' }, SOUTH])
    await wrapper.get('[role="dialog"] form').trigger('submit')
    await flushPromises()

    expect(updateProductionUnit).toHaveBeenCalledWith(1, {
      name: 'Potrero Este',
      polygon: NORTH.polygon,
    })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(wrapper.get('h1').text()).toBe('Potrero Este')
  })

  it('bloquea el resto de la pantalla mientras se edita el contorno', async () => {
    vi.mocked(updateProductionUnit).mockResolvedValue(NORTH)
    const { wrapper } = await openAt('/farm/7/sectors/1')

    await button(wrapper, 'Editar contorno').trigger('click')
    const map = wrapper.getComponent({ name: 'UnitsMap' })
    expect(map.props('editingId')).toBe(1)
    for (const part of ['.breadcrumb', '.heading', '.cards', '.rest']) {
      expect(wrapper.get(part).attributes('inert')).toBeDefined()
    }

    map.vm.$emit('reshape', polygon)
    await button(wrapper, 'Guardar contorno').trigger('click')
    await flushPromises()

    expect(updateProductionUnit).toHaveBeenCalledWith(1, { name: 'Potrero Norte', polygon })
    expect(map.props('editingId')).toBeNull()
    expect(wrapper.get('.breadcrumb').attributes('inert')).toBeUndefined()
    expect(wrapper.get('.rest').attributes('inert')).toBeUndefined()
  })

  it('si el servidor rechaza el contorno, muestra el motivo y sigue editando', async () => {
    vi.mocked(updateProductionUnit).mockRejectedValue(
      new ApiError('El contorno se superpone con el sector «Potrero Sur».'),
    )
    const { wrapper } = await openAt('/farm/7/sectors/1')

    await button(wrapper, 'Editar contorno').trigger('click')
    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('reshape', polygon)
    await button(wrapper, 'Guardar contorno').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('se superpone con el sector')
    expect(wrapper.getComponent({ name: 'UnitsMap' }).props('editingId')).toBe(1)
  })

  it('cancelar la edición del contorno no guarda nada', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/1')
    await button(wrapper, 'Editar contorno').trigger('click')
    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('reshape', polygon)
    await button(wrapper, 'Cancelar').trigger('click')

    expect(updateProductionUnit).not.toHaveBeenCalled()
    expect(wrapper.getComponent({ name: 'UnitsMap' }).props('editingId')).toBeNull()
  })

  it('elimina una aguada y vuelve a cargar el sector', async () => {
    vi.spyOn(window, 'confirm').mockReturnValueOnce(true)
    vi.mocked(waterRequest).mockResolvedValue(undefined)
    const { wrapper } = await openAt('/farm/7/sectors/1')

    vi.mocked(listScenarioWaterPoints).mockResolvedValue([])
    await wrapper.get('tbody .danger').trigger('click')
    await flushPromises()

    expect(waterRequest).toHaveBeenCalledWith('/water-points/10', 'DELETE')
    expect(wrapper.find('tbody').exists()).toBe(false)
  })

  it('elimina el sector y vuelve al escenario con la misma campaña', async () => {
    vi.spyOn(window, 'confirm').mockReturnValueOnce(true)
    vi.mocked(deleteProductionUnit).mockResolvedValue()
    const { wrapper, router } = await openAt('/farm/7/sectors/1?season=12')

    await button(wrapper, 'Eliminar sector').trigger('click')
    await flushPromises()

    expect(deleteProductionUnit).toHaveBeenCalledWith(1)
    expect(router.currentRoute.value.fullPath).toBe('/farm/7?season=12')
  })

  it('no elimina el sector si no se confirma', async () => {
    vi.spyOn(window, 'confirm').mockReturnValueOnce(false)
    const { wrapper, router } = await openAt('/farm/7/sectors/1')

    await button(wrapper, 'Eliminar sector').trigger('click')
    await flushPromises()

    expect(deleteProductionUnit).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/farm/7/sectors/1')
  })

  it('avisa si el sector no es del escenario, sin ofrecer reintentar', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/99')
    expect(wrapper.get('[role="alert"]').text()).toContain('No se encontró este sector')
    expect(wrapper.text()).not.toContain('Reintentar')
    expect(wrapper.findComponent({ name: 'HerdForm' }).exists()).toBe(false)
  })

  it('si falla la carga, deja reintentar', async () => {
    vi.mocked(listScenarios).mockRejectedValueOnce(new Error('Sin red'))
    const { wrapper } = await openAt('/farm/7/sectors/1')
    expect(wrapper.get('[role="alert"]').text()).toContain('No se pudo cargar el sector')

    await button(wrapper, 'Reintentar').trigger('click')
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Potrero Norte')
  })

  it('carga otro sector al cambiar la dirección', async () => {
    const { wrapper, router } = await openAt('/farm/7/sectors/1')
    await router.push('/farm/7/sectors/2')
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Potrero Sur')
  })
})

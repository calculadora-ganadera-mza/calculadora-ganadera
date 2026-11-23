import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { ApiError } from '@/api/errors'
import { listScenarios, listSeasons } from '@/api/scenarios'
import { createProductionUnit, listProductionUnits } from '@/api/productionUnits'
import { listScenarioWaterPoints } from '@/api/waterPoints'
import { NORTH, SCENARIO, SOUTH, openAt, season } from './farmFixtures'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', async (original) => ({
  ...(await original<typeof import('@/api/productionUnits')>()),
  listProductionUnits: vi.fn(),
  createProductionUnit: vi.fn(),
}))
vi.mock('@/api/waterPoints', () => ({ listScenarioWaterPoints: vi.fn() }))

const polygon = { type: 'Polygon' as const, coordinates: [[[-68, -34]]] as [number, number][][] }

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([SCENARIO])
  vi.mocked(listProductionUnits).mockResolvedValue([NORTH, SOUTH])
  vi.mocked(listSeasons).mockResolvedValue([season(12, 2026, true)])
  vi.mocked(listScenarioWaterPoints).mockResolvedValue([])
})

describe('Dibujar sector', () => {
  it('muestra los demás sectores como referencia fija', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/new')
    const map = wrapper.getComponent({ name: 'UnitsMap' })
    expect(map.props('units')).toEqual([])
    expect(map.props('referenceUnits')).toEqual([NORTH, SOUTH])
    expect(map.props('readOnly')).toBeFalsy()
  })

  it('guarda el sector dibujado y abre su pantalla', async () => {
    vi.mocked(createProductionUnit).mockResolvedValue({ ...NORTH, id: 3, name: 'Sector 3' })
    const { wrapper, router } = await openAt('/farm/7/sectors/new')

    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('draw', polygon)
    await wrapper.get('#unit-name').setValue(' Sector 3 ')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(createProductionUnit).toHaveBeenCalledWith(7, { name: 'Sector 3', polygon })
    expect(router.currentRoute.value.path).toBe('/farm/7/sectors/3')
  })

  it('pide el contorno antes de guardar y cancelar vuelve al escenario', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/new')
    await wrapper.get('#unit-name').setValue('Sector 3')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('Dibujá el contorno del sector en el mapa.')
    expect(createProductionUnit).not.toHaveBeenCalled()
    const cancel = wrapper.findAll('a').find((a) => a.text() === 'Cancelar')!
    expect(cancel.attributes('href')).toBe('/farm/7')
  })

  it('pide el nombre antes de guardar', async () => {
    const { wrapper } = await openAt('/farm/7/sectors/new')
    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('draw', polygon)
    await wrapper.get('#unit-name').setValue('   ')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('Falta el nombre del sector.')
    expect(createProductionUnit).not.toHaveBeenCalled()
  })

  it('si el servidor rechaza el contorno, muestra el motivo y no sale de la pantalla', async () => {
    vi.mocked(createProductionUnit).mockRejectedValue(
      new ApiError('El contorno se superpone con el sector «Potrero Norte».'),
    )
    const { wrapper, router } = await openAt('/farm/7/sectors/new')

    wrapper.getComponent({ name: 'UnitsMap' }).vm.$emit('draw', polygon)
    await wrapper.get('#unit-name').setValue('Sector 3')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('se superpone con el sector')
    expect(router.currentRoute.value.path).toBe('/farm/7/sectors/new')
  })

  it('avisa si el escenario no existe, sin ofrecer reintentar', async () => {
    const { wrapper } = await openAt('/farm/99/sectors/new')
    expect(wrapper.get('[role="alert"]').text()).toContain('No se encontró el escenario.')
    expect(wrapper.text()).not.toContain('Reintentar')
  })
})

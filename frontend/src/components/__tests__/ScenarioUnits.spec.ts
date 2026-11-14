import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import ScenarioUnits from '../ScenarioUnits.vue'
import UnitsMap from '../UnitsMap.vue'
import WaterPoints from '../WaterPoints.vue'
import { confirmSharing, waterRequest } from '@/api/waterPoints'
vi.mock('@/api/waterPoints', () => ({
  waterRequest: vi.fn(),
  confirmSharing: vi.fn((point: unknown) => Promise.resolve(point)),
}))
import {
  ApiError,
  createProductionUnit,
  deleteProductionUnit,
  listProductionUnits,
  updateProductionUnit,
  type PolygonGeoJSON,
  type ProductionUnit,
} from '@/api/productionUnits'

// Simula la API, pero conserva ApiError para distinguir los mensajes del backend
vi.mock('@/api/productionUnits', async (importOriginal) => ({
  ApiError: (await importOriginal<typeof import('@/api/productionUnits')>()).ApiError,
  listProductionUnits: vi.fn(),
  createProductionUnit: vi.fn(),
  updateProductionUnit: vi.fn(),
  deleteProductionUnit: vi.fn(),
}))

const SQUARE: PolygonGeoJSON = {
  type: 'Polygon',
  coordinates: [
    [
      [-68.09, -34.58],
      [-68.08, -34.58],
      [-68.08, -34.57],
      [-68.09, -34.57],
      [-68.09, -34.58],
    ],
  ],
}

const OTHER: PolygonGeoJSON = {
  type: 'Polygon',
  coordinates: [
    [
      [-68.2, -34.6],
      [-68.1, -34.6],
      [-68.1, -34.5],
      [-68.2, -34.6],
    ],
  ],
}

const UNIT = { id: 1, name: 'Potrero 1', polygon: SQUARE, area_ha: 101.84, usable_area_ha: 0 }

// El mapa se reemplaza por un componente vacío: las pruebas emiten sus eventos
async function mountUnits() {
  const wrapper = mount(ScenarioUnits, {
    props: { scenarioId: 7 },
    global: { stubs: { UnitsMap: true, WaterPoints: true } },
  })
  await flushPromises()
  return { wrapper, map: wrapper.findComponent(UnitsMap) }
}

function button(wrapper: Awaited<ReturnType<typeof mountUnits>>['wrapper'], text: string) {
  return wrapper.findAll('button').find((item) => item.text() === text)!
}

beforeEach(() => {
  vi.mocked(waterRequest).mockReset().mockResolvedValue([])
  vi.mocked(confirmSharing)
    .mockReset()
    .mockImplementation(async (point) => point)
  vi.mocked(listProductionUnits).mockReset().mockResolvedValue([UNIT])
  vi.mocked(createProductionUnit).mockReset()
  vi.mocked(updateProductionUnit).mockReset()
  vi.mocked(deleteProductionUnit).mockReset()
})
afterEach(() => vi.restoreAllMocks())

describe('ScenarioUnits', () => {
  it('muestra los sectores con su superficie en hectáreas', async () => {
    const { wrapper } = await mountUnits()

    expect(listProductionUnits).toHaveBeenCalledWith(7)
    expect(wrapper.find('.lote-name').text()).toContain('Potrero 1')
    expect(wrapper.text()).toContain('101,8 ha')
  })

  it('guarda el contorno dibujado con el nombre ingresado', async () => {
    vi.mocked(listProductionUnits)
      .mockResolvedValueOnce([])
      .mockResolvedValue([{ ...UNIT, id: 2, name: 'Bajo' }])
    vi.mocked(createProductionUnit).mockResolvedValue({ ...UNIT, id: 2, name: 'Bajo' })
    const { wrapper, map } = await mountUnits()

    map.vm.$emit('draw', SQUARE)
    await flushPromises()
    await wrapper.find('#unit-name').setValue('  Bajo ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(createProductionUnit).toHaveBeenCalledWith(7, { name: 'Bajo', polygon: SQUARE })
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.text()).toContain('Bajo')
    expect(wrapper.text()).toContain('101,8 ha')
  })

  it('pide el nombre antes de guardar', async () => {
    const { wrapper, map } = await mountUnits()

    map.vm.$emit('draw', SQUARE)
    await flushPromises()
    await wrapper.find('form').trigger('submit')

    expect(createProductionUnit).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Falta el nombre del sector.')
  })

  it('muestra el mensaje del backend si el contorno no es válido', async () => {
    vi.mocked(createProductionUnit).mockRejectedValue(
      new ApiError('El contorno no es válido: no puede cruzarse consigo mismo.'),
    )
    const { wrapper, map } = await mountUnits()

    map.vm.$emit('draw', SQUARE)
    await flushPromises()
    await wrapper.find('#unit-name').setValue('Moño')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toBe(
      'El contorno no es válido: no puede cruzarse consigo mismo.',
    )
    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('guarda el contorno editado y muestra la superficie nueva', async () => {
    const wide = { ...SQUARE, coordinates: [[...SQUARE.coordinates[0]!]] }
    vi.mocked(updateProductionUnit).mockResolvedValue({ ...UNIT, polygon: wide, area_ha: 203.6 })
    const { wrapper, map } = await mountUnits()

    await button(wrapper, 'Editar contorno').trigger('click')
    expect(map.props('editingId')).toBe(1)
    map.vm.$emit('reshape', wide)
    vi.mocked(listProductionUnits).mockResolvedValue([{ ...UNIT, area_ha: 203.6 }])
    await button(wrapper, 'Guardar contorno').trigger('click')
    await flushPromises()

    expect(updateProductionUnit).toHaveBeenCalledWith(1, { name: 'Potrero 1', polygon: wide })
    expect(wrapper.text()).toContain('203,6 ha')
    expect(map.props('editingId')).toBeNull()
  })

  it('elimina el sector después de confirmar', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(deleteProductionUnit).mockResolvedValue()
    const { wrapper } = await mountUnits()

    vi.mocked(listProductionUnits).mockResolvedValue([])
    await button(wrapper, 'Eliminar').trigger('click')
    await flushPromises()

    expect(deleteProductionUnit).toHaveBeenCalledWith(1)
    expect(wrapper.text()).toContain('Todavía no hay lotes.')
  })

  it('no descarta un contorno dibujado mientras se guardaba otro', async () => {
    let finishSave!: (unit: ProductionUnit) => void
    vi.mocked(createProductionUnit).mockReturnValue(
      new Promise((resolve) => (finishSave = resolve)),
    )
    const { wrapper, map } = await mountUnits()

    map.vm.$emit('draw', SQUARE)
    await flushPromises()
    await wrapper.find('#unit-name').setValue('Bajo')
    await wrapper.find('form').trigger('submit')
    map.vm.$emit('draw', OTHER)
    finishSave({ ...UNIT, id: 2, name: 'Bajo' })
    await flushPromises()

    expect(map.props('draft')).toEqual(OTHER)
    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('no cierra una edición empezada mientras se guardaba la anterior', async () => {
    let finishSave!: (unit: ProductionUnit) => void
    vi.mocked(updateProductionUnit).mockReturnValue(
      new Promise((resolve) => (finishSave = resolve)),
    )
    const { wrapper, map } = await mountUnits()

    await button(wrapper, 'Editar contorno').trigger('click')
    map.vm.$emit('reshape', OTHER)
    await button(wrapper, 'Guardar contorno').trigger('click')
    await button(wrapper, 'Cancelar').trigger('click')
    await button(wrapper, 'Editar contorno').trigger('click')
    finishSave({ ...UNIT, polygon: OTHER })
    await flushPromises()

    expect(map.props('editingId')).toBe(1)
  })

  it('no elimina el sector si no se confirma', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { wrapper } = await mountUnits()

    await button(wrapper, 'Eliminar').trigger('click')

    expect(deleteProductionUnit).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Potrero 1')
  })
})

it('selecciona el sector desde el mapa y muestra sus aguadas en la card', async () => {
  const { wrapper, map } = await mountUnits()
  expect(wrapper.find('.lote-card').classes()).not.toContain('active')
  map.vm.$emit('selectUnit', 1)
  await flushPromises()
  expect(wrapper.find('.lote-card').classes()).toContain('active')
  expect(wrapper.findComponent(WaterPoints).props('unitId')).toBe(1)
  expect(map.props('waterMode')).toBe(false)
  map.vm.$emit('selectWater', 3)
  await flushPromises()
  expect(map.props('selectedWaterId')).toBe(3)
})

describe('Creación general de aguadas', () => {
  it('asigna por ubicación aunque otro sector esté seleccionado y envía los litros', async () => {
    const second = { ...UNIT, id: 2, name: 'Otro', polygon: OTHER }
    vi.mocked(listProductionUnits).mockResolvedValue([UNIT, second])
    const { wrapper, map } = await mountUnits()
    map.vm.$emit('selectUnit', 1)
    await flushPromises()
    await wrapper.find('.map-actions .accent').trigger('click')
    map.vm.$emit('locate', [-68.15, -34.55])
    await flushPromises()
    expect(wrapper.find('#crosshair-action-bar').text()).toContain('Nueva aguada en Otro')
    const inputs = wrapper.findAll('#crosshair-action-bar input')
    await inputs[0]!.setValue('Tanque nuevo')
    await inputs[1]!.setValue('900')
    vi.mocked(waterRequest).mockResolvedValueOnce({ id: 8, name: 'Tanque nuevo' })
    await wrapper.find('#crosshair-action-bar .sky').trigger('click')
    await flushPromises()
    expect(waterRequest).toHaveBeenCalledWith('/production-units/2/water-points', 'POST', {
      shared: false,
      name: 'Tanque nuevo',
      location: { type: 'Point', coordinates: [-68.15, -34.55] },
      refill_l_day: 900,
    })
    expect(map.props('selectedUnitId')).toBe(2)
    expect(map.props('selectedWaterId')).toBe(8)
    expect(wrapper.find('#crosshair-action-bar').exists()).toBe(false)
  })

  it('no asigna puntos exteriores y conserva el panel ante un error de guardado', async () => {
    const { wrapper, map } = await mountUnits()
    await wrapper.find('.map-actions .accent').trigger('click')
    map.vm.$emit('locate', [-70, -35])
    await flushPromises()
    expect(wrapper.find('#crosshair-action-bar .sky').attributes('disabled')).toBeDefined()
    map.vm.$emit('locate', [-68.085, -34.575])
    await flushPromises()
    vi.mocked(waterRequest).mockRejectedValueOnce(new Error('fallo'))
    await wrapper.find('#crosshair-action-bar .sky').trigger('click')
    await flushPromises()
    expect(wrapper.find('#crosshair-action-bar').exists()).toBe(true)
    expect(wrapper.text()).toContain('fallo')
    expect(waterRequest).toHaveBeenLastCalledWith(
      '/production-units/1/water-points',
      'POST',
      expect.objectContaining({ refill_l_day: null }),
    )
  })
})

it('refresca la tarjeta y la cobertura al guardar una aguada desde el mapa', async () => {
  const covered = {
    ...UNIT,
    usable_area_ha: 50.92,
    usable_geometry: {
      type: 'MultiPolygon' as const,
      coordinates: [SQUARE.coordinates],
    },
  }
  vi.mocked(listProductionUnits).mockResolvedValueOnce([UNIT]).mockResolvedValue([covered])
  vi.mocked(waterRequest)
    .mockResolvedValueOnce([])
    .mockResolvedValueOnce({
      id: 8,
      production_unit_id: 1,
      name: 'Aguada 1',
      location: { type: 'Point', coordinates: [-68.085, -34.575] },
      refill_l_day: null,
      shared: false,
      neighbor_unit_ids: [],
    })
  vi.mocked(waterRequest).mockResolvedValue([
    {
      id: 8,
      production_unit_id: 1,
      name: 'Aguada 1',
      location: { type: 'Point', coordinates: [-68.085, -34.575] },
      refill_l_day: null,
      shared: false,
      neighbor_unit_ids: [],
    },
  ])
  const wrapper = mount(ScenarioUnits, {
    props: { scenarioId: 7 },
    global: { stubs: { UnitsMap: true } },
  })
  await flushPromises()
  const map = wrapper.findComponent(UnitsMap)
  await wrapper.find('.map-actions .accent').trigger('click')
  map.vm.$emit('locate', [-68.085, -34.575])
  await flushPromises()
  await wrapper.find('#crosshair-action-bar .sky').trigger('click')
  await flushPromises()
  expect(wrapper.find('.water-points h4').text()).toBe('AGUADAS (1)')
  expect(wrapper.find('.point-choice').text()).toContain('Aguada 1')
  expect(wrapper.find('.card-heading .badge').text()).toBe('50% cubierto')
  expect(map.props('units')[0]!.usable_geometry).toEqual(covered.usable_geometry)
  expect(wrapper.text()).not.toContain('Radio fijo')
  expect(wrapper.text()).not.toContain('2,5 km')
})

it('mantiene el nombre durante el dibujo y habilita guardar solo al cerrar el contorno', async () => {
  const { wrapper, map } = await mountUnits()
  await wrapper.find('.map-actions button').trigger('click')
  const save = wrapper.find('#draw-lote-bar .primary')
  expect(save.text()).toBe('Guardar lote')
  expect(save.attributes('disabled')).toBeDefined()
  await wrapper.find('#unit-name').setValue('Lote Norte')
  await wrapper.find('#draw-lote-bar').trigger('submit')
  expect(createProductionUnit).not.toHaveBeenCalled()
  map.vm.$emit('draw', SQUARE)
  await flushPromises()
  expect((wrapper.find('#unit-name').element as HTMLInputElement).value).toBe('Lote Norte')
  expect(save.attributes('disabled')).toBeUndefined()
})

it('admite aguadas hasta 5 m del borde y rechaza las más alejadas', async () => {
  const { wrapper, map } = await mountUnits()
  await wrapper.find('.map-actions .accent').trigger('click')
  map.vm.$emit('locate', [-68.085, -34.58003])
  await flushPromises()
  expect(wrapper.find('#crosshair-action-bar .sky').attributes('disabled')).toBeUndefined()
  expect(wrapper.find('#crosshair-action-bar').text()).toContain('Nueva aguada en Potrero 1')
  expect(wrapper.find('#crosshair-action-bar').text()).toContain('Reposición (L/día)')
  map.vm.$emit('locate', [-68.085, -34.58011])
  await flushPromises()
  expect(wrapper.find('#crosshair-action-bar .sky').attributes('disabled')).toBeDefined()
})

it('carga todas las aguadas con una petición por escenario sin consultas por tarjeta', async () => {
  vi.mocked(listProductionUnits).mockResolvedValue([UNIT, { ...UNIT, id: 2 }])
  vi.mocked(waterRequest).mockResolvedValue([
    {
      id: 3,
      production_unit_id: 2,
      name: 'Tanque',
      shared: false,
      neighbor_unit_ids: [],
      location: { type: 'Point', coordinates: [-68, -34] },
      refill_l_day: null,
    },
  ])
  const wrapper = mount(ScenarioUnits, {
    props: { scenarioId: 7 },
    global: { stubs: { UnitsMap: true } },
  })
  await flushPromises()
  expect(waterRequest).toHaveBeenCalledTimes(1)
  expect(waterRequest).toHaveBeenCalledWith('/scenarios/7/water-points')
  expect(wrapper.findAll('.water-points h4').map((h) => h.text())).toEqual([
    'AGUADAS (0)',
    'AGUADAS (1)',
  ])
  vi.mocked(waterRequest).mockClear()
  wrapper.findComponent(WaterPoints).vm.$emit('changed')
  await flushPromises()
  expect(waterRequest).toHaveBeenCalledTimes(1)
  expect(waterRequest).toHaveBeenCalledWith('/scenarios/7/water-points')
})

it('termina el alta y refresca la cobertura aunque falle la confirmación de compartir', async () => {
  const { wrapper, map } = await mountUnits()
  await wrapper.find('.map-actions .accent').trigger('click')
  map.vm.$emit('locate', [-68.085, -34.575])
  await flushPromises()
  const point = {
    id: 9,
    name: 'Nueva',
    shared: false,
    neighbor_unit_ids: [2],
    location: { type: 'Point' as const, coordinates: [-68.085, -34.575] as [number, number] },
    refill_l_day: null,
  }
  vi.mocked(waterRequest).mockResolvedValueOnce(point)
  vi.mocked(confirmSharing).mockRejectedValueOnce(new Error('Falló compartir'))
  await wrapper.find('#crosshair-action-bar .sky').trigger('click')
  await flushPromises()
  expect(wrapper.find('#crosshair-action-bar').exists()).toBe(false)
  expect(map.props('waterMode')).toBe(false)
  expect(map.props('selectedWaterId')).toBe(9)
  expect(wrapper.text()).toContain('Falló compartir')
  expect(waterRequest).toHaveBeenCalledWith('/scenarios/7/water-points')
  expect(vi.mocked(waterRequest).mock.calls.filter(([, method]) => method === 'POST')).toHaveLength(
    1,
  )
})

it.each(['sectores', 'aguadas'])(
  'avisa si falla el refresco de %s y permite reintentar',
  async (resource) => {
    const { wrapper, map } = await mountUnits()
    if (resource === 'sectores')
      vi.mocked(listProductionUnits).mockRejectedValueOnce(new Error('sin red'))
    else vi.mocked(waterRequest).mockRejectedValueOnce(new Error('sin red'))
    wrapper.findComponent(WaterPoints).vm.$emit('changed')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('pueden estar desactualizados')
    expect(map.props('units')[0]!.usable_area_ha).toBe(0)
    vi.mocked(listProductionUnits).mockResolvedValue([{ ...UNIT, usable_area_ha: 50 }])
    await button(wrapper, 'Reintentar actualización').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(map.props('units')[0]!.usable_area_ha).toBe(50)
  },
)

it.each(['éxito', 'error'])(
  'ignora una respuesta antigua con %s tras un refresco más reciente',
  async (result) => {
    const { wrapper, map } = await mountUnits()
    let finish!: (units: ProductionUnit[]) => void
    let fail!: (error: Error) => void
    vi.mocked(listProductionUnits)
      .mockImplementationOnce(
        () =>
          new Promise((resolve, reject) => {
            finish = resolve
            fail = reject
          }),
      )
      .mockResolvedValueOnce([{ ...UNIT, usable_area_ha: 50 }])
    const child = wrapper.findComponent(WaterPoints)
    child.vm.$emit('changed')
    child.vm.$emit('changed')
    await flushPromises()
    expect(map.props('units')[0]!.usable_area_ha).toBe(50)
    if (result === 'éxito') finish([UNIT])
    else fail(new Error('respuesta vieja'))
    await flushPromises()
    expect(map.props('units')[0]!.usable_area_ha).toBe(50)
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  },
)

it('cierra la edición de contorno al editar una aguada y viceversa', async () => {
  vi.mocked(waterRequest).mockResolvedValue([
    {
      id: 3,
      production_unit_id: 1,
      name: 'Tanque',
      shared: false,
      neighbor_unit_ids: [],
      location: { type: 'Point', coordinates: [-68.085, -34.575] },
      refill_l_day: null,
    },
  ])
  const wrapper = mount(ScenarioUnits, {
    props: { scenarioId: 7 },
    global: { stubs: { UnitsMap: true } },
  })
  await flushPromises()
  const map = wrapper.findComponent(UnitsMap)
  await button(wrapper, 'Editar contorno').trigger('click')
  map.vm.$emit('reshape', OTHER)
  await flushPromises()
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'Editar')!
    .trigger('click')
  await flushPromises()
  expect(map.props('editingId')).toBe(null)
  expect(map.props('editingWaterId')).toBe(3)
  expect(wrapper.text()).not.toContain('Guardar contorno')
  await button(wrapper, 'Editar contorno').trigger('click')
  await flushPromises()
  expect(map.props('editingId')).toBe(1)
  expect(map.props('editingWaterId')).toBe(null)
  expect(wrapper.find('.water-points form').exists()).toBe(false)
  // El borrador anterior fue descartado, no se guarda al volver al contorno.
  await button(wrapper, 'Guardar contorno').trigger('click')
  expect(updateProductionUnit).not.toHaveBeenCalled()
})

it.each(['.map-actions .accent', '.water-points header button'])(
  'mantiene el alta abierta desde %s después de seleccionar una aguada',
  async (selector) => {
    vi.mocked(waterRequest).mockResolvedValue([
      {
        id: 3,
        production_unit_id: 1,
        name: 'Tanque',
        shared: false,
        neighbor_unit_ids: [],
        location: { type: 'Point', coordinates: [-68.085, -34.575] },
        refill_l_day: null,
      },
    ])
    const wrapper = mount(ScenarioUnits, {
      props: { scenarioId: 7 },
      global: { stubs: { UnitsMap: true } },
    })
    await flushPromises()
    await wrapper.find('.point-choice').trigger('click')
    const map = wrapper.findComponent(UnitsMap)
    expect(map.props('selectedWaterId')).toBe(3)
    await wrapper.find(selector).trigger('click')
    await flushPromises()
    expect(map.props('waterMode')).toBe(true)
    expect(wrapper.find('#crosshair-action-bar').exists()).toBe(true)
    map.vm.$emit('locate', [-68.085, -34.575])
    await flushPromises()
    expect(wrapper.find('#crosshair-action-bar .sky').attributes('disabled')).toBeUndefined()
  },
)

it('actualiza los vecinos y elimina la advertencia al crear un sector', async () => {
  const point = {
    id: 3,
    production_unit_id: 1,
    name: 'Compartida',
    shared: true,
    neighbor_unit_ids: [],
    location: { type: 'Point' as const, coordinates: [-68.08, -34.575] as [number, number] },
    refill_l_day: null,
  }
  vi.mocked(waterRequest).mockResolvedValue([point])
  const wrapper = mount(ScenarioUnits, {
    props: { scenarioId: 7 },
    global: { stubs: { UnitsMap: true } },
  })
  await flushPromises()
  const map = wrapper.findComponent(UnitsMap)
  vi.mocked(createProductionUnit).mockResolvedValue({
    ...UNIT,
    id: 2,
    name: 'Vecino',
    usable_area_ha: 50,
  })
  vi.mocked(listProductionUnits).mockResolvedValue([
    UNIT,
    { ...UNIT, id: 2, name: 'Vecino', usable_area_ha: 50 },
  ])
  vi.mocked(waterRequest).mockResolvedValue([{ ...point, neighbor_unit_ids: [2] }])
  map.vm.$emit('draw', SQUARE)
  await flushPromises()
  await wrapper.find('#unit-name').setValue('Vecino')
  await wrapper.find('#draw-lote-bar').trigger('submit')
  await flushPromises()
  expect(wrapper.findAll('.lote-card')).toHaveLength(2)
  expect(wrapper.text()).not.toContain('no se está compartiendo')
  expect(waterRequest).toHaveBeenCalledTimes(2)
  expect(
    wrapper.findAllComponents(WaterPoints)[0]!.props('savedPoints')![0]!.neighbor_unit_ids,
  ).toEqual([2])
})

it('integra el rodeo por campaña con la gestión de aguadas en cada lote', async () => {
  const wrapper = mount(ScenarioUnits, {
    props: { scenarioId: 7, seasonId: 12 },
    global: { stubs: { UnitsMap: true, WaterPoints: true, HerdForm: true } },
  })
  await flushPromises()
  const herd = wrapper.findComponent({ name: 'HerdForm' })
  expect(herd.props('seasonId')).toBe(12)
  expect(herd.props('unitId')).toBe(1)
  expect(wrapper.findComponent(WaterPoints).props('unitId')).toBe(1)
  await button(wrapper, 'Editar contorno').trigger('click')
  expect(wrapper.findComponent({ name: 'HerdForm' }).exists()).toBe(false)
  await button(wrapper, 'Cancelar').trigger('click')
  expect(wrapper.findComponent({ name: 'HerdForm' }).exists()).toBe(true)
})

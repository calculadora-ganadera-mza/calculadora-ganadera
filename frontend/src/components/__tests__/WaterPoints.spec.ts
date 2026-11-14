import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import WaterPoints from '../WaterPoints.vue'
import { confirmSharing, waterRequest, type WaterPoint } from '@/api/waterPoints'
vi.mock('@/api/waterPoints', () => ({
  waterRequest: vi.fn(),
  confirmSharing: vi.fn((point: unknown) => Promise.resolve(point)),
}))
const point: WaterPoint = {
  id: 3,
  name: 'Tanque',
  location: { type: 'Point', coordinates: [-68, -34] },
  refill_l_day: null,
  shared: true,
  neighbor_unit_ids: [],
}
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(waterRequest).mockResolvedValue([point])
})
describe('Aguadas', () => {
  it('muestra la advertencia exterior y permite editar', async () => {
    const wrapper = mount(WaterPoints, { props: { unitId: 1, position: null, selectedPointId: 3 } })
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Editar')!
      .trigger('click')
    expect(wrapper.text()).toContain('no se está compartiendo')
    expect(wrapper.emitted('edit')?.slice(-1)[0]).toEqual([3])
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('Tanque')
  })
  it('selecciona aguadas y expande su edición inline', async () => {
    const wrapper = mount(WaterPoints, { props: { unitId: 1, position: null } })
    await flushPromises()
    expect(wrapper.text()).toContain('Editar')
    expect(wrapper.find('form').exists()).toBe(false)
    await wrapper.find('.point-choice').trigger('click')
    expect(wrapper.emitted('select')).toEqual([[3]])
    await wrapper.setProps({ selectedPointId: 3 })
    expect(wrapper.text()).toContain('Editar')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Editar')!
      .trigger('click')
    expect(wrapper.find('form').exists()).toBe(true)
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Cancelar')!
      .trigger('click')
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.emitted('mode')?.slice(-1)[0]).toEqual([false])
  })
  it('guarda un punto exterior sin requerir litros', async () => {
    const wrapper = mount(WaterPoints, { props: { unitId: 1, position: [-68, -34] } })
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((b) => b.text() === '+ Ubicar aguada')!
      .trigger('click')
    await wrapper.find('input').setValue('Nueva')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(waterRequest).toHaveBeenCalledWith('/production-units/1/water-points', 'POST', {
      shared: false,
      name: 'Nueva',
      location: { type: 'Point', coordinates: [-68, -34] },
      refill_l_day: null,
    })
    expect(wrapper.emitted('changed')).toHaveLength(1)
  })
  it('conserva el formulario al fallar', async () => {
    const wrapper = mount(WaterPoints, { props: { unitId: 1, position: [-68, -34] } })
    await flushPromises()
    vi.mocked(waterRequest).mockRejectedValueOnce(new Error('fallo'))
    await wrapper
      .findAll('button')
      .find((b) => b.text() === '+ Ubicar aguada')!
      .trigger('click')
    await wrapper.find('input').setValue('Nueva')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('fallo')
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('Nueva')
  })
})

it('actualiza el contador y la lista cuando se crea una aguada desde el mapa', async () => {
  vi.mocked(waterRequest).mockResolvedValueOnce([])
  const wrapper = mount(WaterPoints, { props: { unitId: 1, position: null, savedPoints: [] } })
  await flushPromises()
  expect(wrapper.text()).toContain('AGUADAS (0)')
  await wrapper.setProps({ savedPoints: [point] })
  expect(wrapper.text()).toContain('AGUADAS (1)')
  expect(wrapper.find('.point-choice').text()).toContain('Tanque')
  expect(wrapper.find('.empty').exists()).toBe(false)
})

it('conserva la posición y reintenta el mismo movimiento tras un error', async () => {
  const wrapper = mount(WaterPoints, { props: { unitId: 1, position: null, selectedPointId: 3 } })
  await flushPromises()
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'Editar')!
    .trigger('click')
  await wrapper.setProps({ position: [-68.001, -34] })
  const editEvents = wrapper.emitted('edit')!.length
  vi.mocked(waterRequest).mockRejectedValueOnce(new Error('Error de red'))
  await wrapper.find('form').trigger('submit')
  await flushPromises()
  expect(wrapper.emitted('edit')).toHaveLength(editEvents)
  expect(wrapper.find('form').exists()).toBe(true)
  vi.mocked(waterRequest).mockResolvedValueOnce(point).mockResolvedValue([point])
  await wrapper.find('form').trigger('submit')
  await flushPromises()
  expect(waterRequest).toHaveBeenCalledWith(
    '/water-points/3',
    'PUT',
    expect.objectContaining({
      location: { type: 'Point', coordinates: [-68.001, -34] },
    }),
  )
  expect(wrapper.emitted('changed')).toHaveLength(1)
})

it('refresca el movimiento guardado aunque falle compartir y permite reintentar ese paso', async () => {
  const wrapper = mount(WaterPoints, { props: { unitId: 1, position: null, selectedPointId: 3 } })
  await flushPromises()
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'Editar')!
    .trigger('click')
  const moved = {
    ...point,
    shared: false,
    location: { type: 'Point' as const, coordinates: [-68.001, -34] as [number, number] },
  }
  await wrapper.setProps({ position: moved.location.coordinates })
  vi.mocked(waterRequest).mockResolvedValueOnce(moved).mockResolvedValue([moved])
  vi.mocked(confirmSharing).mockRejectedValueOnce(new Error('Error al compartir'))
  await wrapper.find('form').trigger('submit')
  await flushPromises()
  expect(wrapper.emitted('changed')).toHaveLength(1)
  expect(wrapper.find('form').exists()).toBe(false)
  expect(wrapper.find('[role="alert"]').text()).toContain('La aguada se guardó')
  expect(wrapper.emitted('points')!.slice(-1)[0]).toEqual([[moved]])
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'Reintentar uso compartido')!
    .trigger('click')
  await flushPromises()
  expect(waterRequest).toHaveBeenCalledWith('/water-points/3', 'PUT', {
    name: moved.name,
    location: moved.location,
    refill_l_day: moved.refill_l_day,
    shared: true,
  })
  expect(wrapper.emitted('changed')).toHaveLength(2)
  expect(wrapper.text()).not.toContain('Reintentar uso compartido')
})

it('delega la recarga al padre cuando recibe las aguadas por props', async () => {
  const wrapper = mount(WaterPoints, {
    props: { unitId: 1, position: null, selectedPointId: 3, savedPoints: [point] },
  })
  await flushPromises()
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'Editar')!
    .trigger('click')
  vi.mocked(waterRequest).mockRejectedValueOnce(new Error('sin red'))
  await wrapper.find('form').trigger('submit')
  await flushPromises()
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'Reintentar carga')!
    .trigger('click')
  expect(wrapper.emitted('reload')).toHaveLength(1)
  expect(waterRequest).toHaveBeenCalledTimes(1)
})

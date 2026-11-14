import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import WaterPoints from '../WaterPoints.vue'
import { waterRequest, type WaterPoint } from '@/api/waterPoints'
vi.mock('@/api/waterPoints', () => ({ waterRequest: vi.fn() }))
const point: WaterPoint = {
  id: 3,
  name: 'Tanque',
  location: { type: 'Point', coordinates: [-68, -34] },
  refill_l_day: null,
  outside_unit: true,
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
    expect(wrapper.text()).toContain('Esta aguada está fuera del sector')
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
    expect(wrapper.text()).toContain('No se pudo guardar')
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

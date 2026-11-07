import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import FarmView from '../FarmView.vue'
import { createScenario, fetchFirstSeasonYears, listScenarios } from '@/api/scenarios'

// Simula la API: la pantalla no le pide nada al backend real
vi.mock('@/api/scenarios', () => ({
  fetchFirstSeasonYears: vi.fn(),
  createScenario: vi.fn(),
  listScenarios: vi.fn(),
}))

const SCENARIO = {
  id: 1,
  name: 'La Aguada',
  seasons: [{ id: 1, start_date: '2026-07-01', end_date: '2027-06-30' }],
}

beforeEach(() => {
  vi.mocked(listScenarios).mockReset()
  vi.mocked(createScenario).mockReset()
  vi.mocked(fetchFirstSeasonYears)
    .mockReset()
    .mockResolvedValue([{ start_year: 2026, start_date: '2026-07-01', end_date: '2027-06-30' }])
})

describe('FarmView', () => {
  it('muestra el formulario si el usuario no tiene establecimientos', async () => {
    vi.mocked(listScenarios).mockResolvedValue([])
    const wrapper = mount(FarmView)
    await flushPromises()

    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('muestra el establecimiento con su campaña', async () => {
    vi.mocked(listScenarios).mockResolvedValue([SCENARIO])
    const wrapper = mount(FarmView)
    await flushPromises()

    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.text()).toContain('La Aguada')
    expect(wrapper.text()).toContain('Campaña 2026/27 (del 1/7/2026 al 30/6/2027)')
  })

  it('después de registrar muestra el establecimiento creado', async () => {
    vi.mocked(listScenarios).mockResolvedValue([])
    vi.mocked(createScenario).mockResolvedValue(SCENARIO)
    const wrapper = mount(FarmView)
    await flushPromises()

    await wrapper.find('input').setValue('La Aguada')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.text()).toContain('La Aguada')
  })

  it('avisa si no pudo cargar y deja reintentar', async () => {
    vi.mocked(listScenarios).mockRejectedValueOnce(new Error('Error 500'))
    const wrapper = mount(FarmView)
    await flushPromises()

    expect(wrapper.text()).toContain('No se pudieron cargar tus establecimientos.')

    vi.mocked(listScenarios).mockResolvedValue([SCENARIO])
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('La Aguada')
  })
})

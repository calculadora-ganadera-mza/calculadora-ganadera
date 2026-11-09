import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import ScenarioForm from '../ScenarioForm.vue'
import { createScenario, fetchFirstSeasonYears } from '@/api/scenarios'

// Simula la API: el formulario no le pide nada al backend real
vi.mock('@/api/scenarios', () => ({
  fetchFirstSeasonYears: vi.fn(),
  createScenario: vi.fn(),
}))

const OPTIONS = [
  { start_year: 2026, start_date: '2026-07-01', end_date: '2027-06-30' },
  { start_year: 2027, start_date: '2027-07-01', end_date: '2028-06-30' },
  { start_year: 2028, start_date: '2028-07-01', end_date: '2029-06-30' },
]

async function mountForm() {
  const wrapper = mount(ScenarioForm)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.mocked(fetchFirstSeasonYears).mockReset().mockResolvedValue(OPTIONS)
  vi.mocked(createScenario).mockReset()
})

describe('ScenarioForm', () => {
  it('muestra los tres años con sus fechas y elige el primero', async () => {
    const wrapper = await mountForm()
    const labels = wrapper.findAll('option').map((option) => option.text())

    expect(labels).toEqual([
      '2026/27 (del 1/7/2026 al 30/6/2027)',
      '2027/28 (del 1/7/2027 al 30/6/2028)',
      '2028/29 (del 1/7/2028 al 30/6/2029)',
    ])
    expect((wrapper.find('select').element as HTMLSelectElement).value).toBe('2026')
  })

  it('pide el nombre y no envía nada si está vacío', async () => {
    const wrapper = await mountForm()
    await wrapper.find('input').setValue('   ')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('Ingresá el nombre del establecimiento.')
    expect(createScenario).not.toHaveBeenCalled()
  })

  it('envía el nombre sin espacios y el año elegido', async () => {
    const scenario = { id: 1, name: 'La Aguada', is_main: true }
    vi.mocked(createScenario).mockResolvedValue(scenario)
    const wrapper = await mountForm()

    await wrapper.find('input').setValue('  La Aguada ')
    await wrapper.find('select').setValue('2027')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(createScenario).toHaveBeenCalledWith({
      name: 'La Aguada',
      first_season_start_year: 2027,
    })
    expect(wrapper.emitted('created')).toEqual([[scenario]])
  })

  it('avisa si no se pudo registrar', async () => {
    vi.mocked(createScenario).mockRejectedValue(new Error('Error 500'))
    const wrapper = await mountForm()

    await wrapper.find('input').setValue('La Aguada')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('No se pudo registrar el establecimiento.')
    expect(wrapper.emitted('created')).toBeUndefined()
  })

  it('avisa si no se pudieron cargar los años', async () => {
    vi.mocked(fetchFirstSeasonYears).mockRejectedValue(new Error('Error 500'))
    const wrapper = await mountForm()

    expect(wrapper.text()).toContain('No se pudieron cargar los años de campaña.')
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
  })
})

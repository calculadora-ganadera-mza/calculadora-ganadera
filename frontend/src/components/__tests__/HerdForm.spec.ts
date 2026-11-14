import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import HerdForm from '../HerdForm.vue'
import { ApiError } from '@/api/errors'
import { createHerd, listAnimalCategories, listHerds, updateHerd, type Herd } from '@/api/herds'

// Simula la API: el formulario no le pide nada al backend real
vi.mock('@/api/herds', () => ({
  listAnimalCategories: vi.fn(),
  listHerds: vi.fn(),
  createHerd: vi.fn(),
  updateHerd: vi.fn(),
}))

const category = (id: number, code: string, name: string) => ({
  id,
  code,
  name,
  cow_equivalent: 1,
  summer_water_l_day: 1,
  winter_water_l_day: 1,
})
const CATEGORIES = [
  category(1, 'cow', 'Vaca'),
  category(2, 'bull', 'Toro'),
  category(3, 'heifer', 'Vaquillona'),
  category(4, 'calf', 'Ternero'),
]

const HERD: Herd = {
  id: 9,
  season_id: 5,
  production_unit_id: 3,
  categories: [{ animal_category_id: 1, quantity: 100 }],
  range_condition: 'good',
  replacement_rate: 0.2,
  weaning_rate: 0.65,
  early_weaning: true,
  supplemented: false,
  breeding_start: '2026-11-01',
  breeding_end: '2027-01-31',
}

async function openForm() {
  const wrapper = mount(HerdForm, { props: { seasonId: 5, unitId: 3 } })
  await wrapper.find('button').trigger('click')
  await flushPromises()
  return wrapper
}

const input = (wrapper: ReturnType<typeof mount>, id: string) => wrapper.find(`#${id}`)

beforeEach(() => {
  vi.mocked(listAnimalCategories).mockReset().mockResolvedValue(CATEGORIES)
  vi.mocked(listHerds).mockReset().mockResolvedValue([])
  vi.mocked(createHerd).mockReset()
  vi.mocked(updateHerd).mockReset()
})

describe('HerdForm', () => {
  it('no ofrece terneros y aclara qué son vacas y vaquillonas', async () => {
    const wrapper = await openForm()
    const labels = wrapper
      .findAll('fieldset')[0]!
      .findAll('label')
      .map((l) => l.text())

    expect(labels).toEqual(['Vaca', 'Toro', 'Vaquillona'])
    expect(wrapper.text()).toContain('incluidas las vaquillonas ya entoradas')
    expect(wrapper.text()).toContain('más de un año que todavía no se entoraron')
    expect(wrapper.text()).toContain('Los terneros no se cargan')
  })

  it('carga los datos guardados del sector, con porcentajes', async () => {
    vi.mocked(listHerds).mockResolvedValue([HERD])
    const wrapper = await openForm()

    expect((input(wrapper, 'qty-3-1').element as HTMLInputElement).value).toBe('100')
    expect((input(wrapper, 'weaning-3').element as HTMLInputElement).value).toBe('65')
    expect((input(wrapper, 'replacement-3').element as HTMLInputElement).value).toBe('20')
    expect((input(wrapper, 'breeding-end-3').element as HTMLInputElement).value).toBe('2027-01-31')
  })

  it('si hay vacas exige reposición, destete y entore', async () => {
    const wrapper = await openForm()
    await input(wrapper, 'qty-3-1').setValue(50)
    await input(wrapper, 'range-3').setValue('good')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('Si hay vacas, hacen falta')
    expect(createHerd).not.toHaveBeenCalled()
  })

  it('exige el estado del campo', async () => {
    const wrapper = await openForm()
    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('Elegí el estado del campo.')
  })

  it('crea el rodeo con los porcentajes como fracción', async () => {
    vi.mocked(createHerd).mockResolvedValue(HERD)
    const wrapper = await openForm()

    await input(wrapper, 'qty-3-1').setValue(100)
    await input(wrapper, 'qty-3-2').setValue(4)
    await input(wrapper, 'range-3').setValue('good')
    await input(wrapper, 'replacement-3').setValue(20)
    await input(wrapper, 'weaning-3').setValue(65)
    await input(wrapper, 'breeding-start-3').setValue('2026-11-01')
    await input(wrapper, 'breeding-end-3').setValue('2027-01-31')
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(createHerd).toHaveBeenCalledWith(5, {
      production_unit_id: 3,
      categories: [
        { animal_category_id: 1, quantity: 100 },
        { animal_category_id: 2, quantity: 4 },
      ],
      range_condition: 'good',
      replacement_rate: 0.2,
      weaning_rate: 0.65,
      early_weaning: true,
      supplemented: false,
      breeding_start: '2026-11-01',
      breeding_end: '2027-01-31',
    })
    expect(wrapper.text()).toContain('Datos guardados.')
  })

  it('actualiza el rodeo si el sector ya tenía datos', async () => {
    vi.mocked(listHerds).mockResolvedValue([HERD])
    vi.mocked(updateHerd).mockResolvedValue(HERD)
    const wrapper = await openForm()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(updateHerd).toHaveBeenCalledWith(9, expect.objectContaining({ weaning_rate: 0.65 }))
    expect(createHerd).not.toHaveBeenCalled()
  })

  it('muestra el mensaje del backend', async () => {
    vi.mocked(listHerds).mockResolvedValue([HERD])
    vi.mocked(updateHerd).mockRejectedValue(new ApiError('Hay categorías de animales repetidas.'))
    const wrapper = await openForm()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Hay categorías de animales repetidas.')
  })
})

import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import AdminView from '../AdminView.vue'
import { ApiError } from '@/api/errors'
import { listAnimalCategories } from '@/api/herds'
import { listParameters, updateAnimalCategory, updateParameter } from '@/api/referenceData'

// Simula la API: la pantalla no le pide nada al backend real
vi.mock('@/api/herds', () => ({ listAnimalCategories: vi.fn() }))
vi.mock('@/api/referenceData', () => ({
  listParameters: vi.fn(),
  updateParameter: vi.fn(),
  updateAnimalCategory: vi.fn(),
}))

const PARAMETERS = [
  {
    key: 'early_weaning_index',
    description: 'Índice con destete precoz',
    value: null,
    unit: 'índice',
    producer_editable: false,
  },
  {
    key: 'water_point_radius_km',
    description: 'Alcance de una aguada',
    value: 2.5,
    unit: 'km',
    producer_editable: false,
  },
]
const COW = {
  id: 1,
  code: 'cow',
  name: 'Vaca con cría',
  cow_equivalent: 1,
  summer_water_l_day: 70,
  winter_water_l_day: 37.5,
}

async function mountView() {
  const wrapper = mount(AdminView)
  await flushPromises()
  return wrapper
}

const rowOf = (wrapper: Awaited<ReturnType<typeof mountView>>, text: string) =>
  wrapper.findAll('tbody tr').find((row) => row.text().includes(text))!

beforeEach(() => {
  vi.mocked(listParameters).mockReset().mockResolvedValue(PARAMETERS)
  vi.mocked(listAnimalCategories).mockReset().mockResolvedValue([COW])
  vi.mocked(updateParameter).mockReset()
  vi.mocked(updateAnimalCategory).mockReset()
})

describe('AdminView', () => {
  it('muestra los parámetros y un índice sin cargar queda vacío', async () => {
    const wrapper = await mountView()

    expect(wrapper.text()).toContain('Alcance de una aguada')
    expect((wrapper.find('#param-water_point_radius_km').element as HTMLInputElement).value).toBe(
      '2.5',
    )
    expect((wrapper.find('#param-early_weaning_index').element as HTMLInputElement).value).toBe('')
  })

  it('guarda un parámetro', async () => {
    vi.mocked(updateParameter).mockResolvedValue({ ...PARAMETERS[1]!, value: 3 })
    const wrapper = await mountView()
    const row = rowOf(wrapper, 'Alcance de una aguada')

    await row.find('input').setValue(3)
    await row.find('button').trigger('click')
    await flushPromises()

    expect(updateParameter).toHaveBeenCalledWith('water_point_radius_km', 3)
    expect(row.text()).toContain('Guardado.')
  })

  it('un índice vacío se guarda como null', async () => {
    vi.mocked(updateParameter).mockResolvedValue(PARAMETERS[0]!)
    const wrapper = await mountView()

    await rowOf(wrapper, 'Índice con destete precoz').find('button').trigger('click')
    await flushPromises()

    expect(updateParameter).toHaveBeenCalledWith('early_weaning_index', null)
  })

  it('no manda un valor que no sea mayor que 0', async () => {
    const wrapper = await mountView()
    const row = rowOf(wrapper, 'Alcance de una aguada')

    await row.find('input').setValue(0)
    await row.find('button').trigger('click')

    expect(row.text()).toContain('mayor que 0')
    expect(updateParameter).not.toHaveBeenCalled()
  })

  it('muestra el mensaje del backend', async () => {
    vi.mocked(updateParameter).mockRejectedValue(
      new ApiError('Solo los índices pueden quedar sin valor.'),
    )
    const wrapper = await mountView()
    const row = rowOf(wrapper, 'Alcance de una aguada')

    await row.find('input').setValue('')
    await row.find('button').trigger('click')
    await flushPromises()

    expect(row.text()).toContain('Solo los índices pueden quedar sin valor.')
  })

  it('guarda una categoría con todos sus valores', async () => {
    vi.mocked(updateAnimalCategory).mockResolvedValue({ ...COW, name: 'Vaca' })
    const wrapper = await mountView()
    const row = rowOf(wrapper, 'cow')

    await row.find('input[type="text"]').setValue(' Vaca ')
    await row.find('button').trigger('click')
    await flushPromises()

    expect(updateAnimalCategory).toHaveBeenCalledWith(1, {
      name: 'Vaca',
      cow_equivalent: 1,
      summer_water_l_day: 70,
      winter_water_l_day: 37.5,
    })
    expect(row.text()).toContain('Guardado.')
  })

  it('avisa si el nombre de la categoría ya existe', async () => {
    vi.mocked(updateAnimalCategory).mockRejectedValue(
      new ApiError('Ya existe una categoría con ese nombre.'),
    )
    const wrapper = await mountView()
    const row = rowOf(wrapper, 'cow')

    await row.find('button').trigger('click')
    await flushPromises()

    expect(row.text()).toContain('Ya existe una categoría con ese nombre.')
  })
})

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import MaxBreedingHerd from '../MaxBreedingHerd.vue'

const HERD = {
  cow_equivalents: 6.25,
  categories: [
    { animal_category_id: 1, name: 'Vaca', quantity: 4 },
    { animal_category_id: 2, name: 'Toro', quantity: 1 },
    { animal_category_id: 4, name: 'Ternero de destete', quantity: 1 },
    { animal_category_id: 3, name: 'Vaquillona', quantity: 1 },
  ],
  weaned_calves: { males: 1, females: 1 },
}

const warning = (code: string, message: string) => ({ code, message })

describe('MaxBreedingHerd', () => {
  it('muestra cada categoría, el total en EV y los terneros destetados', () => {
    const wrapper = mount(MaxBreedingHerd, { props: { herd: HERD, warnings: [] } })
    const rows = wrapper.findAll('tbody tr').map((row) => row.text())

    expect(wrapper.get('h2 button').text()).toBe('Rodeo de cría máximo')
    expect(rows).toEqual(['Vaca4', 'Toro1', 'Ternero de destete1', 'Vaquillona1'])
    expect(wrapper.find('tfoot').text()).toContain('6,3 EV')
    expect(wrapper.text()).toContain('Terneros destetados por año: 1 macho y 1 hembra.')
  })

  it('avisa si la reposición pide más terneras que hembras', () => {
    const wrapper = mount(MaxBreedingHerd, {
      props: {
        herd: HERD,
        warnings: [
          warning('missing_index', 'Falta un índice.'),
          warning('replacement_exceeds_females', 'La reposición pide más terneras.'),
        ],
      },
    })

    expect(wrapper.text()).toContain('La reposición pide más terneras.')
    expect(wrapper.text()).not.toContain('Falta un índice.')
  })

  it('si el campo no alcanza, avisa y no muestra el rodeo', () => {
    const wrapper = mount(MaxBreedingHerd, {
      props: {
        herd: null,
        warnings: [warning('herd_does_not_fit', 'El campo no alcanza para una vaca con su toro.')],
      },
    })

    expect(wrapper.text()).toContain('El campo no alcanza para una vaca con su toro.')
    expect(wrapper.find('table').exists()).toBe(false)
  })

  it('sin vacas no muestra nada', () => {
    const wrapper = mount(MaxBreedingHerd, { props: { herd: null, warnings: [] } })

    expect(wrapper.find('section').exists()).toBe(false)
  })
})

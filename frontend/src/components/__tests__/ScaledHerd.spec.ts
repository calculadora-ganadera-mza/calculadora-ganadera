import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import ScaledHerd from '../ScaledHerd.vue'

// El caso del test de la API: 10 vacas y 2 terneras ajustadas hasta 4,2 EV
const HERD = {
  cow_equivalents: 3.25,
  max_cow_equivalents: 4.2,
  categories: [
    { animal_category_id: 1, name: 'Vaca con cría', current_quantity: 10, quantity: 3 },
    { animal_category_id: 4, name: 'Ternero de destete', current_quantity: 2, quantity: 1 },
  ],
}

describe('ScaledHerd', () => {
  it('muestra el rodeo actual, el ajustado y el total en EV', () => {
    const wrapper = mount(ScaledHerd, { props: { herd: HERD, maxHerdCowEquivalents: 4.2 } })
    const rows = wrapper
      .findAll('tbody tr')
      .map((row) => row.findAll('th, td').map((cell) => cell.text()))

    expect(rows).toEqual([
      ['Vaca con cría', '10', '3'],
      ['Ternero de destete', '2', '1'],
    ])
    expect(wrapper.find('tfoot').text()).toContain('3,3 EV')
    expect(wrapper.text()).toContain('Ajustado hasta 4,2 EV')
    expect(wrapper.find('.note').exists()).toBe(false)
  })

  it('aclara cuando el agua lo deja por debajo del rodeo máximo', () => {
    const wrapper = mount(ScaledHerd, { props: { herd: HERD, maxHerdCowEquivalents: 4.334 } })

    expect(wrapper.find('.note').text()).toContain('Queda por debajo del rodeo máximo')
  })

  it('sin rodeo ajustado no muestra nada', () => {
    const wrapper = mount(ScaledHerd, { props: { herd: null, maxHerdCowEquivalents: 4.2 } })

    expect(wrapper.find('section').exists()).toBe(false)
  })
})

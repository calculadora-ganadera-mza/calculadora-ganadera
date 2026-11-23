import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import FarmBreadcrumb from '../FarmBreadcrumb.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/:pathMatch(.*)*', component: {} }],
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('FarmBreadcrumb', () => {
  it('enlaza cada paso salvo el último, aunque dos se llamen igual', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    // Como en las pantallas: primero los nombres provisorios y después los cargados
    const wrapper = mount(FarmBreadcrumb, {
      props: { steps: [{ label: 'Escenario', to: '/farm/7' }, { label: 'Sector' }] },
      global: { plugins: [router] },
    })
    await wrapper.setProps({ steps: [{ label: 'Lote', to: '/farm/7' }, { label: 'Lote' }] })

    expect(wrapper.findAll('a').map((a) => a.attributes('href'))).toEqual(['/farm', '/farm/7'])
    expect(wrapper.get('[aria-current="page"]').text()).toBe('Lote')
    expect(warn).not.toHaveBeenCalled()
  })
})

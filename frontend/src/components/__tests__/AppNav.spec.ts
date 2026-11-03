import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

import AppNav from '../AppNav.vue'
import { routes } from '../../router'

async function mountAt(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  await router.isReady()
  return mount(AppNav, { global: { plugins: [router] } })
}

describe('AppNav', () => {
  it('muestra las cuatro secciones', async () => {
    const wrapper = await mountAt('/')
    const labels = wrapper.findAll('.nav-link').map((link) => link.text())

    expect(labels).toEqual(['Inicio', 'Mi campo', 'Calculadoras', 'Seguimiento'])
  })

  it('marca la sección actual', async () => {
    const wrapper = await mountAt('/farm')
    const active = wrapper.find('.router-link-exact-active')

    expect(active.text()).toBe('Mi campo')
  })
})

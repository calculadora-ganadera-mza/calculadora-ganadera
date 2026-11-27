import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'

import AppNav from '../AppNav.vue'
import { routes } from '../../router'
import { useAuthStore } from '../../stores/auth'

async function mountAt(path: string, role: 'producer' | 'admin' = 'producer') {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = { id: 1, name: 'Ana', email: 'ana@example.com', role, email_verified: true }
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  await router.isReady()
  return mount(AppNav, { global: { plugins: [router, pinia] } })
}

const labels = (wrapper: Awaited<ReturnType<typeof mountAt>>) =>
  wrapper.findAll('.nav-link').map((link) => link.text())

describe('AppNav', () => {
  it('muestra las cuatro secciones a un productor', async () => {
    const wrapper = await mountAt('/')

    expect(labels(wrapper)).toEqual(['Inicio', 'Mi campo', 'Calculadoras', 'Seguimiento'])
  })

  it('suma Administración para un administrador', async () => {
    const wrapper = await mountAt('/', 'admin')

    expect(labels(wrapper)).toEqual([
      'Inicio',
      'Mi campo',
      'Calculadoras',
      'Seguimiento',
      'Administración',
    ])
  })

  it('marca la sección actual', async () => {
    const wrapper = await mountAt('/farm')
    const active = wrapper.find('.router-link-exact-active')

    expect(active.text()).toBe('Mi campo')
  })
})

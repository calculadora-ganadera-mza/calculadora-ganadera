import { afterEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import ServerStatus from '../ServerStatus.vue'

// Simula la respuesta del servidor a /api/health
function mockFetch(response: Promise<Partial<Response>>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => response),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ServerStatus', () => {
  it('avisa que el servidor responde', async () => {
    mockFetch(Promise.resolve({ ok: true, status: 200 }))
    const wrapper = mount(ServerStatus)
    await flushPromises()

    expect(wrapper.text()).toContain('El servidor responde.')
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('avisa cuando el servidor no llega a la base de datos', async () => {
    mockFetch(Promise.resolve({ ok: false, status: 503 }))
    const wrapper = mount(ServerStatus)
    await flushPromises()

    expect(wrapper.text()).toContain('no llega a la base de datos')
  })

  it('avisa cuando no hay conexión y deja reintentar', async () => {
    mockFetch(Promise.reject(new TypeError('Failed to fetch')))
    const wrapper = mount(ServerStatus)
    await flushPromises()

    expect(wrapper.text()).toContain('No hay conexión con el servidor.')

    mockFetch(Promise.resolve({ ok: true, status: 200 }))
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('El servidor responde.')
  })
})

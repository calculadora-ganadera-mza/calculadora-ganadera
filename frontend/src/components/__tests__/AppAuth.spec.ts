import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import App from '../../App.vue'
import router from '../../router'
import { login, logout } from '../../api/auth'

afterEach(() => vi.unstubAllGlobals())

describe('authenticated application', () => {
  it('only shows login to signed-out users and protects direct navigation', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementation(() =>
          Promise.resolve(
            new Response(JSON.stringify({ access_token: 'test-token', token_type: 'bearer' })),
          ),
        ),
    )

    await router.push('/farm')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })
    expect(router.currentRoute.value.path).toBe('/login')
    expect(wrapper.find('.auth-form').exists()).toBe(true)
    expect(wrapper.find('.app-nav').exists()).toBe(false)

    for (const path of ['/', '/calculators', '/tracking', '/unknown']) {
      await router.push(path)
      expect(router.currentRoute.value.path).toBe('/login')
    }

    await login('test@example.com', 'password123')
    await router.push('/')
    await router.push('/login')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/')
    expect(wrapper.find('.app-nav').exists()).toBe(true)
    expect(wrapper.find('.auth-form').exists()).toBe(false)

    await logout()
    await flushPromises()
    expect(wrapper.find('.app-nav').exists()).toBe(false)
    expect(wrapper.find('.auth-form').exists()).toBe(true)
    await router.push('/farm')
    expect(router.currentRoute.value.path).toBe('/login')
    wrapper.unmount()
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { loadRole } from '../users'
import { useAuthStore } from '../../stores/auth'

const me = (role: string) =>
  new Response(JSON.stringify({ id: 1, name: 'Ana', email: 'ana@example.com', role }), {
    status: 200,
  })

beforeEach(() => {
  setActivePinia(createPinia())
  useAuthStore().accessToken = 'token'
})
afterEach(() => vi.unstubAllGlobals())

describe('loadRole', () => {
  it('guarda el rol de /auth/me', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(me('admin')))

    await loadRole()

    expect(useAuthStore().isAdmin).toBe(true)
  })

  it('si no puede leerlo, lo trata como productor', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await loadRole()

    expect(useAuthStore().role).toBe('producer')
  })

  it('al cerrar la sesión el rol se borra', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(me('admin')))
    await loadRole()

    useAuthStore().accessToken = null
    await Promise.resolve()

    expect(useAuthStore().role).toBeNull()
  })
})

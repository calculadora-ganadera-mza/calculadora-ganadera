import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../../stores/auth'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const tokenResponse = (token: string) =>
  new Response(
    JSON.stringify({
      access_token: token,
      token_type: 'bearer',
    }),
    { status: 200 },
  )

beforeEach(() => {
  setActivePinia(createPinia())
})
afterEach(() => vi.unstubAllGlobals())

describe('cliente de autenticación', () => {
  it('restaura la sesión y envía el token de acceso', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(tokenResponse('restored'))
      .mockResolvedValueOnce(new Response('{}'))
    vi.stubGlobal('fetch', fetch)
    const auth = await import('../auth')
    expect(await auth.restoreSession()).toBe(true)
    expect(useAuthStore().accessToken).toBe('restored')
    expect(useAuthStore().isAuthenticated).toBe(true)
    await auth.authenticatedFetch('/auth/me')
    expect(fetch.mock.calls[1]![1].headers.get('Authorization')).toBe('Bearer restored')
  })

  it('comparte la renovación entre pedidos fallidos simultáneos y reintenta cada uno una vez', async () => {
    let resolveRefresh!: (response: Response) => void
    const refresh = new Promise<Response>((resolve) => {
      resolveRefresh = resolve
    })
    let calls = 0
    const fetch = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/auth/refresh')) return refresh
      calls++
      return Promise.resolve(new Response('{}', { status: calls <= 2 ? 401 : 200 }))
    })
    vi.stubGlobal('fetch', fetch)
    const auth = await import('../auth')
    const requests = [auth.authenticatedFetch('/one'), auth.authenticatedFetch('/two')]
    await vi.waitFor(() =>
      expect(fetch.mock.calls.filter(([url]) => url.endsWith('/auth/refresh'))).toHaveLength(1),
    )
    resolveRefresh(tokenResponse('new'))
    expect((await Promise.all(requests)).map((response) => response.status)).toEqual([200, 200])
    expect(calls).toBe(4)
  })

  it('pide iniciar sesión cuando falla la renovación, sin reintentar en bucle', async () => {
    const fetch = vi
      .fn()
      .mockImplementation(() => Promise.resolve(new Response('{}', { status: 401 })))
    vi.stubGlobal('fetch', fetch)
    const auth = await import('../auth')
    expect((await auth.authenticatedFetch('/private')).status).toBe(401)
    expect(useAuthStore().authenticationRequired).toBe(true)
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})

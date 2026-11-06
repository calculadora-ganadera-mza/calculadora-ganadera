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

describe('authentication client', () => {
  it('restores a session and sends its bearer token', async () => {
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

  it('shares refresh between concurrent failed requests and retries each once', async () => {
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

  it('requests login when renewal fails without retry loops', async () => {
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

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { loadCurrentUser, resendVerification, verifyEmail } from '../users'
import { ApiError } from '../errors'
import { useAuthStore } from '../../stores/auth'

const me = (role: string) =>
  new Response(
    JSON.stringify({ id: 1, name: 'Ana', email: 'ana@example.com', role, email_verified: false }),
    { status: 200 },
  )

beforeEach(() => {
  setActivePinia(createPinia())
  useAuthStore().accessToken = 'token'
})
afterEach(() => vi.unstubAllGlobals())

describe('loadCurrentUser', () => {
  it('guarda el usuario de /auth/me', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(me('admin')))

    await loadCurrentUser()

    expect(useAuthStore().isAdmin).toBe(true)
    expect(useAuthStore().user?.email_verified).toBe(false)
  })

  it('si no puede leerlo, lo deja sin leer para reintentar', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await loadCurrentUser()

    expect(useAuthStore().user).toBeNull()
    expect(useAuthStore().isAdmin).toBe(false)
  })

  it('en el reintento, si ya puede leerlo, guarda el usuario', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockRejectedValueOnce(new TypeError('Failed to fetch'))
        .mockResolvedValue(me('admin')),
    )

    await loadCurrentUser()
    await loadCurrentUser()

    expect(useAuthStore().isAdmin).toBe(true)
  })

  it('al cerrar la sesión el usuario se borra', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(me('admin')))
    await loadCurrentUser()

    useAuthStore().accessToken = null
    await Promise.resolve()

    expect(useAuthStore().user).toBeNull()
  })
})

describe('verifyEmail', () => {
  it('manda el código por POST', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await verifyEmail('123456')

    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toMatch(/\/auth\/verify-email$/)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ code: '123456' })
  })

  it('convierte el rechazo del código en un ApiError con el mensaje del backend', async () => {
    const body = JSON.stringify({ detail: 'El código no es correcto.' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 422 })))

    await expect(verifyEmail('123456')).rejects.toEqual(new ApiError('El código no es correcto.'))
  })
})

describe('resendVerification', () => {
  it('pide un código nuevo por POST', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 202 }))
    vi.stubGlobal('fetch', fetchMock)

    await resendVerification()

    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toMatch(/\/auth\/resend-verification$/)
    expect(init.method).toBe('POST')
  })

  it('convierte la espera en un ApiError con el mensaje del backend', async () => {
    const body = JSON.stringify({ detail: 'Ya se envió un código hace menos de 60 segundos.' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 429 })))

    await expect(resendVerification()).rejects.toEqual(
      new ApiError('Ya se envió un código hace menos de 60 segundos.'),
    )
  })
})

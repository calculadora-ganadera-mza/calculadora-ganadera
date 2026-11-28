import { responseError } from './errors'
import { useAuthStore } from '../stores/auth'

const API_BASE = '/api'
let pendingRefresh: Promise<boolean> | null = null

interface TokenResponse {
  access_token: string
  token_type: string
}

/** Error de inicio de sesión o de registro, con el código de la respuesta. */
export class AuthError extends Error {
  constructor(
    readonly status: number,
    // Campo que no pasó la validación (422), si el servidor lo dice
    readonly field?: string,
  ) {
    super(`Falló la autenticación (${status})`)
  }
}

async function acceptToken(response: Response): Promise<void> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const field = Array.isArray(body?.detail) ? body.detail[0]?.loc?.at(-1) : undefined
    throw new AuthError(response.status, typeof field === 'string' ? field : undefined)
  }
  const token: TokenResponse = await response.json()
  useAuthStore().accessToken = token.access_token
  useAuthStore().authenticationRequired = false
}

export async function login(email: string, password: string): Promise<void> {
  await acceptToken(
    await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      credentials: 'include',
      body: new URLSearchParams({ username: email, password }),
    }),
  )
}

export async function register(user: {
  name: string
  email: string
  password: string
}): Promise<void> {
  await acceptToken(
    await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(user),
    }),
  )
}

export function restoreSession(): Promise<boolean> {
  if (!pendingRefresh) {
    pendingRefresh = (async () => {
      try {
        await acceptToken(
          await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            credentials: 'include',
            signal: AbortSignal.timeout(10000),
          }),
        )
        return true
      } catch {
        useAuthStore().accessToken = null
        return false
      } finally {
        pendingRefresh = null
      }
    })()
  }
  return pendingRefresh
}

export async function logout(): Promise<void> {
  // Espera la rotación en curso antes de revocar su reemplazo.
  if (pendingRefresh) await pendingRefresh
  const response = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) throw new Error('No se pudo cerrar la sesión. Volver a intentar.')
  useAuthStore().accessToken = null
  useAuthStore().authenticationRequired = false
}

export async function requestPasswordReset(email: string): Promise<void> {
  const response = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!response.ok) throw await responseError(response)
}

export async function resetPassword(data: {
  email: string
  code: string
  password: string
}): Promise<void> {
  const response = await fetch(`${API_BASE}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw await responseError(response)
}

/** Ruta relativa de la API; reintenta una vez y comparte la renovación entre pedidos simultáneos. */
export async function authenticatedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  if (!path.startsWith('/') || path.startsWith('//'))
    throw new Error('Se espera una ruta relativa de la API')
  const send = () => {
    const headers = new Headers(init.headers)
    if (useAuthStore().accessToken)
      headers.set('Authorization', `Bearer ${useAuthStore().accessToken}`)
    return fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'include' })
  }
  const originalToken = useAuthStore().accessToken
  let response = await send()
  if (response.status === 401) {
    // Otro pedido puede haber renovado el token mientras llegaba esta respuesta.
    if (
      (useAuthStore().accessToken && useAuthStore().accessToken !== originalToken) ||
      (await restoreSession())
    ) {
      response = await send()
    }
    if (response.status === 401) {
      useAuthStore().accessToken = null
      useAuthStore().authenticationRequired = true
      window.dispatchEvent(new Event('auth:required'))
    }
  }
  return response
}

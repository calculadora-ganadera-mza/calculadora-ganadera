import { computed, shallowRef } from 'vue'

const API_BASE = '/api'
const accessToken = shallowRef<string | null>(null)
export const isAuthenticated = computed(() => accessToken.value !== null)
export const authenticationRequired = shallowRef(false)
let pendingRefresh: Promise<boolean> | null = null

interface TokenResponse {
  access_token: string
  token_type: string
}

async function acceptToken(response: Response): Promise<void> {
  if (!response.ok) throw new Error(`Authentication failed (${response.status})`)
  const token: TokenResponse = await response.json()
  accessToken.value = token.access_token
  authenticationRequired.value = false
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
        accessToken.value = null
        return false
      } finally {
        pendingRefresh = null
      }
    })()
  }
  return pendingRefresh
}

export async function logout(): Promise<void> {
  // Finish any in-flight rotation before revoking its replacement.
  if (pendingRefresh) await pendingRefresh
  const response = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) throw new Error('Logout failed; please try again')
  accessToken.value = null
  authenticationRequired.value = false
}

/** Relative API path; retries once and shares renewal between concurrent requests. */
export async function authenticatedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Use a relative API path')
  const send = () => {
    const headers = new Headers(init.headers)
    if (accessToken.value) headers.set('Authorization', `Bearer ${accessToken.value}`)
    return fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'include' })
  }
  const originalToken = accessToken.value
  let response = await send()
  if (response.status === 401) {
    // Another request may already have renewed while this response was in flight.
    if ((accessToken.value && accessToken.value !== originalToken) || (await restoreSession())) {
      response = await send()
    }
    if (response.status === 401) {
      accessToken.value = null
      authenticationRequired.value = true
      window.dispatchEvent(new Event('auth:required'))
    }
  }
  return response
}

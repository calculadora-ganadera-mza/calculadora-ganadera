import { authenticatedFetch } from './auth'
import { responseError } from './errors'
import { useAuthStore } from '../stores/auth'

// Tipos según docs/openapi.yaml

export interface CurrentUser {
  id: number
  name: string
  email: string
  role: 'producer' | 'technician' | 'admin'
  email_verified: boolean
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const response = await authenticatedFetch('/auth/me')
  if (!response.ok) throw await responseError(response)
  return response.json()
}

// Guarda el usuario en el store. Si no se puede leer, queda sin leer (null) y se
// vuelve a pedir en la próxima navegación. Mientras tanto no se muestran
// Administración ni el aviso del correo, y la API igual rechaza a quien no es
// administrador.
export async function loadCurrentUser(): Promise<void> {
  try {
    useAuthStore().user = await fetchCurrentUser()
  } catch {
    useAuthStore().user = null
  }
}

// Verifica el correo con el código de 6 dígitos que llegó por correo
export async function verifyEmail(code: string): Promise<void> {
  const response = await authenticatedFetch('/auth/verify-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })
  if (!response.ok) throw await responseError(response)
}

// Pide otro código: el backend lo manda por correo y anula el anterior
export async function resendVerification(): Promise<void> {
  const response = await authenticatedFetch('/auth/resend-verification', { method: 'POST' })
  if (!response.ok) throw await responseError(response)
}

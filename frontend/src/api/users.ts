import { authenticatedFetch } from './auth'
import { responseError } from './errors'
import { useAuthStore, type Role } from '../stores/auth'

// Tipos según docs/openapi.yaml

export interface CurrentUser {
  id: number
  name: string
  email: string
  role: Role
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const response = await authenticatedFetch('/auth/me')
  if (!response.ok) throw await responseError(response)
  return response.json()
}

// Guarda el rol en el store. Si no se puede leer, se trata como productor:
// la API igual rechaza a quien no es administrador.
export async function loadRole(): Promise<void> {
  try {
    useAuthStore().role = (await fetchCurrentUser()).role
  } catch {
    useAuthStore().role = 'producer'
  }
}

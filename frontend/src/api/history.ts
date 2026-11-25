import { authenticatedFetch } from './auth'
import type { HerdQuantity } from './carryingCapacity'
import { responseError } from './errors'

// Tipos según docs/openapi.yaml

export interface HistoryEntry {
  season_id: number
  start_year: number
  // Vacía si el sector no tiene rodeo en esa campaña
  categories: HerdQuantity[]
  // Fracciones entre 0 y 1
  replacement_rate: number | null
  weaning_rate: number | null
  // Lluvia de la campaña anterior, de julio a junio, en mm
  rainfall_mm: number | null
}

// Evolución del sector: una entrada por campaña, ordenadas por año
export async function getUnitHistory(unitId: number): Promise<HistoryEntry[]> {
  const response = await authenticatedFetch(`/production-units/${unitId}/history`)
  if (!response.ok) throw await responseError(response)
  return response.json()
}

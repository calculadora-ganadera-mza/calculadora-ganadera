import { authenticatedFetch } from './auth'
import { responseError } from './errors'
import type { Season } from './scenarios'

// Guarda la lluvia de la campaña anterior, en mm; null la borra
export async function updateSeasonRainfall(
  seasonId: number,
  rainfallMm: number | null,
): Promise<Season> {
  const response = await authenticatedFetch(`/seasons/${seasonId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rainfall_mm: rainfallMm }),
  })
  if (!response.ok) throw await responseError(response)
  return response.json()
}

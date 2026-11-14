import { authenticatedFetch } from './auth'
import type { Position } from './productionUnits'
export interface WaterPointInput {
  name: string
  location: { type: 'Point'; coordinates: Position }
  refill_l_day: number | null
}
export interface WaterPoint extends WaterPointInput {
  id: number
  outside_unit: boolean
}
export async function waterRequest<T>(
  path: string,
  method = 'GET',
  data?: WaterPointInput,
): Promise<T> {
  const response = await authenticatedFetch(path, {
    method,
    ...(data
      ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }
      : {}),
  })
  if (!response.ok) throw new Error('No se pudo completar la operación de aguadas.')
  return response.status === 204 ? (undefined as T) : response.json()
}

import { authenticatedFetch } from './auth'
import type { Position } from './productionUnits'
export interface WaterPointInput {
  shared: boolean
  name: string
  location: { type: 'Point'; coordinates: Position }
  refill_l_day: number | null
}
export interface WaterPoint extends WaterPointInput {
  id: number
  neighbor_unit_ids: number[]
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
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : 'No se pudo completar la operación de aguadas.',
    )
  }
  return response.status === 204 ? (undefined as T) : response.json()
}

export async function confirmSharing(point: WaterPoint): Promise<WaterPoint> {
  if (
    !point.neighbor_unit_ids.length ||
    !window.confirm('¿Esta aguada también abastece a los sectores vecinos?')
  )
    return point
  return waterRequest<WaterPoint>(`/water-points/${point.id}`, 'PUT', {
    name: point.name,
    location: point.location,
    refill_l_day: point.refill_l_day,
    shared: true,
  })
}

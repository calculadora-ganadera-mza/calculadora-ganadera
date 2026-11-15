import { authenticatedFetch } from './auth'
import { responseError } from './errors'
import type { HerdData } from './herds'

// Tipos según docs/openapi.yaml. El agua y los rodeos del resultado se suman
// en las tareas que los calculan.

export interface CarryingCapacityInput extends HerdData {
  rainfall_mm: number
}

export interface CalculationWarning {
  code: string
  message: string
}

export interface CarryingCapacityResult {
  area_ha: number
  usable_area_ha: number
  carrying_capacity_ha_per_cow_equivalent: number
  pasture_limit_cow_equivalents: number
  warnings: CalculationWarning[]
}

// Calcula con la superficie del sector y los datos recibidos, sin guardar
export async function calculateCarryingCapacity(
  unitId: number,
  data: CarryingCapacityInput,
): Promise<CarryingCapacityResult> {
  const response = await authenticatedFetch(`/production-units/${unitId}/carrying-capacity`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw await responseError(response)
  return response.json()
}

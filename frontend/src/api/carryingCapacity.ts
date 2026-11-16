import { authenticatedFetch } from './auth'
import { responseError } from './errors'
import type { HerdData } from './herds'

// Tipos según docs/openapi.yaml. El agua, el rodeo máximo, el rodeo ajustado y
// el termómetro se suman en las tareas que los calculan.

export interface CarryingCapacityInput extends HerdData {
  rainfall_mm: number
  // Si se omite, el backend usa el parámetro bulls_per_100_cows
  bulls_per_100_cows?: number
}

export interface HerdQuantity {
  animal_category_id: number
  name: string
  quantity: number
}

export interface RecommendedHerd {
  cow_equivalents: number
  categories: HerdQuantity[]
  weaned_calves: { males: number; females: number }
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
  // null si no hay vacas o si no entra ni una vaca con su toro
  recommended_herd: RecommendedHerd | null
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

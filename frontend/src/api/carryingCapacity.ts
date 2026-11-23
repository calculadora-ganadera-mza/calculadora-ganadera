import { authenticatedFetch } from './auth'
import { responseError } from './errors'
import type { HerdData } from './herds'

// Tipos según docs/openapi.yaml.

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

export interface ScaledHerdQuantity {
  animal_category_id: number
  name: string
  // Cabezas del rodeo actual y de Mi rodeo ajustado
  current_quantity: number
  quantity: number
}

export interface ScaledHerd {
  cow_equivalents: number
  // Rodeo máximo con la composición del rodeo actual: hasta donde se ajustó
  max_cow_equivalents: number
  categories: ScaledHerdQuantity[]
}

export type LimitedBy = 'pasture' | 'water'

// Si se evaluó, el límite y los litros siempre llegan. Si no se evaluó (sin
// litros cargados o sin vacas), no hay límite, pero puede haber litros.
export type WaterResult = (
  | { evaluated: true; limit_cow_equivalents: number; refill_l_day: number }
  | { evaluated: false; limit_cow_equivalents: null; refill_l_day: number | null }
) & {
  summer_need_l_day: number | null
  winter_need_l_day: number | null
}

export interface LoadThermometer {
  status: 'below' | 'within' | 'above'
  current_cow_equivalents: number
  max_cow_equivalents: number
  below_cow_equivalents: number
}

// Rodeo máximo sin redondear. Sus categorías quedan vacías si no hay vacas.
export interface MaxHerd {
  cow_equivalents: number
  limited_by: LimitedBy
  categories: HerdQuantity[]
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
  water: WaterResult
  max_herd: MaxHerd
  // null si no hay vacas o si no entra ni una vaca con su toro
  recommended_herd: RecommendedHerd | null
  // null si no hay vacas o si no entra ni una vaca con su parte de los demás animales
  scaled_herd: ScaledHerd | null
  load_thermometer: LoadThermometer
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

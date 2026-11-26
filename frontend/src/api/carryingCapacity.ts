import { authenticatedFetch } from './auth'
import { responseError } from './errors'
import type { AnimalCategory, HerdData } from './herds'

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

export interface MaxBreedingHerd {
  cow_equivalents: number
  categories: HerdQuantity[]
  weaned_calves: { males: number; females: number }
}

export interface ScaledHerdQuantity {
  animal_category_id: number
  name: string
  // Cabezas del rodeo actual y de Mi rodeo ajustado al campo
  current_quantity: number
  quantity: number
}

export interface ScaledHerd {
  cow_equivalents: number
  categories: ScaledHerdQuantity[]
}

export type LimitedBy = 'pasture' | 'water'

// Si se evaluó, el límite y los litros siempre llegan. Si no se evaluó (sin
// litros cargados o sin animales), no hay límite, pero puede haber litros.
// Las necesidades faltan si no hay animales cargados.
export type WaterResult = (
  | { evaluated: true; limit_cow_equivalents: number; refill_l_day: number }
  | { evaluated: false; limit_cow_equivalents: null; refill_l_day: number | null }
) & {
  summer_need_l_day: number | null
  winter_need_l_day: number | null
}

// Compara el rodeo actual con el rodeo máximo del resultado
export interface LoadThermometer {
  status: 'below' | 'within' | 'above'
  current_cow_equivalents: number
  below_cow_equivalents: number
}

// Rodeo máximo en EV, sin redondear
export interface MaxHerd {
  cow_equivalents: number
  limited_by: LimitedBy
}

export interface CalculationWarning {
  code: string
  message: string
}

// Índice de corrección: si corresponde aplicarlo y su valor (null si no se cargó)
export interface CorrectionIndex {
  code: 'range_condition' | 'early_weaning' | 'supplementation'
  applies: boolean
  value: number | null
}

// Pasos del cálculo de la receptividad
export interface PastureBreakdown {
  cow_equivalent_dm_intake_kg_year: number
  consumable_forage_kg_ha_year: number
  base_carrying_capacity_ha_per_cow_equivalent: number
  // Estado del campo, destete precoz y suplementación, en ese orden
  indices: CorrectionIndex[]
}

export interface CarryingCapacityResult {
  area_ha: number
  usable_area_ha: number
  carrying_capacity_ha_per_cow_equivalent: number
  pasture_limit_cow_equivalents: number
  pasture_breakdown: PastureBreakdown
  water: WaterResult
  max_herd: MaxHerd
  // null si no hay vacas o si no entra ni una vaca con su toro
  max_breeding_herd: MaxBreedingHerd | null
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

export type CalculationKind = 'result' | 'simulation'

export interface ReferenceValues {
  parameters: Record<string, number | null>
  animal_categories: AnimalCategory[]
}

export interface CarryingCapacityCalculationCreate {
  season_id: number
  kind: CalculationKind
  update_season?: boolean
  input: CarryingCapacityInput
}

export interface CarryingCapacityCalculationSummary {
  id: number
  production_unit_id: number
  season_id: number
  scenario_name: string
  production_unit_name: string
  season_start_date: string
  season_end_date: string
  kind: CalculationKind
  created_at: string
  rainfall_mm: number
  carrying_capacity_ha_per_cow_equivalent: number
  max_herd_cow_equivalents: number
}

export interface CarryingCapacityCalculation {
  id: number
  production_unit_id: number
  season_id: number
  scenario_name: string
  production_unit_name: string
  season_start_date: string
  season_end_date: string
  kind: CalculationKind
  created_at: string
  season_updated: boolean
  input: CarryingCapacityInput
  reference_values: ReferenceValues
  result: CarryingCapacityResult
}

// Historial liviano de todos los cálculos guardados del usuario
export async function listUserCarryingCapacityCalculations(): Promise<
  CarryingCapacityCalculationSummary[]
> {
  const response = await authenticatedFetch('/carrying-capacity-calculations')
  if (!response.ok) throw await responseError(response)
  return response.json()
}

// Vuelve a calcular en el servidor y guarda el resultado o la simulación
export async function saveCarryingCapacityCalculation(
  unitId: number,
  data: CarryingCapacityCalculationCreate,
): Promise<CarryingCapacityCalculation> {
  const response = await authenticatedFetch(
    `/production-units/${unitId}/carrying-capacity-calculations`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    },
  )
  if (!response.ok) throw await responseError(response)
  return response.json()
}

// Consulta un cálculo guardado tal como fue registrado
export async function getCarryingCapacityCalculation(
  calculationId: number,
): Promise<CarryingCapacityCalculation> {
  const response = await authenticatedFetch(`/carrying-capacity-calculations/${calculationId}`)
  if (!response.ok) throw await responseError(response)
  return response.json()
}

// Elimina un cálculo guardado
export async function deleteCarryingCapacityCalculation(calculationId: number): Promise<void> {
  const response = await authenticatedFetch(`/carrying-capacity-calculations/${calculationId}`, {
    method: 'DELETE',
  })
  if (!response.ok) throw await responseError(response)
}

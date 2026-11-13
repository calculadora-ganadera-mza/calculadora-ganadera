import { authenticatedFetch } from './auth'
import { responseError } from './errors'

// Tipos según docs/openapi.yaml

export type RangeCondition = 'fair' | 'good' | 'very_good'

export interface AnimalCategory {
  id: number
  code: string
  name: string
  cow_equivalent: number
  summer_water_l_day: number
  winter_water_l_day: number
}

export interface HerdCategoryInput {
  animal_category_id: number
  quantity: number
}

export interface HerdData {
  categories: HerdCategoryInput[]
  range_condition: RangeCondition
  replacement_rate: number | null
  weaning_rate: number | null
  early_weaning: boolean
  supplemented: boolean
  breeding_start: string | null
  breeding_end: string | null
}

export interface Herd extends HerdData {
  id: number
  season_id: number
  production_unit_id: number
}

async function send<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await authenticatedFetch(path, init)
  if (!response.ok) throw await responseError(response)
  return response.json()
}

function withJson(method: string, data: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }
}

export function listAnimalCategories(): Promise<AnimalCategory[]> {
  return send('/animal-categories')
}

// Rodeos de la campaña, uno por sector que ya tiene datos
export function listHerds(seasonId: number): Promise<Herd[]> {
  return send(`/seasons/${seasonId}/herds`)
}

export function createHerd(
  seasonId: number,
  data: HerdData & { production_unit_id: number },
): Promise<Herd> {
  return send(`/seasons/${seasonId}/herds`, withJson('POST', data))
}

export function updateHerd(id: number, data: HerdData): Promise<Herd> {
  return send(`/herds/${id}`, withJson('PUT', data))
}

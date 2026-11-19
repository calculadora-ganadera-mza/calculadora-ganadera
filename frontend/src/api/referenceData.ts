import { authenticatedFetch } from './auth'
import { responseError } from './errors'
import type { AnimalCategory } from './herds'

// Tipos según docs/openapi.yaml

export interface Parameter {
  key: string
  description: string
  value: number | null
  unit: string
  producer_editable: boolean
}

export type AnimalCategoryUpdate = Partial<
  Pick<AnimalCategory, 'name' | 'cow_equivalent' | 'summer_water_l_day' | 'winter_water_l_day'>
>

async function send<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await authenticatedFetch(path, init)
  if (!response.ok) throw await responseError(response)
  return response.json()
}

function patch(data: unknown): RequestInit {
  return {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }
}

export function listParameters(): Promise<Parameter[]> {
  return send('/parameters')
}

// Solo los índices aceptan null
export function updateParameter(key: string, value: number | null): Promise<Parameter> {
  return send(`/parameters/${encodeURIComponent(key)}`, patch({ value }))
}

export function updateAnimalCategory(
  id: number,
  data: AnimalCategoryUpdate,
): Promise<AnimalCategory> {
  return send(`/animal-categories/${id}`, patch(data))
}

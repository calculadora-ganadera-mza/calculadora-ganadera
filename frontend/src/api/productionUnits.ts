import { authenticatedFetch } from './auth'

// Tipos según docs/openapi.yaml

// Posición GeoJSON: [longitud, latitud]
export type Position = [number, number]

export interface PolygonGeoJSON {
  type: 'Polygon'
  coordinates: Position[][]
}

export interface ProductionUnitInput {
  name: string
  polygon: PolygonGeoJSON
}

export interface ProductionUnit extends ProductionUnitInput {
  id: number
  area_ha: number
  usable_geometry?: { type: 'MultiPolygon'; coordinates: Position[][][] } | null
  usable_area_ha: number
}

/** Error con un mensaje del backend pensado para mostrar al usuario. */
export class ApiError extends Error {}

async function send<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await authenticatedFetch(path, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    // Un detail de texto es un mensaje para el usuario; una lista es un error de formato
    if (typeof body?.detail === 'string') throw new ApiError(body.detail)
    throw new Error(`Error ${response.status}`)
  }
  return response.status === 204 ? (undefined as T) : response.json()
}

function withJson(method: string, data: ProductionUnitInput): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }
}

// Sectores del establecimieto, ordenados por fecha de creación.
export function listProductionUnits(scenarioId: number): Promise<ProductionUnit[]> {
  return send(`/scenarios/${scenarioId}/production-units`)
}

export function createProductionUnit(
  scenarioId: number,
  data: ProductionUnitInput,
): Promise<ProductionUnit> {
  return send(`/scenarios/${scenarioId}/production-units`, withJson('POST', data))
}

export function updateProductionUnit(
  id: number,
  data: ProductionUnitInput,
): Promise<ProductionUnit> {
  return send(`/production-units/${id}`, withJson('PUT', data))
}

// También borra las aguadas y los rodeos del sector
export function deleteProductionUnit(id: number): Promise<void> {
  return send(`/production-units/${id}`, { method: 'DELETE' })
}

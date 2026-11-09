import { authenticatedFetch } from './auth'

// Tipos según docs/openapi.yaml

export interface SeasonYearOption {
  start_year: number
  start_date: string
  end_date: string
}

export interface ScenarioCreate {
  name: string
  first_season_start_year: number
}

export interface Scenario {
  id: number
  name: string
  is_main: boolean
}

export interface Season {
  id: number
  start_year: number
  start_date: string
  end_date: string
  rainfall_mm: number | null
  is_current: boolean
}

async function getJson<T>(path: string): Promise<T> {
  const response = await authenticatedFetch(path)
  if (!response.ok) throw new Error(`Error ${response.status}`)
  return response.json()
}

// Años que se pueden elegir para la primera campaña
export function fetchFirstSeasonYears(): Promise<SeasonYearOption[]> {
  return getJson('/scenarios/first-season-years')
}

// Establecimientos del usuario, ordenados por fecha de creación
export function listScenarios(): Promise<Scenario[]> {
  return getJson('/scenarios')
}

// Campañas de un establecimiento, ordenadas por año
export function listSeasons(scenarioId: number): Promise<Season[]> {
  return getJson(`/scenarios/${scenarioId}/seasons`)
}

// Crea el establecimiento del usuario con su primera campaña
export async function createScenario(data: ScenarioCreate): Promise<Scenario> {
  const response = await authenticatedFetch('/scenarios', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error(`Error ${response.status}`)
  return response.json()
}

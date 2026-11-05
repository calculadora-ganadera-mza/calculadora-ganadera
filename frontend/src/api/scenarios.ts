// En desarrollo, Vite reenvía /api al backend (ver vite.config.ts)
const API_BASE = '/api'

export interface SeasonYearOption {
  start_year: number
  start_date: string
  end_date: string
}

export interface ScenarioCreate {
  name: string
  first_season_year: number
}

export interface ScenarioRead {
  id: number
  name: string
  seasons: { id: number; start_date: string; end_date: string }[]
}

// Años que se pueden elegir para la primera campaña
export async function fetchFirstSeasonYears(): Promise<SeasonYearOption[]> {
  const response = await fetch(`${API_BASE}/scenarios/first-season-years`)
  if (!response.ok) throw new Error(`Error ${response.status}`)
  return response.json()
}

// Crea el establecimiento con su primera campaña.
// Pendiente de la #7: enviar la sesión del usuario.
export async function createScenario(data: ScenarioCreate): Promise<ScenarioRead> {
  const response = await fetch(`${API_BASE}/scenarios`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error(`Error ${response.status}`)
  return response.json()
}

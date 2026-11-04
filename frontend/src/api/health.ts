// En desarrollo, Vite reenvía /api al backend (ver vite.config.ts)
const API_BASE = '/api'

export type HealthStatus = 'ok' | 'database_unavailable' | 'offline'

// Consulta /health: el servidor responde 200 si todo anda y 503 si no llega a la base
export async function fetchHealth(): Promise<HealthStatus> {
  try {
    const response = await fetch(`${API_BASE}/health`)
    if (response.ok) return 'ok'
    if (response.status === 503) return 'database_unavailable'
    return 'offline'
  } catch {
    return 'offline'
  }
}

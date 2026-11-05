// En desarrollo, Vite reenvía /api al backend (ver vite.config.ts)
const API_BASE = '/api'

export type HealthStatus = 'ok' | 'database_unavailable' | 'offline'

// 200: servidor y base disponibles; 503: el servidor no accede a la base
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

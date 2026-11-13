import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { createScenario } from '../scenarios'
import { ApiError } from '../productionUnits'

// Simula la respuesta del backend al registrar un establecimiento
function mockResponse(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })))
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('createScenario', () => {
  const data = { name: 'La Aguada', first_season_start_year: 2030 }

  it('convierte un detail de texto en un ApiError con ese mensaje', async () => {
    mockResponse(422, { detail: 'El año de la primera campaña tiene que ser 2026, 2027 o 2028.' })

    await expect(createScenario(data)).rejects.toEqual(
      new ApiError('El año de la primera campaña tiene que ser 2026, 2027 o 2028.'),
    )
  })

  it('no muestra los errores de formato de FastAPI', async () => {
    mockResponse(422, { detail: [{ loc: ['body', 'name'], msg: 'x', type: 'y' }] })

    const error = await createScenario(data).catch((err) => err)

    expect(error).not.toBeInstanceOf(ApiError)
    expect(error.message).toBe('Error 422')
  })
})

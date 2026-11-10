import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, createProductionUnit, deleteProductionUnit } from '../productionUnits'

const UNIT_INPUT = {
  name: 'Potrero',
  polygon: {
    type: 'Polygon' as const,
    coordinates: [
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 0],
      ] as [number, number][],
    ],
  },
}

const reply = (status: number, body?: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), { status })

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('cliente de sectores', () => {
  it('convierte un detail de texto en un mensaje para el usuario', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply(422, { detail: 'Contorno inválido.' })))

    const request = createProductionUnit(1, UNIT_INPUT)

    await expect(request).rejects.toBeInstanceOf(ApiError)
    await expect(request).rejects.toThrow('Contorno inválido.')
  })

  it('no muestra los errores de formato de FastAPI', async () => {
    const detail = [{ loc: ['body', 'name'], msg: 'Field required', type: 'missing' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply(422, { detail })))

    const error = await createProductionUnit(1, UNIT_INPUT).catch((err: unknown) => err)

    expect(error).not.toBeInstanceOf(ApiError)
    expect(error).toEqual(new Error('Error 422'))
  })

  it('acepta la respuesta vacía al eliminar', async () => {
    const fetch = vi.fn().mockResolvedValue(reply(204))
    vi.stubGlobal('fetch', fetch)

    await expect(deleteProductionUnit(3)).resolves.toBeUndefined()
    expect(fetch.mock.calls[0]![0]).toBe('/api/production-units/3')
    expect(fetch.mock.calls[0]![1].method).toBe('DELETE')
  })
})

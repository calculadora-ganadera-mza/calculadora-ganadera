import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { calculateCarryingCapacity } from '../carryingCapacity'
import { ApiError } from '../errors'

const DATA = {
  categories: [],
  range_condition: 'good' as const,
  replacement_rate: null,
  weaning_rate: null,
  early_weaning: false,
  supplemented: false,
  breeding_start: null,
  breeding_end: null,
  rainfall_mm: 300,
}

const reply = (status: number, body: unknown) => new Response(JSON.stringify(body), { status })

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('calculateCarryingCapacity', () => {
  it('envía los datos al sector y devuelve el resultado', async () => {
    const result = { pasture_limit_cow_equivalents: 65, warnings: [] }
    const fetchMock = vi.fn().mockResolvedValue(reply(200, result))
    vi.stubGlobal('fetch', fetchMock)

    await expect(calculateCarryingCapacity(4, DATA)).resolves.toEqual(result)

    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toContain('/production-units/4/carrying-capacity')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual(DATA)
  })

  it('convierte el aviso del backend en un mensaje para el usuario', async () => {
    const detail = 'El sector no tiene superficie aprovechable.'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply(422, { detail })))

    await expect(calculateCarryingCapacity(4, DATA)).rejects.toEqual(new ApiError(detail))
  })
})

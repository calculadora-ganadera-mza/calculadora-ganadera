import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  calculateCarryingCapacity,
  deleteCarryingCapacityCalculation,
  getCarryingCapacityCalculation,
  listUserCarryingCapacityCalculations,
  saveCarryingCapacityCalculation,
} from '../carryingCapacity'
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

const reply = (status: number, body?: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), { status })

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

describe('carryingCapacity calculations API', () => {
  it('listUserCarryingCapacityCalculations pide el historial liviano del usuario', async () => {
    const items = [{ id: 10, kind: 'result' }]
    const fetchMock = vi.fn().mockResolvedValue(reply(200, items))
    vi.stubGlobal('fetch', fetchMock)

    await expect(listUserCarryingCapacityCalculations()).resolves.toEqual(items)

    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toMatch(/\/carrying-capacity-calculations$/)
    expect(init?.method).toBeUndefined()
  })

  it('saveCarryingCapacityCalculation envía la campaña, el tipo y el input al sector', async () => {
    const payload = { season_id: 12, kind: 'simulation' as const, input: DATA }
    const saved = { id: 15, ...payload }
    const fetchMock = vi.fn().mockResolvedValue(reply(201, saved))
    vi.stubGlobal('fetch', fetchMock)

    await expect(saveCarryingCapacityCalculation(4, payload)).resolves.toEqual(saved)

    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toContain('/production-units/4/carrying-capacity-calculations')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual(payload)
  })

  it('getCarryingCapacityCalculation consulta un cálculo guardado y propaga errores', async () => {
    const saved = { id: 15, kind: 'result' }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(reply(200, saved))
      .mockResolvedValueOnce(reply(404, { detail: 'Cálculo no encontrado.' }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(getCarryingCapacityCalculation(15)).resolves.toEqual(saved)
    expect(fetchMock.mock.calls[0]![0]).toContain('/carrying-capacity-calculations/15')

    await expect(getCarryingCapacityCalculation(99)).rejects.toEqual(
      new ApiError('Cálculo no encontrado.'),
    )
  })

  it('deleteCarryingCapacityCalculation envía DELETE y propaga errores', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(reply(204))
      .mockResolvedValueOnce(reply(404, { detail: 'Cálculo no encontrado.' }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(deleteCarryingCapacityCalculation(15)).resolves.toBeUndefined()
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toContain('/carrying-capacity-calculations/15')
    expect(init.method).toBe('DELETE')

    await expect(deleteCarryingCapacityCalculation(15)).rejects.toEqual(
      new ApiError('Cálculo no encontrado.'),
    )
  })
})

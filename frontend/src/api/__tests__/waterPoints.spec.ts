import { afterEach, describe, expect, it, vi } from 'vitest'
import { confirmSharing, waterRequest, type WaterPoint } from '../waterPoints'
import { authenticatedFetch } from '../auth'
vi.mock('../auth', () => ({ authenticatedFetch: vi.fn() }))
const point: WaterPoint = {
  id: 1,
  name: 'Tanque',
  location: { type: 'Point', coordinates: [-68, -34] },
  refill_l_day: null,
  shared: false,
  neighbor_unit_ids: [2],
}
afterEach(() => vi.restoreAllMocks())
describe('Uso compartido de aguadas', () => {
  it('solo activa shared con confirmación explícita', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response(JSON.stringify({ ...point, shared: true }), { status: 200 }),
    )
    expect((await confirmSharing(point)).shared).toBe(true)
    expect(
      JSON.parse(vi.mocked(authenticatedFetch).mock.calls.slice(-1)[0]![1]!.body as string).shared,
    ).toBe(true)
  })
  it('no pregunta sin vecinos ni modifica si se responde que no', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    expect(await confirmSharing({ ...point, neighbor_unit_ids: [] })).toEqual({
      ...point,
      neighbor_unit_ids: [],
    })
    expect(confirm).not.toHaveBeenCalled()
    expect(await confirmSharing(point)).toBe(point)
  })
  it('conserva el mensaje de validación del backend', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'La aguada está fuera del sector.' }), { status: 422 }),
    )
    await expect(waterRequest('/water-points/1', 'PUT', point)).rejects.toThrow(
      'La aguada está fuera del sector.',
    )
  })
})

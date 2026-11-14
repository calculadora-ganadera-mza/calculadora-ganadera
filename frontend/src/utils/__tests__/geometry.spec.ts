import { describe, it, expect } from 'vitest'
import { containsPosition } from '../geometry'
import type { PolygonGeoJSON } from '@/api/productionUnits'
const polygon: PolygonGeoJSON = {
  type: 'Polygon',
  coordinates: [
    [
      [0, 0],
      [10, 0],
      [10, 10],
      [0, 10],
      [0, 0],
    ],
    [
      [4, 4],
      [6, 4],
      [6, 6],
      [4, 6],
      [4, 4],
    ],
  ],
}
describe('Asignación espacial de aguadas', () => {
  it('incluye interiores y bordes exteriores', () => {
    expect(containsPosition(polygon, [2, 2])).toBe(true)
    expect(containsPosition(polygon, [0, 5])).toBe(true)
  })
  it('excluye exteriores y huecos', () => {
    expect(containsPosition(polygon, [12, 2])).toBe(false)
    expect(containsPosition(polygon, [5, 5])).toBe(false)
    expect(containsPosition(polygon, [4, 5])).toBe(false)
  })
})

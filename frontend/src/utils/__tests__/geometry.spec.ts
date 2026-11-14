import { describe, it, expect } from 'vitest'
import { containsPosition, distanceToPolygon } from '../geometry'
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

it('mide en metros según la latitud y contempla los bordes de huecos', () => {
  const square: PolygonGeoJSON = {
    type: 'Polygon',
    coordinates: [
      [
        [-68.09, -34.58],
        [-68.08, -34.58],
        [-68.08, -34.57],
        [-68.09, -34.57],
        [-68.09, -34.58],
      ],
    ],
  }
  expect(distanceToPolygon(square, [-68.085, -34.58003])).toBeCloseTo(3.328, 2)
  expect(distanceToPolygon(square, [-68.09003, -34.575])).toBeCloseTo(2.753, 2)
  expect(distanceToPolygon(polygon, [4.00001, 5])).toBeLessThan(1.2)
  expect(distanceToPolygon(square, [-68.09, -34.58])).toBe(0)
})

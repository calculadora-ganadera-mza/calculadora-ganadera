import type { PolygonGeoJSON, Position } from '@/api/productionUnits'

// Incluye el borde exterior y excluye los huecos del polígono.
export function containsPosition(polygon: PolygonGeoJSON, point: Position): boolean {
  function ringContains(ring: Position[]): boolean {
    const [x, y] = point
    let inside = false
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [ax, ay] = ring[j]!
      const [bx, by] = ring[i]!
      const cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
      if (
        Math.abs(cross) < 1e-12 &&
        x >= Math.min(ax, bx) &&
        x <= Math.max(ax, bx) &&
        y >= Math.min(ay, by) &&
        y <= Math.max(ay, by)
      )
        return true
      if (ay > y !== by > y && x < ((bx - ax) * (y - ay)) / (by - ay) + ax) inside = !inside
    }
    return inside
  }
  const [outer, ...holes] = polygon.coordinates
  return !!outer && ringContains(outer) && !holes.some(ringContains)
}

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

// Distancia en metros al borde, en un plano tangente WGS84 centrado en el punto.
// Aproximación local para asignar aguadas cercanas; PostGIS valida al guardar.
export function distanceToPolygon(polygon: PolygonGeoJSON, point: Position): number {
  const radians = Math.PI / 180
  const latitude = point[1] * radians
  const eccentricitySquared = 0.00669437999014
  const denominator = Math.sqrt(1 - eccentricitySquared * Math.sin(latitude) ** 2)
  const xScale = (6378137 / denominator) * Math.cos(latitude) * radians
  const yScale = ((6378137 * (1 - eccentricitySquared)) / denominator ** 3) * radians
  let distance = Infinity
  for (const ring of polygon.coordinates) {
    for (let i = 1; i < ring.length; i++) {
      const a = ring[i - 1]!
      const b = ring[i]!
      const ax = (a[0] - point[0]) * xScale
      const ay = (a[1] - point[1]) * yScale
      const dx = (b[0] - a[0]) * xScale
      const dy = (b[1] - a[1]) * yScale
      const lengthSquared = dx * dx + dy * dy
      const t = lengthSquared ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / lengthSquared)) : 0
      distance = Math.min(distance, Math.hypot(ax + t * dx, ay + t * dy))
    }
  }
  return distance
}

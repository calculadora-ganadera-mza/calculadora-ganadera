// Ayudas de las pantallas de Mi campo

// Número de la dirección (escenario, sector o aguada); null si no es un id válido
export function routeId(value: unknown): number | null {
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

// 1234.56 → "1.234,6"
export function hectares(value: number): string {
  return value.toLocaleString('es-AR', { maximumFractionDigits: 1 })
}

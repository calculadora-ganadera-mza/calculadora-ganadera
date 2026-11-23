// "2026-07-01" → "1/7/2026", sin pasar por Date para no correr el día por la zona horaria
export function formatDate(isoDate: string): string {
  const [y, m, d] = isoDate.split('-')
  return `${Number(d)}/${Number(m)}/${y}`
}

// "2026/27", a partir de las fechas de la campaña
export function seasonName(startDate: string, endDate: string): string {
  return `${startDate.slice(0, 4)}/${endDate.slice(2, 4)}`
}

// "2026/27 (del 1/7/2026 al 30/6/2027)"
export function seasonLabel(startDate: string, endDate: string): string {
  return `${seasonName(startDate, endDate)} (del ${formatDate(startDate)} al ${formatDate(endDate)})`
}

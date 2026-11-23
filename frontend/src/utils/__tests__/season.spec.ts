import { describe, expect, it } from 'vitest'
import { formatDate, seasonLabel, seasonName } from '../season'

describe('season', () => {
  it('arma el nombre de la campaña con sus fechas', () => {
    expect(seasonName('2026-07-01', '2027-06-30')).toBe('2026/27')
    // Si la campaña empieza en enero, termina el mismo año
    expect(seasonName('2026-01-01', '2026-12-31')).toBe('2026/26')
  })

  it('agrega las fechas al nombre', () => {
    expect(seasonLabel('2026-07-01', '2027-06-30')).toBe('2026/27 (del 1/7/2026 al 30/6/2027)')
  })

  it('muestra la fecha sin correr el día', () => {
    expect(formatDate('2026-07-01')).toBe('1/7/2026')
  })
})

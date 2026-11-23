import { describe, expect, it } from 'vitest'
import type { Season } from '@/api/scenarios'
import { formatDate, pickSeason, seasonLabel, seasonName } from '../season'

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

const season = (id: number, isCurrent: boolean): Season => ({
  id,
  start_year: 2025,
  start_date: '2025-07-01',
  end_date: '2026-06-30',
  rainfall_mm: null,
  is_current: isCurrent,
})

describe('pickSeason', () => {
  const seasons = [season(11, false), season(12, true)]

  it('elige la campaña pedida, como texto de la dirección o como número', () => {
    expect(pickSeason(seasons, '11')?.id).toBe(11)
    expect(pickSeason(seasons, 11)?.id).toBe(11)
  })

  it('si la pedida no es de la lista, elige la actual', () => {
    for (const value of ['abc', '99', undefined]) {
      expect(pickSeason(seasons, value)?.id).toBe(12)
    }
  })

  it('sin campañas no elige ninguna', () => {
    expect(pickSeason([], '11')).toBeUndefined()
  })
})

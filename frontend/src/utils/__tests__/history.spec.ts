import { describe, expect, it } from 'vitest'
import type { HistoryEntry } from '@/api/history'
import { headCount, historyCategories, percent } from '../history'

const entry = (seasonId: number, categories: HistoryEntry['categories']): HistoryEntry => ({
  season_id: seasonId,
  start_year: 2020 + seasonId,
  categories,
  replacement_rate: null,
  weaning_rate: null,
  rainfall_mm: null,
})

const COW = { animal_category_id: 1, name: 'Vaca' }
const BULL = { animal_category_id: 2, name: 'Toro' }
const HEIFER = { animal_category_id: 3, name: 'Vaquillona' }

describe('historyCategories', () => {
  it('junta las categorías con animales de todas las campañas, en el orden de la tabla', () => {
    const entries = [
      entry(1, [
        { ...BULL, quantity: 3 },
        { ...HEIFER, quantity: 0 },
      ]),
      entry(2, []),
      entry(3, [{ ...COW, quantity: 80 }]),
    ]

    expect(historyCategories(entries)).toEqual([
      { id: 1, name: 'Vaca' },
      { id: 2, name: 'Toro' },
    ])
  })
})

describe('headCount', () => {
  it('da las cabezas, 0 si la categoría no se cargó y null si no hay rodeo', () => {
    const loaded = entry(1, [{ ...COW, quantity: 80 }])

    expect(headCount(loaded, 1)).toBe(80)
    expect(headCount(loaded, 2)).toBe(0)
    expect(headCount(entry(2, []), 1)).toBeNull()
  })
})

describe('percent', () => {
  it('pasa la fracción a porcentaje redondeado', () => {
    expect(percent(0.65)).toBe(65)
    expect(percent(0.204)).toBe(20)
    expect(percent(0)).toBe(0)
    expect(percent(null)).toBeNull()
  })
})

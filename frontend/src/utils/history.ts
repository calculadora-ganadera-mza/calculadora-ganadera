// Ayudas de la pantalla de Seguimiento
import type { HistoryEntry } from '@/api/history'

export interface HistoryCategory {
  id: number
  name: string
}

// Categorías con animales en alguna campaña, en el orden de la tabla del servidor
export function historyCategories(entries: HistoryEntry[]): HistoryCategory[] {
  const found = new Map<number, string>()
  for (const entry of entries)
    for (const item of entry.categories)
      if (item.quantity > 0) found.set(item.animal_category_id, item.name)
  return [...found].sort(([a], [b]) => a - b).map(([id, name]) => ({ id, name }))
}

// Cabezas de la categoría en la campaña; null si el sector no tiene rodeo en ella
export function headCount(entry: HistoryEntry, categoryId: number): number | null {
  if (!entry.categories.length) return null
  return entry.categories.find((item) => item.animal_category_id === categoryId)?.quantity ?? 0
}

// 0.65 → 65
export function percent(rate: number | null): number | null {
  return rate === null ? null : Math.round(rate * 100)
}

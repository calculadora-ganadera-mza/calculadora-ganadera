// Ayudas para mostrar los datos del rodeo de una campaña
import type { AnimalCategory, HerdData, RangeCondition } from '@/api/herds'

export const RANGE_CONDITION_LABELS: Record<RangeCondition, string> = {
  fair: 'Regular',
  good: 'Bueno',
  very_good: 'Muy bueno',
}

// Categorías cargadas con más de 0 cabezas, con su nombre, en el orden de la tabla
export function loadedAnimals(herd: HerdData, categories: AnimalCategory[]) {
  return categories.flatMap((category) => {
    const quantity =
      herd.categories.find((item) => item.animal_category_id === category.id)?.quantity ?? 0
    return quantity > 0 ? [{ id: category.id, name: category.name, quantity }] : []
  })
}

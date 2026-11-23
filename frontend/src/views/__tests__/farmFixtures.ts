// Datos y montaje comunes de las pruebas de Mi campo
import { flushPromises, mount } from '@vue/test-utils'
import type { Component } from 'vue'
import { createMemoryHistory, createRouter, RouterView, type RouteRecordRaw } from 'vue-router'
import { routes } from '@/router'

export const SCENARIO = { id: 7, name: 'La Aguada', is_main: true }

export const season = (id: number, startYear: number, isCurrent = false) => ({
  id,
  start_year: startYear,
  start_date: `${startYear}-07-01`,
  end_date: `${startYear + 1}-06-30`,
  rainfall_mm: null,
  is_current: isCurrent,
})

export const NORTH = {
  id: 1,
  name: 'Potrero Norte',
  area_ha: 100,
  usable_area_ha: 60,
  polygon: { type: 'Polygon' as const, coordinates: [] },
}
export const SOUTH = { ...NORTH, id: 2, name: 'Potrero Sur', area_ha: 50, usable_area_ha: 50 }

export const WELL = {
  id: 10,
  production_unit_id: 1,
  name: 'Aguada 1',
  shared: false,
  neighbor_unit_ids: [] as number[],
  location: { type: 'Point' as const, coordinates: [-68, -34] as [number, number] },
  refill_l_day: 4200 as number | null,
}

// Las pantallas se cargan antes para que navegar no dependa de importaciones diferidas
const loadedRoutes = Promise.all(
  routes.map(async (route) =>
    typeof route.component === 'function'
      ? {
          ...route,
          component: (await (route.component as () => Promise<{ default: Component }>)()).default,
        }
      : route,
  ),
)

// Monta la app en una dirección, con las rutas reales y sin el mapa ni el rodeo
export async function openAt(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: (await loadedRoutes) as RouteRecordRaw[],
  })
  await router.push(path)
  const wrapper = mount(RouterView, {
    global: {
      plugins: [router],
      stubs: { UnitsMap: true, HerdForm: true, teleport: true },
    },
  })
  await flushPromises()
  return { router, wrapper }
}

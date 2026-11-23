import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import L from 'leaflet'

import UnitsMap from '../UnitsMap.vue'
import type { Position, ProductionUnit } from '@/api/productionUnits'

// Sector rectangular entre dos esquinas [longitud, latitud]
function unitBetween(id: number, [west, south]: Position, [east, north]: Position): ProductionUnit {
  const ring: Position[] = [
    [west, south],
    [east, south],
    [east, north],
    [west, north],
    [west, south],
  ]
  return {
    id,
    name: `Sector ${id}`,
    area_ha: 100,
    usable_area_ha: 100,
    polygon: { type: 'Polygon', coordinates: [ring] },
  }
}

function spyMap() {
  return { create: vi.spyOn(L, 'map'), fitBounds: vi.spyOn(L.Map.prototype, 'fitBounds') }
}

describe('encuadre y modo de la pantalla', () => {
  let svg: boolean
  let wrapper: VueWrapper | undefined
  let spy: ReturnType<typeof spyMap>

  beforeEach(() => {
    spy = spyMap()
    // jsdom ofrece SVG pero Leaflet no lo detecta.
    svg = L.Browser.svg
    Object.assign(L.Browser, { svg: true })
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    spy.create.mockRestore()
    spy.fitBounds.mockRestore()
    Object.assign(L.Browser, { svg })
  })

  it('al dibujar un sector nuevo se centra en los vecinos', () => {
    const neighbor = unitBetween(1, [-68.5, -34.6], [-68.4, -34.5])
    wrapper = mount(UnitsMap, {
      props: { units: [], referenceUnits: [neighbor], draft: null, editingId: null },
    })

    const bounds = spy.fitBounds.mock.calls[0]![0] as L.LatLngBounds
    expect(bounds.getCenter().lat).toBeCloseTo(-34.55)
    expect(bounds.getCenter().lng).toBeCloseTo(-68.45)
  })

  it('al ubicar una aguada abre listo para marcar el punto', () => {
    wrapper = mount(UnitsMap, {
      props: {
        units: [unitBetween(1, [-68.5, -34.6], [-68.4, -34.5])],
        draft: null,
        editingId: null,
        readOnly: true,
        waterMode: true,
      },
    })

    const map = spy.create.mock.results[0]!.value as L.Map
    expect(map.pm.globalDrawModeEnabled()).toBe(true)
    expect(map.pm.Draw.getActiveShape()).toBe('Marker')
  })

  it('vuelve a encuadrar el sector cuando cambia su contorno', async () => {
    wrapper = mount(UnitsMap, {
      props: {
        units: [unitBetween(1, [-68.5, -34.6], [-68.4, -34.5])],
        draft: null,
        editingId: null,
      },
    })
    await wrapper.setProps({ units: [unitBetween(1, [-68.5, -34.6], [-68.2, -34.5])] })
    ;(wrapper.vm as unknown as { fitUnits: () => void }).fitUnits()

    const bounds = spy.fitBounds.mock.lastCall![0] as L.LatLngBounds
    expect(bounds.getEast()).toBeCloseTo(-68.2)
  })
})

it('impide cerrar un polígono si el lado de cierre cruza otro lado', () => {
  const createMap = vi.spyOn(L, 'map')
  // jsdom ofrece SVG pero Leaflet no lo detecta.
  const svg = L.Browser.svg
  Object.assign(L.Browser, { svg: true })
  const wrapper = mount(UnitsMap, {
    props: { units: [], draft: null, editingId: null },
  })
  try {
    const map = createMap.mock.results[0]!.value as L.Map
    const start = L.latLng(-34.6, -68.5)
    const east = L.latLng(-34.6, -68.4)
    const northwest = L.latLng(-34.5, -68.5)
    const northeast = L.latLng(-34.5, -68.4)

    const draw = wrapper.get('.leaflet-pm-icon-polygon').element as HTMLElement
    draw.click()
    for (const latlng of [start, east, northwest, northeast, start]) {
      map.fire('click', { latlng })
    }
    expect(wrapper.emitted('draw')).toBeUndefined()
    expect(map.pm.globalDrawModeEnabled()).toBe(true)

    map.pm.disableDraw()
    draw.click()
    for (const latlng of [start, east, northeast, northwest, start]) {
      map.fire('click', { latlng })
    }
    expect(wrapper.emitted('draw')).toHaveLength(1)
  } finally {
    wrapper.unmount()
    createMap.mockRestore()
    Object.assign(L.Browser, { svg })
  }
})

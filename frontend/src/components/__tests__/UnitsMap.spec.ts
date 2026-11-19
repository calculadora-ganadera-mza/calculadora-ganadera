import { expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import L from 'leaflet'

import UnitsMap from '../UnitsMap.vue'

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

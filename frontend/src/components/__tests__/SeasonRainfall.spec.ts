import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import SeasonRainfall from '../SeasonRainfall.vue'
import { updateSeasonRainfall } from '@/api/seasons'

vi.mock('@/api/seasons', () => ({ updateSeasonRainfall: vi.fn() }))

beforeEach(() => {
  vi.mocked(updateSeasonRainfall).mockReset()
})

describe('SeasonRainfall', () => {
  it('guarda la lluvia cargada', async () => {
    const wrapper = mount(SeasonRainfall, { props: { seasonId: 5, rainfallMm: null } })

    await wrapper.find('input').setValue(280)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(updateSeasonRainfall).toHaveBeenCalledWith(5, 280)
    expect(wrapper.text()).toContain('Lluvia guardada.')
  })

  it('sin valor borra la lluvia', async () => {
    const wrapper = mount(SeasonRainfall, { props: { seasonId: 5, rainfallMm: 300 } })

    await wrapper.find('input').setValue('')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(updateSeasonRainfall).toHaveBeenCalledWith(5, null)
  })

  it('no acepta lluvia negativa', async () => {
    const wrapper = mount(SeasonRainfall, { props: { seasonId: 5, rainfallMm: null } })

    await wrapper.find('input').setValue(-3)
    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('no puede ser negativa')
    expect(updateSeasonRainfall).not.toHaveBeenCalled()
  })
})

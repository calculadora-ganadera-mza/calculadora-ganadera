import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import AddSeason from '../AddSeason.vue'
import { ApiError } from '@/api/errors'
import { createSeason } from '@/api/seasons'

vi.mock('@/api/seasons', () => ({ createSeason: vi.fn() }))

const season = (id: number, startYear: number) => ({
  id,
  start_year: startYear,
  start_date: `${startYear}-07-01`,
  end_date: `${startYear + 1}-06-30`,
  rainfall_mm: null,
  is_current: false,
})

beforeEach(() => {
  vi.mocked(createSeason).mockReset()
})

describe('AddSeason', () => {
  it('ofrece el año siguiente a la última campaña', () => {
    const wrapper = mount(AddSeason, {
      props: { scenarioId: 6, seasons: [season(1, 2027), season(2, 2026)] },
    })

    expect(wrapper.find('button').text()).toBe('Agregar campaña 2028/29')
  })

  it('con previous ofrece el año anterior a la primera campaña', async () => {
    vi.mocked(createSeason).mockResolvedValue(season(3, 2025))
    const wrapper = mount(AddSeason, {
      props: { scenarioId: 6, seasons: [season(1, 2027), season(2, 2026)], previous: true },
    })

    expect(wrapper.find('button').text()).toBe('Agregar campaña 2025/26')
    await wrapper.find('button').trigger('click')
    expect(createSeason).toHaveBeenCalledWith(6, 2025)
  })

  it('crea la campaña y avisa', async () => {
    const created = season(3, 2028)
    vi.mocked(createSeason).mockResolvedValue(created)
    const wrapper = mount(AddSeason, { props: { scenarioId: 6, seasons: [season(1, 2027)] } })

    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(createSeason).toHaveBeenCalledWith(6, 2028)
    expect(wrapper.emitted('created')).toEqual([[created]])
  })

  it('muestra el mensaje del backend', async () => {
    vi.mocked(createSeason).mockRejectedValue(
      new ApiError('El establecimiento ya tiene una campaña para ese año.'),
    )
    const wrapper = mount(AddSeason, { props: { scenarioId: 6, seasons: [season(1, 2027)] } })

    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('ya tiene una campaña para ese año')
    expect(wrapper.emitted('created')).toBeUndefined()
  })

  it('sin campañas no muestra nada', () => {
    const wrapper = mount(AddSeason, { props: { scenarioId: 6, seasons: [] } })

    expect(wrapper.find('button').exists()).toBe(false)
  })
})

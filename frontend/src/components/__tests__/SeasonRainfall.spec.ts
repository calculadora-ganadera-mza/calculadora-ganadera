import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

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

  it('avisa la campaña con la lluvia guardada', async () => {
    const saved = {
      id: 5,
      start_year: 2026,
      start_date: '2026-07-01',
      end_date: '2027-06-30',
      rainfall_mm: 280,
      is_current: true,
    }
    vi.mocked(updateSeasonRainfall).mockResolvedValue(saved)
    const wrapper = mount(SeasonRainfall, { props: { seasonId: 5, rainfallMm: null } })

    await wrapper.find('input').setValue(280)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.emitted('saved')).toEqual([[saved]])
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

  describe('desde la calculadora', () => {
    const calculator = {
      unitName: 'Potrero Norte',
      afterSave: { path: '/calc', query: { unit: '1', rainfall: 'saved' } },
      back: { path: '/calc', query: { unit: '1' } },
    }

    async function openFromCalculator() {
      const router = createRouter({
        history: createMemoryHistory(),
        routes: [{ path: '/:any(.*)', component: { render: () => null } }],
      })
      await router.push('/farm/7')
      const wrapper = mount(SeasonRainfall, {
        props: { seasonId: 5, rainfallMm: null, calculator },
        global: { plugins: [router] },
      })
      return { router, wrapper }
    }

    it('avisa para qué sector falta la lluvia y ofrece volver sin guardar', async () => {
      const { wrapper } = await openFromCalculator()

      expect(wrapper.get('.notice').text()).toBe(
        'Falta la lluvia para calcular la receptividad de Potrero Norte. Al guardarla, se vuelve a la calculadora.',
      )
      expect(wrapper.get('button[type="submit"]').text()).toBe('Guardar y volver a la calculadora')
      expect(wrapper.get('a').text()).toBe('Volver sin guardar')
      expect(wrapper.get('a').attributes('href')).toBe('/calc?unit=1')
    })

    it('al guardar vuelve a la calculadora', async () => {
      vi.mocked(updateSeasonRainfall).mockResolvedValue({
        id: 5,
        start_year: 2026,
        start_date: '2026-07-01',
        end_date: '2027-06-30',
        rainfall_mm: 280,
        is_current: true,
      })
      const { router, wrapper } = await openFromCalculator()

      await wrapper.get('input').setValue(280)
      await wrapper.get('form').trigger('submit')
      await flushPromises()

      expect(updateSeasonRainfall).toHaveBeenCalledWith(5, 280)
      expect(router.currentRoute.value.fullPath).toBe('/calc?unit=1&rainfall=saved')
    })

    it('pide una lluvia mayor que 0 antes de volver', async () => {
      const { router, wrapper } = await openFromCalculator()

      for (const value of ['', 0]) {
        await wrapper.get('input').setValue(value)
        await wrapper.get('form').trigger('submit')
        await flushPromises()
        expect(wrapper.get('[role="alert"]').text()).toBe(
          'Para calcular, la lluvia tiene que ser mayor que 0.',
        )
      }
      expect(updateSeasonRainfall).not.toHaveBeenCalled()
      expect(router.currentRoute.value.path).toBe('/farm/7')
    })
  })
})

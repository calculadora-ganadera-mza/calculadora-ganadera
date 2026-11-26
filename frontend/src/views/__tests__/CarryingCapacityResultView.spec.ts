import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import CarryingCapacityResultView from '../CarryingCapacityResultView.vue'
import { calculateCarryingCapacity, type CarryingCapacityResult } from '@/api/carryingCapacity'
import { ApiError } from '@/api/errors'
import { listAnimalCategories, listHerds } from '@/api/herds'
import { listProductionUnits } from '@/api/productionUnits'
import { listScenarios, listSeasons } from '@/api/scenarios'

vi.mock('@/api/scenarios', () => ({ listScenarios: vi.fn(), listSeasons: vi.fn() }))
vi.mock('@/api/productionUnits', () => ({ listProductionUnits: vi.fn() }))
vi.mock('@/api/herds', () => ({ listAnimalCategories: vi.fn(), listHerds: vi.fn() }))
vi.mock('@/api/carryingCapacity', () => ({ calculateCarryingCapacity: vi.fn() }))

const season = {
  id: 12,
  start_year: 2026,
  start_date: '2026-07-01',
  end_date: '2027-06-30',
  rainfall_mm: 300,
  is_current: true,
}
const herd = {
  id: 30,
  season_id: 12,
  production_unit_id: 2,
  categories: [],
  range_condition: 'good' as const,
  replacement_rate: null,
  weaning_rate: null,
  early_weaning: false,
  supplemented: false,
  breeding_start: null,
  breeding_end: null,
}
const result: CarryingCapacityResult = {
  area_ha: 1000,
  usable_area_ha: 981.8,
  carrying_capacity_ha_per_cow_equivalent: 15.1,
  pasture_limit_cow_equivalents: 65.02,
  pasture_breakdown: {
    cow_equivalent_dm_intake_kg_year: 3285,
    consumable_forage_kg_ha_year: 217.8,
    base_carrying_capacity_ha_per_cow_equivalent: 15.08,
    indices: [
      { code: 'range_condition', applies: true, value: null },
      { code: 'early_weaning', applies: false, value: null },
      { code: 'supplementation', applies: true, value: 1.25 },
    ],
  },
  water: {
    evaluated: true,
    limit_cow_equivalents: 60.7,
    refill_l_day: 4200,
    summer_need_l_day: 4500,
    winter_need_l_day: 2400,
  },
  max_herd: { cow_equivalents: 60.7, limited_by: 'water' },
  max_breeding_herd: null,
  scaled_herd: null,
  load_thermometer: {
    status: 'above',
    current_cow_equivalents: 98.4,
    below_cow_equivalents: 54.63,
  },
  warnings: [],
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listScenarios).mockResolvedValue([{ id: 7, name: 'La Esperanza', is_main: true }])
  vi.mocked(listSeasons).mockResolvedValue([season])
  vi.mocked(listProductionUnits).mockResolvedValue([
    {
      id: 2,
      name: 'Sector 1',
      area_ha: 1000,
      usable_area_ha: 981.8,
      refill_l_day: null,
      polygon: { type: 'Polygon', coordinates: [] },
    },
  ])
  vi.mocked(listHerds).mockResolvedValue([herd])
  vi.mocked(listAnimalCategories).mockResolvedValue([
    {
      id: 1,
      code: 'cow',
      name: 'Vaca',
      cow_equivalent: 1,
      summer_water_l_day: 70,
      winter_water_l_day: 40,
    },
    {
      id: 2,
      code: 'bull',
      name: 'Toro',
      cow_equivalent: 1.3,
      summer_water_l_day: 65,
      winter_water_l_day: 40,
    },
  ])
  vi.mocked(calculateCarryingCapacity).mockResolvedValue(result)
})

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/calc/:scenarioId/:unitId/:seasonId', component: CarryingCapacityResultView },
      { path: '/farm/:scenarioId', name: 'scenario', component: {} },
      { path: '/farm/:scenarioId/sectors/:unitId', name: 'sector', component: {} },
      { path: '/:other(.*)', component: {} },
    ],
  })
  await router.push('/calc/7/2/12')
  const wrapper = mount(RouterView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

// Celdas de cada fila de la tabla del agua
function waterRows(wrapper: Awaited<ReturnType<typeof open>>) {
  return wrapper
    .findAll('.water-need tbody tr')
    .map((row) => row.findAll('th, td').map((cell) => cell.text()))
}

describe('Resultado de receptividad', () => {
  it('calcula con el rodeo y la lluvia de la campaña y muestra los límites y el rodeo máximo', async () => {
    const wrapper = await open()

    expect(calculateCarryingCapacity).toHaveBeenCalledWith(2, { ...herd, rainfall_mm: 300 })
    expect(wrapper.find('.subtitle').text()).toContain('La Esperanza · Sector 1 · campaña 2026/27')
    const sector = wrapper.findAll('a').find((a) => a.text() === 'ver sector')!
    expect(sector.attributes('href')).toBe('/farm/7/sectors/2?season=12')
    expect(wrapper.findAll('.kpi .value').map((value) => value.text())).toEqual([
      '15,1 ha/EV',
      '65,0 EV',
      '60,7 EV',
      '60,7 EV',
    ])
    expect(wrapper.findAll('.kpi .sub').map((sub) => sub.text())).toEqual([
      '300 mm de lluvia',
      '981,8 ha aprovechables',
      '4.200 L/día de reposición',
      'Limita el agua',
    ])
    expect(wrapper.find('.tag.warn').exists()).toBe(false)
  })

  it('marca la receptividad si se calculó sin algún índice', async () => {
    vi.mocked(calculateCarryingCapacity).mockResolvedValue({
      ...result,
      warnings: [
        {
          code: 'missing_index',
          message: 'Falta cargar algún índice de corrección: se calculó sin él.',
        },
      ],
    })

    const wrapper = await open()

    expect(wrapper.find('.tag.warn').text()).toBe('Falta un índice')
    expect(wrapper.find('.kpi').text()).toContain(
      'Falta cargar algún índice de corrección: se calculó sin él.',
    )
  })

  it.each([
    ['below', 40, 'Por debajo', '66 %', 'Menos de 54,6 EV.'],
    ['within', 58.3, 'Dentro', '96 %', 'Entre 54,6 y 60,7 EV, el rodeo máximo.'],
    ['above', 98.4, 'Por encima', '162 %', 'Más de 60,7 EV, el rodeo máximo.'],
  ] as const)(
    'compara el estado %s con el rodeo máximo',
    async (status, current, label, percent, hint) => {
      vi.mocked(calculateCarryingCapacity).mockResolvedValue({
        ...result,
        load_thermometer: { ...result.load_thermometer, status, current_cow_equivalents: current },
      })

      const wrapper = await open()
      const load = wrapper.get('.load')

      expect(load.get('.status').text()).toBe(label)
      expect(load.get('.percent').text()).toBe(`${percent} del rodeo máximo`)
      expect(load.get('.tip').text()).toBe(hint)
      expect(load.get('.line-label').text()).toBe('Rodeo máximo 60,7')
      expect(load.get('[role="meter"]').attributes('aria-valuenow')).toBe(String(current))
    },
  )

  it.each([
    [40, '80', ['0', '20', '40', '60', '80 EV']],
    [98.4, '120', ['0', '30', '60', '90', '120 EV']],
  ] as const)(
    'con %s EV arma el eje del termómetro con números redondos',
    async (current, end, ticks) => {
      vi.mocked(calculateCarryingCapacity).mockResolvedValue({
        ...result,
        load_thermometer: { ...result.load_thermometer, current_cow_equivalents: current },
      })

      const wrapper = await open()
      const meter = wrapper.get('[role="meter"]')

      expect(meter.attributes('aria-valuemax')).toBe(end)
      expect(meter.findAll('.tick').map((tick) => tick.text())).toEqual(ticks)
    },
  )

  it.each([
    [40, ['line-label', 'end']],
    [98.4, ['line-label']],
    [500, ['line-label', 'start']],
  ] as const)(
    'con %s EV ubica la etiqueta del rodeo máximo dentro del gráfico',
    async (current, classes) => {
      vi.mocked(calculateCarryingCapacity).mockResolvedValue({
        ...result,
        load_thermometer: { ...result.load_thermometer, current_cow_equivalents: current },
      })

      const wrapper = await open()

      expect(wrapper.get('.line-label').classes()).toEqual(classes)
    },
  )

  it('compara el agua que necesita el límite por pasto con la que reponen las aguadas', async () => {
    const wrapper = await open()

    expect(waterRows(wrapper)).toEqual([
      ['Verano', '4.500', '4.200', '-300'],
      ['Invierno', '2.400', '4.200', '+1.800'],
    ])
    expect(wrapper.get('.water-need .negative').text()).toBe('-300')
  })

  it('sin animales cargados no estima el agua necesaria', async () => {
    vi.mocked(calculateCarryingCapacity).mockResolvedValue({
      ...result,
      water: {
        evaluated: false,
        limit_cow_equivalents: null,
        refill_l_day: 4200,
        summer_need_l_day: null,
        winter_need_l_day: null,
      },
      max_herd: { cow_equivalents: 65.02, limited_by: 'pasture' },
    })

    const wrapper = await open()

    expect(waterRows(wrapper)).toEqual([
      ['Verano', 'Sin estimación', '4.200', ''],
      ['Invierno', 'Sin estimación', '4.200', ''],
    ])
  })

  it('explica cada término con un tooltip asociado a su botón', async () => {
    const wrapper = await open()
    const buttons = wrapper.findAll('.term button')

    expect(buttons.map((button) => button.text())).toEqual([
      'Receptividad',
      'Límite por pasto',
      'Límite por agua',
      'Rodeo máximo',
      'Por encima',
      'Agua para aprovechar todo el pasto',
    ])
    for (const button of buttons) {
      const tip = wrapper.get(`#${button.attributes('aria-describedby')}`)
      expect(tip.attributes('role')).toBe('tooltip')
    }
  })

  it('muestra que el pasto limita el rodeo máximo', async () => {
    vi.mocked(calculateCarryingCapacity).mockResolvedValue({
      ...result,
      max_herd: { cow_equivalents: 65.02, limited_by: 'pasture' },
    })

    const wrapper = await open()
    const max = wrapper.get('.kpi.max')

    expect(max.get('.value').text()).toBe('65,0 EV')
    expect(max.get('.tag').text()).toBe('Limita el pasto')
  })

  it('aclara en el límite por agua por qué no se evaluó', async () => {
    const message = 'Ninguna aguada tiene litros cargados: no se evaluó el agua.'
    vi.mocked(calculateCarryingCapacity).mockResolvedValue({
      ...result,
      water: { ...result.water, evaluated: false, limit_cow_equivalents: null, refill_l_day: null },
      max_herd: { cow_equivalents: 65.02, limited_by: 'pasture' },
      warnings: [{ code: 'water_not_evaluated', message }],
    })

    const wrapper = await open()
    const water = wrapper.findAll('.kpi')[2]!

    expect(water.get('.value').text()).toBe('Sin evaluar')
    expect(water.get('.sub').text()).toBe(message)
    expect(waterRows(wrapper)).toEqual([
      ['Verano', '4.500', 'Sin datos', ''],
      ['Invierno', '2.400', 'Sin datos', ''],
    ])
  })

  it('marca el límite por agua cuando alguna aguada no tiene litros', async () => {
    const message = 'Algunas aguadas no tienen litros cargados.'
    vi.mocked(calculateCarryingCapacity).mockResolvedValue({
      ...result,
      warnings: [{ code: 'partial_water_data', message }],
    })

    const wrapper = await open()
    const water = wrapper.findAll('.kpi')[2]!

    expect(water.get('.tag.warn').text()).toBe('Datos parciales')
    expect(water.text()).toContain(message)
  })

  it.each([null, 0])('pide la lluvia si es %s, sin calcular', async (rainfall) => {
    vi.mocked(listSeasons).mockResolvedValue([{ ...season, rainfall_mm: rainfall }])

    const wrapper = await open()

    expect(calculateCarryingCapacity).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"] a').attributes('href')).toBe('/farm/7?season=12')
    expect(wrapper.find('[role="alert"]').text()).toContain('falta cargar la lluvia')
    expect(wrapper.find('.simulate-link').exists()).toBe(false)
  })

  it('pide los datos de la campaña si el sector no tiene rodeo', async () => {
    vi.mocked(listHerds).mockResolvedValue([{ ...herd, production_unit_id: 99 }])

    const wrapper = await open()

    expect(calculateCarryingCapacity).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"] a').attributes('href')).toBe('/farm/7/sectors/2?season=12')
    expect(wrapper.find('[role="alert"]').text()).toContain('falta cargar los datos de la campaña')
  })

  it('muestra el aviso del backend cuando no se puede calcular', async () => {
    const detail = 'El sector no tiene superficie aprovechable.'
    vi.mocked(calculateCarryingCapacity).mockRejectedValue(new ApiError(detail))

    const wrapper = await open()

    expect(wrapper.find('[role="alert"]').text()).toContain(detail)
    expect(wrapper.find('.kpis').exists()).toBe(false)
    expect(wrapper.find('.simulate-link').exists()).toBe(false)
  })

  it('muestra los datos usados, cada uno con un enlace para cambiarlo', async () => {
    vi.mocked(listHerds).mockResolvedValue([
      {
        ...herd,
        categories: [
          { animal_category_id: 1, quantity: 80 },
          { animal_category_id: 2, quantity: 3 },
        ],
        replacement_rate: 0.2,
        weaning_rate: 0.65,
        breeding_start: '2026-11-15',
        breeding_end: '2027-01-31',
        supplemented: true,
      },
    ])
    const wrapper = await open()

    const rows = wrapper
      .findAll('.details .data-list > div')
      .map((row) => [row.get('dt').text(), row.get('dd').text()])
    expect(rows).toEqual([
      ['Lluvia de la campaña anterior', '300 mm'],
      ['Estado del campo', 'Bueno'],
      ['Rodeo cargado', 'Vaca 80Toro 3'],
      ['Reposición del rodeo', '20 %'],
      ['Destete', '65 %'],
      ['Inicio del entore', '15/11/2026'],
      ['Destete precoz', 'No'],
      ['Suplementación', 'Sí'],
      ['Superficie aprovechable', '981,8 de 1.000,0 ha'],
      ['Reposición de las aguadas', '4.200 L/día'],
    ])
    const links = wrapper.findAll('.details .data-list a')
    expect(links).toHaveLength(10)
    expect(links[0]!.attributes('href')).toBe('/farm/7?season=12')
    expect(links[0]!.text()).toBe('Cambiar la lluvia')
    expect(links[2]!.attributes('href')).toBe('/farm/7/sectors/2?season=12')
  })

  it('muestra el desglose plegado con el forraje, la receptividad base y cada índice', async () => {
    const wrapper = await open()

    const details = wrapper.get('details.breakdown')
    expect(details.attributes('open')).toBeUndefined()
    expect(details.get('summary').text()).toBe('Desglose del cálculo')
    const cells = details
      .findAll('tr')
      .map((row) => row.findAll('th, td').map((cell) => cell.text()))
    expect(cells).toEqual([
      ['Lluvia de la campaña anterior', '300 mm'],
      ['Forraje consumible', '217,8 kg MS/ha/año'],
      ['Consumo anual de un EV', '3.285 kg MS'],
      ['Base', '15,1 ha/EV'],
      ['Índice por estado del campo (bueno)', 'Sin valor'],
      ['Índice por destete precoz', 'No marcado'],
      ['Índice por suplementación', '1,25'],
      ['Corregida', '15,1 ha/EV'],
      ['Superficie aprovechable', '981,8 ha'],
      ['Límite por pasto', '65,0 EV'],
    ])
  })
})

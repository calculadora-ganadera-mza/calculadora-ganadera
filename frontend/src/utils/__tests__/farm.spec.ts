import { describe, expect, it } from 'vitest'
import { hectares, keepSeason, routeId } from '../farm'

describe('routeId', () => {
  it('acepta solo enteros positivos', () => {
    expect(routeId('7')).toBe(7)
    for (const value of ['0', '-3', '1.5', 'abc', '', undefined]) {
      expect(routeId(value)).toBeNull()
    }
  })
})

describe('hectares', () => {
  it('usa el formato argentino con un decimal como máximo', () => {
    expect(hectares(4614.27)).toBe('4.614,3')
    expect(hectares(150)).toBe('150')
  })
})

describe('keepSeason', () => {
  it('pasa solo la campaña de la dirección', () => {
    expect(keepSeason({ season: '12', scenario: '7' })).toEqual({ season: '12' })
    expect(keepSeason({}).season).toBeUndefined()
  })
})

import { describe, expect, it } from 'vitest'
import { hectares, routeId } from '../farm'

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

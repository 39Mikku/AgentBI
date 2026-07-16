import { describe, expect, it } from 'vitest'
import { initialQuoteIndex, nextQuoteIndex } from './home-quotes'

describe('home quote rotation', () => {
  it('chooses a bounded random starting quote', () => {
    expect(initialQuoteIndex(4, () => 0.99)).toBe(3)
    expect(initialQuoteIndex(0, () => 0.5)).toBe(-1)
  })

  it('cycles back to the first quote', () => {
    expect(nextQuoteIndex(3, 4)).toBe(0)
    expect(nextQuoteIndex(-1, 4)).toBe(0)
    expect(nextQuoteIndex(0, 0)).toBe(-1)
  })
})

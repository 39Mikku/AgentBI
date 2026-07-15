import { describe, expect, it } from 'vitest'

import { autoInputProgress, isAutoInputActive, normalizeTextFile } from './auto-input'


describe('automatic input workbench state', () => {
  it('calculates safe progress values', () => {
    expect(autoInputProgress({ typed_characters: 0, total_characters: 0 })).toBe(0)
    expect(autoInputProgress({ typed_characters: 2, total_characters: 4 })).toBe(50)
    expect(autoInputProgress({ typed_characters: 8, total_characters: 4 })).toBe(100)
  })

  it('identifies countdown and running jobs as active', () => {
    expect(isAutoInputActive('countdown')).toBe(true)
    expect(isAutoInputActive('running')).toBe(true)
    expect(isAutoInputActive('completed')).toBe(false)
    expect(isAutoInputActive('cancelled')).toBe(false)
  })

  it('normalizes imported text file line endings', () => {
    expect(normalizeTextFile('a\r\nb\rc')).toBe('a\nb\nc')
  })
})

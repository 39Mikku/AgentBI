import { describe, expect, it } from 'vitest'

import {
  historySliderToTurns,
  historyTurnsLabel,
  historyTurnsToSlider,
} from './history-context'

describe('Live history context slider', () => {
  it('accelerates toward the right and reserves the endpoint for all history', () => {
    expect(historySliderToTurns(0)).toBe(1)
    expect(historySliderToTurns(100)).toBe(0)
    expect(historySliderToTurns(75)).toBeGreaterThan(historySliderToTurns(50) * 1.5)
  })

  it('round-trips configured turn values to a nearby slider position', () => {
    for (const turns of [1, 5, 12, 25, 50]) {
      const restored = historySliderToTurns(historyTurnsToSlider(turns))
      expect(Math.abs(restored - turns)).toBeLessThanOrEqual(1)
    }
    expect(historyTurnsToSlider(0)).toBe(100)
  })

  it('labels zero as all history', () => {
    expect(historyTurnsLabel(0)).toBe('全部历史')
    expect(historyTurnsLabel(12)).toBe('最近 12 轮')
  })
})

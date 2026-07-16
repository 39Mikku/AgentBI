import { describe, expect, it } from 'vitest'
import { isVideoJobTerminal, normalizeVideoProgress, videoPollDelay } from './video-generation'

describe('video generation job helpers', () => {
  it('recognizes only completed and failed jobs as terminal', () => {
    expect(isVideoJobTerminal('queued')).toBe(false)
    expect(isVideoJobTerminal('in_progress')).toBe(false)
    expect(isVideoJobTerminal('completed')).toBe(true)
    expect(isVideoJobTerminal('failed')).toBe(true)
  })

  it('clamps provider progress for rendering', () => {
    expect(normalizeVideoProgress(-20)).toBe(0)
    expect(normalizeVideoProgress(47.8)).toBe(48)
    expect(normalizeVideoProgress(130)).toBe(100)
    expect(normalizeVideoProgress(undefined)).toBe(0)
  })

  it('polls active generation without a tight loop', () => {
    expect(videoPollDelay('queued')).toBe(3000)
    expect(videoPollDelay('in_progress')).toBe(3000)
    expect(videoPollDelay('completed')).toBeNull()
  })
})

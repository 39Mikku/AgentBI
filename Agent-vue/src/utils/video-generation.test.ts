import { describe, expect, it } from 'vitest'
import {
  isVideoJobTerminal,
  normalizeVideoProgress,
  videoAspectRatioOptions,
  videoDurationOptions,
  videoResolutionOptions,
  videoPollDelay,
} from './video-generation'

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

  it('returns provider-specific video configuration options', () => {
    expect(videoDurationOptions('agnes-video-v2.0')).toEqual([3, 5, 10, 18])
    expect(videoDurationOptions('doubao-seedance-1-0-pro-250528')).toEqual([5, 10])
    expect(videoAspectRatioOptions('agnes-video-v2.0')).not.toContain('adaptive')
    expect(videoAspectRatioOptions('doubao-seedance-1-0-pro-250528')).toContain('21:9')
    expect(videoAspectRatioOptions('doubao-seedance-1-0-pro-250528')).toContain('adaptive')
    expect(videoResolutionOptions('doubao-seedance-1-0-pro-250528')).toEqual(['480p', '720p'])
  })
})

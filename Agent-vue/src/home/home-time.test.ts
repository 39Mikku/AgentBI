import { describe, expect, it } from 'vitest'
import { formatHomeDate, formatRelativeTime, greetingForHour } from './home-time'

describe('home time helpers', () => {
  it('selects a greeting for each part of the day', () => {
    expect(greetingForHour(5)).toBe('清晨好')
    expect(greetingForHour(10)).toBe('上午好')
    expect(greetingForHour(14)).toBe('下午好')
    expect(greetingForHour(19)).toBe('晚上好')
    expect(greetingForHour(2)).toBe('夜深了')
  })

  it('formats the editorial date deterministically', () => {
    expect(formatHomeDate(new Date(2026, 6, 16, 10, 0))).toBe('2026年7月16日 · 星期四')
  })

  it('formats recent activity and hides invalid timestamps', () => {
    const now = new Date(2026, 6, 16, 10, 0)
    expect(formatRelativeTime('2026-07-16T09:55:00', now)).toBe('5 分钟前')
    expect(formatRelativeTime('2026-07-16T08:00:00', now)).toBe('2 小时前')
    expect(formatRelativeTime('not-a-date', now)).toBe('')
  })
})

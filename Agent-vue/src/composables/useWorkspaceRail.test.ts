import { describe, expect, it } from 'vitest'

import { readWorkspaceRailCollapsed, useWorkspaceRail } from './useWorkspaceRail'

function memoryStorage(initial?: string) {
  const values = new Map<string, string>()
  if (initial !== undefined) values.set('agentbi.workspace-rail-collapsed', initial)
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  }
}

describe('workspace rail state', () => {
  it('restores a persisted collapsed rail', () => {
    expect(readWorkspaceRailCollapsed(memoryStorage('true'))).toBe(true)
    expect(readWorkspaceRailCollapsed(memoryStorage('false'))).toBe(false)
  })

  it('toggles and persists the shared workspace preference', () => {
    const storage = memoryStorage()
    const rail = useWorkspaceRail(storage)

    rail.toggleRail()

    expect(rail.railCollapsed.value).toBe(true)
    expect(readWorkspaceRailCollapsed(storage)).toBe(true)
  })

  it('falls back to expanded when browser storage is unavailable', () => {
    const unavailable = {
      getItem: () => { throw new Error('blocked') },
      setItem: () => { throw new Error('blocked') },
    }

    expect(readWorkspaceRailCollapsed(unavailable)).toBe(false)
    expect(() => useWorkspaceRail(unavailable).toggleRail()).not.toThrow()
  })
})

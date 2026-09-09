import { describe, expect, it } from 'vitest'

import {
  PROJECT_AUTHOR,
  PROJECT_LINKS,
  PROJECT_MODULES,
  getNotFoundPrimaryAction,
} from './project-surfaces'

describe('project surfaces content', () => {
  it('keeps the public author signature', () => {
    expect(PROJECT_AUTHOR).toBe('骑士')
  })

  it('presents four main workspaces and keeps Toolbox as a secondary surface', () => {
    expect(PROJECT_MODULES.map((module) => module.name)).toEqual([
      'Studio',
      'Live',
      'Test',
      'Playground',
      'Toolbox',
    ])
    expect(PROJECT_MODULES.find((module) => module.name === 'Playground')?.to).toBe('/playground')
  })

  it('publishes only real project destinations', () => {
    expect(PROJECT_LINKS).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: '官网', href: 'https://agentbi.39miku.tech/', external: true }),
        expect.objectContaining({ label: 'GitHub', href: 'https://github.com/39Mikku/AgentBI', external: true }),
        expect.objectContaining({ label: 'elysiareal.me', href: 'http://elysiareal.me/', external: true }),
      ]),
    )
  })
})

describe('not-found primary action', () => {
  it('returns directly to the local workspace', () => {
    expect(getNotFoundPrimaryAction()).toEqual({ label: '返回工作台', to: '/' })
  })
})

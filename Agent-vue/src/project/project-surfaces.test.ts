import { describe, expect, it } from 'vitest'

import {
  AUTHOR_PARAGRAPHS,
  PROJECT_AUTHOR,
  PROJECT_LINKS,
  PROJECT_MODULES,
  getNotFoundPrimaryAction,
} from './project-surfaces'

describe('project surfaces content', () => {
  it('keeps the public author signature and supplied closing line', () => {
    expect(PROJECT_AUTHOR).toBe('骑士')
    expect(AUTHOR_PARAGRAPHS.at(-1)).toBe('Built for myself, expanded by curiosity.')
  })

  it('presents the four workspaces in product order', () => {
    expect(PROJECT_MODULES.map((module) => module.name)).toEqual([
      'Studio',
      'Live',
      'Test',
      'Toolbox',
    ])
  })

  it('publishes only real project destinations', () => {
    expect(PROJECT_LINKS).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: 'About', href: '/about', external: false }),
        expect.objectContaining({ label: 'GitHub', href: 'https://github.com/39Mikku/AgentBI', external: true }),
        expect.objectContaining({ label: 'elysiareal.me', href: 'http://elysiareal.me/', external: true }),
      ]),
    )
  })
})

describe('not-found primary action', () => {
  it('returns to the workspace for authenticated users', () => {
    expect(getNotFoundPrimaryAction(true)).toEqual({ label: '返回工作台', to: '/home' })
  })

  it('opens login for visitors', () => {
    expect(getNotFoundPrimaryAction(false)).toEqual({ label: '进入 AgentBI', to: '/login' })
  })
})

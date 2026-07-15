import { describe, expect, it } from 'vitest'

import { hasRoleAvatar } from '@/live/role-presentation'

describe('LiveAvatarCore presentation', () => {
  it('keeps the main sound field text-free when no avatar is configured', () => {
    expect(hasRoleAvatar(null)).toBe(false)
    expect(hasRoleAvatar('')).toBe(false)
  })

  it('shows the configured avatar in the main sound field', () => {
    expect(hasRoleAvatar('data:image/png;base64,AA==')).toBe(true)
  })
})

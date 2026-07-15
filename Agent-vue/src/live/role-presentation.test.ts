import { describe, expect, it } from 'vitest'

import { roleInitials, resolvedVoice, voiceLabel } from './role-presentation'

describe('Live role presentation', () => {
  it('builds compact initials for Chinese and Latin role names', () => {
    expect(roleInitials('星野')).toBe('星野')
    expect(roleInitials('Nova Guide')).toBe('NG')
    expect(roleInitials('  ')).toBe('AI')
  })

  it('keeps a custom voice id instead of forcing a built-in voice', () => {
    expect(resolvedVoice('longanqian', '')).toBe('longanqian')
    expect(resolvedVoice('longanqian', 'cosyvoice-v3-plus-demo')).toBe('cosyvoice-v3-plus-demo')
    expect(voiceLabel('cosyvoice-v3-plus-demo')).toBe('自定义音色')
  })
})

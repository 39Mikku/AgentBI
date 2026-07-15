import { describe, expect, it } from 'vitest'

import type { TtsCustomVoice } from '@/api/toolbox-tts-types'
import { isLiveVoiceCompatible, roleInitials, resolvedVoice, voiceLabel } from './role-presentation'

const catalog: TtsCustomVoice[] = [{
  id: 'voice-db', user_id: 'alice', provider: 'bailian', display_name: '夜间电台',
  external_voice_id: 'qwen-audio-3.0-realtime-plus-livevoice-001', voice_kind: 'cloned',
  bound_model: 'qwen-audio-3.0-realtime-plus', provider_metadata: { usage: 'live' },
  created_at: '', updated_at: '',
}]

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

  it('shows the saved friendly name and checks exact Live model compatibility', () => {
    const voiceId = 'qwen-audio-3.0-realtime-plus-livevoice-001'
    expect(voiceLabel(voiceId, catalog)).toBe('夜间电台')
    expect(isLiveVoiceCompatible(voiceId, 'qwen-audio-3.0-realtime-plus', catalog)).toBe(true)
    expect(isLiveVoiceCompatible(voiceId, 'qwen-audio-3.0-realtime-flash', catalog)).toBe(false)
    expect(isLiveVoiceCompatible('manual-external-id', 'qwen-audio-3.0-realtime-flash', catalog)).toBe(true)
  })
})

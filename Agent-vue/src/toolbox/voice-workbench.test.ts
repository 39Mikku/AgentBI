import { describe, expect, it, vi } from 'vitest'

import type { TtsCapabilityProvider, TtsCustomVoice, TtsTrackConfig } from '@/api/toolbox-tts-types'
import { availableLiveVoices, availableVoices, generateTracks } from './voice-workbench'


const bailian: TtsCapabilityProvider = {
  id: 'bailian',
  label: '阿里云百炼',
  configured: true,
  missing_configuration: [],
  models: [
    { id: 'cosyvoice-v3.5-plus', label: 'Plus', voice_kinds: ['cloned'] },
    { id: 'cosyvoice-v3.5-flash', label: 'Flash', voice_kinds: ['cloned'] },
  ],
  builtin_voices: [],
  audio_formats: ['mp3', 'wav'],
  parameters: [],
}

const voices: TtsCustomVoice[] = [
  {
    id: 'db-plus', user_id: 'alice', provider: 'bailian', display_name: '电影旁白',
    external_voice_id: 'voice-plus-id', voice_kind: 'cloned', bound_model: 'cosyvoice-v3.5-plus',
    provider_metadata: {}, created_at: '', updated_at: '',
  },
  {
    id: 'db-flash', user_id: 'alice', provider: 'bailian', display_name: '快速女声',
    external_voice_id: 'voice-flash-id', voice_kind: 'cloned', bound_model: 'cosyvoice-v3.5-flash',
    provider_metadata: {}, created_at: '', updated_at: '',
  },
]

const liveVoices: TtsCustomVoice[] = [
  {
    id: 'live-plus', user_id: 'alice', provider: 'bailian', display_name: 'Live 旁白',
    external_voice_id: 'qwen-audio-3.0-realtime-plus-livevoice-1', voice_kind: 'cloned',
    bound_model: 'qwen-audio-3.0-realtime-plus', provider_metadata: { usage: 'live' },
    created_at: '', updated_at: '',
  },
  {
    id: 'live-flash', user_id: 'alice', provider: 'bailian', display_name: 'Live 快速',
    external_voice_id: 'qwen-audio-3.0-realtime-flash-livevoice-2', voice_kind: 'cloned',
    bound_model: 'qwen-audio-3.0-realtime-flash', provider_metadata: { usage: 'live' },
    created_at: '', updated_at: '',
  },
  {
    ...voices[0]!, id: 'not-live', provider_metadata: {},
  },
]

const track = (id: string): TtsTrackConfig => ({
  id,
  provider: 'bailian',
  model: 'cosyvoice-v3.5-plus',
  voice_id: 'voice-plus-id',
  audio_format: 'mp3',
  parameters: {},
})

describe('voice workbench runtime', () => {
  it('filters Live catalog voices by exact model and maps friendly names to remote ids', () => {
    const plus = availableLiveVoices('qwen-audio-3.0-realtime-plus', liveVoices)
    const flash = availableLiveVoices('qwen-audio-3.0-realtime-flash', liveVoices)

    expect(plus).toEqual([{
      key: 'custom:live-plus',
      label: 'Live 旁白',
      value: 'qwen-audio-3.0-realtime-plus-livevoice-1',
      kind: 'cloned',
    }])
    expect(flash).toHaveLength(1)
    expect(flash[0]?.label).toBe('Live 快速')
    expect(flash[0]?.value).toBe('qwen-audio-3.0-realtime-flash-livevoice-2')
  })

  it('shows voice names but returns external ids and respects exact model binding', () => {
    const plus = availableVoices(bailian, 'cosyvoice-v3.5-plus', voices)
    const flash = availableVoices(bailian, 'cosyvoice-v3.5-flash', voices)

    expect(plus).toEqual([{ key: 'custom:db-plus', label: '电影旁白', value: 'voice-plus-id', kind: 'cloned' }])
    expect(flash[0]?.label).toBe('快速女声')
    expect(flash[0]?.value).toBe('voice-flash-id')
  })

  it('generates comparison tracks concurrently and isolates failures', async () => {
    let releaseFirst: (() => void) | undefined
    const firstBlocked = new Promise<void>((resolve) => { releaseFirst = resolve })
    const synthesize = vi.fn(async (value: TtsTrackConfig) => {
      if (value.id === 'a') {
        await firstBlocked
        return { blob: new Blob(['a']), elapsedMs: 31, provider: value.provider, model: value.model }
      }
      throw new Error('MiMo 配额不足')
    })
    const pending = generateTracks([track('a'), track('b')], '同一段文本', synthesize, {
      createObjectURL: (blob) => `blob:${blob.size}`,
      revokeObjectURL: vi.fn(),
    })

    await Promise.resolve()
    expect(synthesize).toHaveBeenCalledTimes(2)
    releaseFirst?.()
    const results = await pending

    expect(results[0]?.status).toBe('success')
    expect(results[0]?.audioUrl).toBe('blob:1')
    expect(results[1]).toMatchObject({ status: 'error', error: 'MiMo 配额不足' })
  })

  it('revokes old temporary audio before replacing a track result', async () => {
    const revokeObjectURL = vi.fn()
    const result = await generateTracks(
      [track('a')],
      '文本',
      async (value) => ({ blob: new Blob(['new']), elapsedMs: 9, provider: value.provider, model: value.model }),
      { createObjectURL: () => 'blob:new', revokeObjectURL },
      [{ trackId: 'a', status: 'success', audioUrl: 'blob:old', elapsedMs: 1 }],
    )

    expect(revokeObjectURL).toHaveBeenCalledWith('blob:old')
    expect(result[0]?.audioUrl).toBe('blob:new')
  })
})

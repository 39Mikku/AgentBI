import type {
  TtsCapabilityProvider,
  TtsCustomVoice,
  TtsSynthesisResponse,
  TtsTrackConfig,
  TtsTrackResult,
  TtsVoiceKind,
} from '@/api/toolbox-tts-types'

export interface SelectableVoice {
  key: string
  label: string
  value: string
  kind: TtsVoiceKind
}

export interface ObjectUrlRuntime {
  createObjectURL(blob: Blob): string
  revokeObjectURL(url: string): void
}

export function availableVoices(
  provider: TtsCapabilityProvider,
  modelId: string,
  customVoices: TtsCustomVoice[],
): SelectableVoice[] {
  const model = provider.models.find((item) => item.id === modelId)
  if (!model) return []
  const builtins = model.voice_kinds.includes('builtin')
    ? provider.builtin_voices.map((voice) => ({
        key: `builtin:${provider.id}:${voice.id}`,
        label: voice.name,
        value: voice.id,
        kind: 'builtin' as const,
      }))
    : []
  const custom = customVoices
    .filter((voice) =>
      voice.provider === provider.id
      && model.voice_kinds.includes(voice.voice_kind)
      && (!voice.bound_model || voice.bound_model === modelId),
    )
    .map((voice) => ({
      key: `custom:${voice.id}`,
      label: voice.display_name,
      value: voice.external_voice_id,
      kind: voice.voice_kind,
    }))
  return [...builtins, ...custom]
}

export function availableLiveVoices(
  modelId: string,
  customVoices: TtsCustomVoice[],
): SelectableVoice[] {
  return customVoices
    .filter((voice) =>
      voice.provider === 'bailian'
      && voice.voice_kind === 'cloned'
      && voice.bound_model === modelId
      && voice.provider_metadata.usage === 'live',
    )
    .map((voice) => ({
      key: `custom:${voice.id}`,
      label: voice.display_name,
      value: voice.external_voice_id,
      kind: voice.voice_kind,
    }))
}

export async function generateTracks(
  tracks: TtsTrackConfig[],
  text: string,
  synthesize: (track: TtsTrackConfig, text: string) => Promise<TtsSynthesisResponse>,
  objectUrls: ObjectUrlRuntime = URL,
  previous: TtsTrackResult[] = [],
  onUpdate?: (result: TtsTrackResult) => void,
): Promise<TtsTrackResult[]> {
  for (const result of previous) {
    if (result.audioUrl) objectUrls.revokeObjectURL(result.audioUrl)
  }
  return Promise.all(tracks.map(async (track): Promise<TtsTrackResult> => {
    let result: TtsTrackResult
    try {
      const response = await synthesize(track, text)
      result = {
        trackId: track.id,
        status: 'success',
        audioUrl: objectUrls.createObjectURL(response.blob),
        elapsedMs: response.elapsedMs,
      }
    } catch (error) {
      result = {
        trackId: track.id,
        status: 'error',
        error: error instanceof Error ? error.message : '语音生成失败',
      }
    }
    onUpdate?.(result)
    return result
  }))
}

export function releaseTrackResults(results: TtsTrackResult[], objectUrls: ObjectUrlRuntime = URL) {
  for (const result of results) {
    if (result.audioUrl) objectUrls.revokeObjectURL(result.audioUrl)
  }
}

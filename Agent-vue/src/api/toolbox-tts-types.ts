export type TtsProviderId = 'minimax' | 'bailian' | 'mimo' | 'volcengine'
export type TtsVoiceKind = 'builtin' | 'cloned'
export type TtsAudioFormat = 'mp3' | 'wav' | 'pcm'

export interface TtsModelOption {
  id: string
  label: string
  voice_kinds: TtsVoiceKind[]
}

export interface TtsBuiltinVoice {
  id: string
  name: string
}

export interface TtsParameterDefinition {
  key: string
  label: string
  type: 'number' | 'select' | 'text'
  default: string | number
  minimum?: number
  maximum?: number
  step?: number
  options?: Array<{ label: string; value: string }>
}

export interface TtsCapabilityProvider {
  id: TtsProviderId
  label: string
  configured: boolean
  missing_configuration: string[]
  models: TtsModelOption[]
  builtin_voices: TtsBuiltinVoice[]
  audio_formats: TtsAudioFormat[]
  parameters: TtsParameterDefinition[]
}

export interface TtsCapabilities {
  providers: TtsCapabilityProvider[]
}

export interface VoiceScriptGeneratePayload {
  user_id: string
  instruction: string
}

export interface VoiceScriptGenerateResponse {
  text: string
  provider_name: string
  model: string
}

export interface TtsCustomVoice {
  id: string
  user_id: string
  provider: TtsProviderId
  display_name: string
  external_voice_id: string
  voice_kind: TtsVoiceKind
  bound_model: string | null
  provider_metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TtsVoiceInput {
  user_id: string
  provider: TtsProviderId
  display_name: string
  external_voice_id: string
  voice_kind: TtsVoiceKind
  bound_model: string | null
  provider_metadata?: Record<string, unknown>
}

export type LiveVoiceTargetModel =
  | 'qwen-audio-3.0-realtime-flash'
  | 'qwen-audio-3.0-realtime-plus'

export interface LiveVoiceEnrollmentPayload {
  user_id: string
  display_name: string
  target_model: LiveVoiceTargetModel
  prefix: string
  audio_url: string
}

export interface TtsTrackConfig {
  id: string
  provider: TtsProviderId
  model: string
  voice_id: string
  audio_format: TtsAudioFormat
  parameters: Record<string, unknown>
}

export interface TtsSynthesisPayload {
  user_id: string
  provider: TtsProviderId
  model: string
  voice_id: string
  text: string
  audio_format: TtsAudioFormat
  parameters: Record<string, unknown>
}

export interface TtsSynthesisResponse {
  blob: Blob
  elapsedMs: number
  provider: TtsProviderId
  model: string
}

export type TtsTrackStatus = 'idle' | 'loading' | 'success' | 'error'

export interface TtsTrackResult {
  trackId: string
  status: TtsTrackStatus
  audioUrl?: string
  elapsedMs?: number
  error?: string
}

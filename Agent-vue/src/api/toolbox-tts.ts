import type {
  LiveVoiceEnrollmentPayload,
  TtsCapabilities,
  TtsCustomVoice,
  TtsSynthesisPayload,
  TtsSynthesisResponse,
  TtsVoiceInput,
  VoiceScriptGeneratePayload,
  VoiceScriptGenerateResponse,
} from './toolbox-tts-types'

const BASE = '/api/toolbox/tts'

async function errorMessage(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null) as { detail?: string } | null
  return payload?.detail || `语音工作台请求失败（HTTP ${response.status}）`
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>
}

export const listTtsCapabilities = () => requestJson<TtsCapabilities>('/capabilities')

export const generateVoiceScript = (payload: VoiceScriptGeneratePayload) =>
  requestJson<VoiceScriptGenerateResponse>('/script/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const listTtsVoices = (userId: string) =>
  requestJson<TtsCustomVoice[]>(`/voices?user_id=${encodeURIComponent(userId)}`)

export const createTtsVoice = (payload: TtsVoiceInput) =>
  requestJson<TtsCustomVoice>('/voices', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const enrollLiveVoice = (payload: LiveVoiceEnrollmentPayload) =>
  requestJson<TtsCustomVoice>('/voices/enroll-live', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const updateTtsVoice = (
  voiceId: string,
  userId: string,
  payload: Partial<Pick<TtsVoiceInput, 'display_name' | 'bound_model' | 'provider_metadata'>>,
) => requestJson<TtsCustomVoice>(`/voices/${encodeURIComponent(voiceId)}?user_id=${encodeURIComponent(userId)}`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
})

export const deleteTtsVoice = (voiceId: string, userId: string) =>
  requestJson<void>(`/voices/${encodeURIComponent(voiceId)}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })

export async function synthesizeTts(payload: TtsSynthesisPayload): Promise<TtsSynthesisResponse> {
  const response = await fetch(`${BASE}/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  return {
    blob: await response.blob(),
    elapsedMs: Number(response.headers.get('X-TTS-Elapsed-Ms') || 0),
    provider: (response.headers.get('X-TTS-Provider') || payload.provider) as TtsSynthesisResponse['provider'],
    model: response.headers.get('X-TTS-Model') || payload.model,
  }
}

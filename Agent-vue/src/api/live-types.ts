export const LIVE_MODELS = [
  'qwen-audio-3.0-realtime-flash',
  'qwen-audio-3.0-realtime-plus',
] as const

export const LIVE_VOICES = [
  'longanqian',
  'longanlingxin',
  'longanlingxi',
  'longanxiaoxin',
  'longanlufeng',
] as const

export type LiveModelId = (typeof LIVE_MODELS)[number]
export type LiveVoiceId = (typeof LIVE_VOICES)[number]

export interface LivePreferences {
  user_id: string
  model: LiveModelId
  voice: LiveVoiceId
  instructions: string
}

export type LiveServerEvent =
  | { type: 'session.ready' }
  | { type: 'state.listening'; item_id?: string }
  | { type: 'state.thinking'; item_id?: string }
  | { type: 'state.speaking' }
  | { type: 'user.transcript.delta'; item_id: string; text: string; stash?: string }
  | { type: 'user.transcript.final'; item_id: string; transcript: string }
  | { type: 'assistant.transcript.delta'; item_id: string; delta: string }
  | { type: 'assistant.transcript.final'; item_id: string; transcript: string }
  | { type: 'response.interrupted' }
  | { type: 'response.completed' }
  | { type: 'session.closed' }
  | {
      type: 'session.error'
      code: string
      message: string
      recoverable: boolean
    }

export interface LiveSessionStart {
  type: 'session.start'
  model: LiveModelId
  voice: LiveVoiceId
  instructions: string
}

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
  history_context_turns: number
  max_history_turns: number
}

export interface LiveRole {
  id: string
  user_id: string
  name: string
  instructions: string
  voice: string
  avatar_data_url: string | null
  memory_enabled: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface LiveRoleMemory {
  user_id: string
  role_id: string
  content: string
  last_message_id: string | null
  updated_at: string | null
}

export interface LiveConversation {
  id: string
  user_id: string
  role_id: string
  title: string
  created_at: string
  updated_at: string
  last_message_at: string
}

export interface LiveMessage {
  id: string
  thread_id: string
  user_id: string
  role_id: string
  item_id: string
  role: 'user' | 'assistant'
  content: string
  status: 'complete' | 'interrupted'
  created_at: string
  updated_at: string
}

export type LiveServerEvent =
  | { type: 'session.ready' }
  | { type: 'state.listening'; item_id?: string }
  | { type: 'state.thinking'; item_id?: string }
  | { type: 'state.speaking' }
  | { type: 'user.transcript.delta'; item_id: string; text: string; stash?: string }
  | {
      type: 'user.transcript.final'
      item_id: string
      transcript: string
      message_id?: string
      conversation_id?: string
      status?: 'complete'
    }
  | { type: 'assistant.transcript.delta'; item_id: string; delta: string }
  | {
      type: 'assistant.transcript.final'
      item_id: string
      transcript: string
      message_id?: string
      conversation_id?: string
      status?: 'complete'
    }
  | {
      type: 'response.interrupted'
      message_id?: string
      conversation_id?: string
      status?: 'interrupted'
    }
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
  role_id: string
  conversation_id: string | null
}

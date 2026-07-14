export interface ProviderProfile {
  id: string
  name: string
  base_url: string
  default_model?: string | null
  available_models: string[]
}

export interface Conversation {
  id: string
  user_id: string
  title: string
  provider_id?: string | null
  model?: string | null
  temperature: number
  context_turns: number
  created_at?: string
  updated_at?: string
  last_message_at?: string
}

export interface ChatMessage {
  id: string
  conversation_id: string
  user_id: string
  role: 'user' | 'assistant'
  content: string
  reasoning_summary?: string | null
  tool_events: Array<Record<string, unknown>>
  timeline?: ChatTimelineEvent[]
  status: 'complete' | 'streaming' | 'error'
  created_at?: string
}

export interface ChatTimelineEvent {
  type: 'delta' | 'reasoning_summary' | 'tool_started' | 'tool_finished'
  content?: string
  tool?: string
}

export interface ChatPreferences {
  providerId?: string
  model?: string
  temperature: number
  contextTurns: number
}

export interface ChatRuntimeContext {
  userName: string
  locale: string
  timezone: string
}

export interface ChatStreamEvent {
  event: string
  data: Record<string, string>
}

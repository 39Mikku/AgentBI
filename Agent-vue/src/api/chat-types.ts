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
  active_message_id?: string | null
  source_thread_id?: string | null
  source_message_id?: string | null
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
  parent_id?: string | null
  sibling_count?: number
  sibling_index?: number
  version_ids?: string[]
  model_snapshot?: Record<string, unknown>
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

export type ChatGenerationPayload = {
  user_id: string
  conversation_id: string
} & Partial<ChatPreferences> & ChatRuntimeContext

export type MessageGenerationPayload = ChatGenerationPayload & {
  message_id: string
}

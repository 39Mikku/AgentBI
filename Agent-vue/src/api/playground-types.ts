import type { ChatMessage, Conversation } from './chat-types'


export type PlaygroundProfileType = 'character' | 'world'
export type PlaygroundPromptSlot =
  | 'system_start'
  | 'system_end'
  | 'after_last_assistant'
  | 'before_latest_user'
  | 'after_latest_user'
export type PlaygroundThinkingLevel = 'off' | 'low' | 'medium' | 'high'
export type PlaygroundStateTemplate = 'adventure' | 'nurturing' | 'romance' | 'custom'
export type PlaygroundStateVariableType = 'text' | 'progress' | 'list'

export interface PlaygroundPreferences {
  providerId?: string
  model?: string
  temperature: number
  contextTurns: number
  thinkingLevel: PlaygroundThinkingLevel
  summaryProviderId?: string
  summaryModel?: string
  summaryTriggerMessages: number
  summaryRetainMessages: number
}

export interface PlaygroundStateVariable {
  key: string
  type: PlaygroundStateVariableType
  label: string
  description?: string
  initial_value?: unknown
  group?: string
  order?: number
  minimum?: number | null
  maximum?: number | null
}

export interface PlaygroundSummarySettings {
  enabled: boolean
  trigger_new_message_count?: number | null
  retain_recent_message_count?: number | null
  provider_id?: string | null
  model?: string | null
  injection_position: PlaygroundPromptSlot
}

export interface PlaygroundStateSettings {
  enabled: boolean
  template: PlaygroundStateTemplate
  variables: PlaygroundStateVariable[]
  update_instructions: string
  injection_position: PlaygroundPromptSlot
}

export interface PlaygroundActionOptionsSettings {
  enabled: boolean
  style_prompt: string
}

export interface PlaygroundTtsSettings {
  enabled: boolean
  auto_play: boolean
  provider?: 'minimax' | 'bailian' | 'mimo' | 'volcengine' | null
  model?: string | null
  voice_id?: string | null
  audio_format: 'mp3' | 'wav' | 'pcm'
  parameters: Record<string, unknown>
}

export interface PlaygroundProfileSettings {
  summary: PlaygroundSummarySettings
  state: PlaygroundStateSettings
  action_options: PlaygroundActionOptionsSettings
  tts: PlaygroundTtsSettings
}

export interface PlaygroundProfile {
  id: string
  user_id: string
  profile_type: PlaygroundProfileType
  name: string
  avatar_attachment_id?: string | null
  background_attachment_id?: string | null
  main_prompt: string
  opening_message: string
  settings: PlaygroundProfileSettings
  created_at: string
  updated_at: string
}

export interface PlaygroundPersona {
  profile_id?: string
  user_id?: string
  name: string
  avatar_attachment_id?: string | null
  identity_text: string
  background: string
  personality: string
  initial_relationship: string
  enabled: boolean
  injection_position: PlaygroundPromptSlot
  updated_at?: string
}

export interface PlaygroundPromptModule {
  id?: string | null
  profile_id?: string
  user_id?: string
  name: string
  content: string
  enabled: boolean
  injection_position: PlaygroundPromptSlot
  sort_order: number
  created_at?: string
  updated_at?: string
}

export interface PlaygroundContextEntry {
  id?: string | null
  profile_id?: string
  user_id?: string
  name: string
  category: string
  content: string
  enabled: boolean
  activation_mode: 'constant' | 'keyword'
  keywords: string[]
  scan_depth: number
  injection_position: PlaygroundPromptSlot
  priority: number
  created_at?: string
  updated_at?: string
}

export interface PlaygroundSummary {
  conversation_id: string
  user_id: string
  content: string
  status: 'idle' | 'pending' | 'running' | 'failed' | 'stale'
  summarized_through_message_id?: string | null
  last_trigger_message_id?: string | null
  trigger_new_message_count: number
  retain_recent_message_count: number
  provider_id?: string | null
  model?: string | null
  injection_position: PlaygroundPromptSlot
  last_error?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface PlaygroundMessageMetadata {
  state_snapshot?: Record<string, unknown> | null
  action_options?: Array<{ text: string }> | null
  structured_errors?: string[]
  matched_context_entry_ids?: string[]
}

export interface PlaygroundMessage extends ChatMessage {
  metadata: PlaygroundMessageMetadata
}

export type PlaygroundConversation = Conversation & {
  workspace_type?: 'playground'
  owner_type?: PlaygroundProfileType
  owner_id?: string
}

export type PlaygroundStreamEventName =
  | 'message_start'
  | 'delta'
  | 'reasoning_summary'
  | 'state_snapshot'
  | 'action_options'
  | 'summary_status'
  | 'conversation_title_updated'
  | 'done'
  | 'error'

export interface PlaygroundStreamEvent {
  event: PlaygroundStreamEventName
  data: Record<string, any>
}

export interface PlaygroundGenerationPayload {
  user_id: string
  conversation_id: string
  profile_id: string
  content?: string
  message_id?: string
}

export type PlaygroundStateTemplates = Record<
  PlaygroundStateTemplate,
  PlaygroundStateVariable[]
>

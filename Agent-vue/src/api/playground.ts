import type { ChatMessage, Conversation } from './chat-types'
import type {
  PlaygroundContextEntry,
  PlaygroundConversation,
  PlaygroundGenerationPayload,
  PlaygroundMessage,
  PlaygroundPersona,
  PlaygroundPreferences,
  PlaygroundProfile,
  PlaygroundProfileType,
  PlaygroundPromptModule,
  PlaygroundStateTemplates,
  PlaygroundStreamEvent,
  PlaygroundSummary,
} from './playground-types'
import { consumePlaygroundSse } from '@/playground/stream-events'


const BASE = '/api/playground'

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) {
    throw new Error(
      (await response.json().catch(() => null))?.detail || `请求失败 (${response.status})`,
    )
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

type StoredPreferences = {
  user_id: string
  provider_id?: string | null
  model?: string | null
  temperature: number
  context_turns: number
  thinking_level: PlaygroundPreferences['thinkingLevel']
  summary_provider_id?: string | null
  summary_model?: string | null
  summary_trigger_messages: number
  summary_retain_messages: number
}

function mapPreferences(value: StoredPreferences): PlaygroundPreferences {
  return {
    providerId: value.provider_id || undefined,
    model: value.model || undefined,
    temperature: value.temperature,
    contextTurns: value.context_turns,
    thinkingLevel: value.thinking_level,
    summaryProviderId: value.summary_provider_id || undefined,
    summaryModel: value.summary_model || undefined,
    summaryTriggerMessages: value.summary_trigger_messages,
    summaryRetainMessages: value.summary_retain_messages,
  }
}

function storedPreferences(value: PlaygroundPreferences) {
  return {
    provider_id: value.providerId || null,
    model: value.model || null,
    temperature: value.temperature,
    context_turns: value.contextTurns,
    thinking_level: value.thinkingLevel,
    summary_provider_id: value.summaryProviderId || null,
    summary_model: value.summaryModel || null,
    summary_trigger_messages: value.summaryTriggerMessages,
    summary_retain_messages: value.summaryRetainMessages,
  }
}

export async function getPlaygroundPreferences(userId: string) {
  return mapPreferences(
    await json<StoredPreferences>(`/preferences?user_id=${encodeURIComponent(userId)}`),
  )
}

export async function savePlaygroundPreferences(
  userId: string,
  preferences: PlaygroundPreferences,
) {
  return mapPreferences(
    await json<StoredPreferences>(
      `/preferences?user_id=${encodeURIComponent(userId)}`,
      jsonInit('PUT', storedPreferences(preferences)),
    ),
  )
}

export async function getPlaygroundStateTemplates() {
  const response = await json<{ templates: PlaygroundStateTemplates }>('/state-templates')
  return response.templates
}

export const listPlaygroundProfiles = (userId: string, type?: PlaygroundProfileType) =>
  json<PlaygroundProfile[]>(
    `/profiles?user_id=${encodeURIComponent(userId)}${type ? `&profile_type=${type}` : ''}`,
  )

export const getPlaygroundProfile = (profileId: string, userId: string) =>
  json<PlaygroundProfile>(`/profiles/${profileId}?user_id=${encodeURIComponent(userId)}`)

export const createPlaygroundProfile = (
  payload: Omit<PlaygroundProfile, 'id' | 'created_at' | 'updated_at'>,
) => json<PlaygroundProfile>('/profiles', jsonInit('POST', payload))

export const updatePlaygroundProfile = (
  profileId: string,
  userId: string,
  payload: Partial<Omit<PlaygroundProfile, 'id' | 'user_id' | 'created_at' | 'updated_at'>>,
) =>
  json<PlaygroundProfile>(
    `/profiles/${profileId}?user_id=${encodeURIComponent(userId)}`,
    jsonInit('PUT', payload),
  )

export const deletePlaygroundProfile = (profileId: string, userId: string) =>
  json<void>(`/profiles/${profileId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })

export const getPlaygroundPersona = (profileId: string, userId: string) =>
  json<PlaygroundPersona | null>(
    `/profiles/${profileId}/persona?user_id=${encodeURIComponent(userId)}`,
  )

export const savePlaygroundPersona = (
  profileId: string,
  userId: string,
  payload: PlaygroundPersona,
) =>
  json<PlaygroundPersona>(
    `/profiles/${profileId}/persona?user_id=${encodeURIComponent(userId)}`,
    jsonInit('PUT', {
      name: payload.name,
      avatar_attachment_id: payload.avatar_attachment_id || null,
      identity_text: payload.identity_text,
      background: payload.background,
      personality: payload.personality,
      initial_relationship: payload.initial_relationship,
      enabled: payload.enabled,
      injection_position: payload.injection_position,
    }),
  )

export const listPlaygroundPromptModules = (profileId: string, userId: string) =>
  json<PlaygroundPromptModule[]>(
    `/profiles/${profileId}/prompt-modules?user_id=${encodeURIComponent(userId)}`,
  )

export const savePlaygroundPromptModules = (
  profileId: string,
  userId: string,
  items: PlaygroundPromptModule[],
) =>
  json<PlaygroundPromptModule[]>(
    `/profiles/${profileId}/prompt-modules?user_id=${encodeURIComponent(userId)}`,
    jsonInit('PUT', {
      items: items.map((item) => ({
        id: item.id || undefined,
        name: item.name,
        content: item.content,
        enabled: item.enabled,
        injection_position: item.injection_position,
        sort_order: item.sort_order,
      })),
    }),
  )

export const listPlaygroundContextEntries = (profileId: string, userId: string) =>
  json<PlaygroundContextEntry[]>(
    `/profiles/${profileId}/context-entries?user_id=${encodeURIComponent(userId)}`,
  )

export const savePlaygroundContextEntries = (
  profileId: string,
  userId: string,
  items: PlaygroundContextEntry[],
) =>
  json<PlaygroundContextEntry[]>(
    `/profiles/${profileId}/context-entries?user_id=${encodeURIComponent(userId)}`,
    jsonInit('PUT', {
      items: items.map((item) => ({
        id: item.id || undefined,
        name: item.name,
        category: item.category,
        content: item.content,
        enabled: item.enabled,
        activation_mode: item.activation_mode,
        keywords: item.keywords,
        scan_depth: item.scan_depth,
        injection_position: item.injection_position,
        priority: item.priority,
      })),
    }),
  )

export const listPlaygroundConversations = (
  userId: string,
  profileId: string,
  profileType: PlaygroundProfileType,
) =>
  json<PlaygroundConversation[]>(
    `/conversations?user_id=${encodeURIComponent(userId)}&profile_id=${encodeURIComponent(profileId)}&profile_type=${profileType}`,
  )

export const createPlaygroundConversation = (
  userId: string,
  profileId: string,
  profileType: PlaygroundProfileType,
  title?: string,
) =>
  json<PlaygroundConversation>(
    '/conversations',
    jsonInit('POST', {
      user_id: userId,
      profile_id: profileId,
      profile_type: profileType,
      title,
    }),
  )

export const updatePlaygroundConversation = (
  conversationId: string,
  userId: string,
  title: string,
) =>
  json<PlaygroundConversation>(
    `/conversations/${conversationId}?user_id=${encodeURIComponent(userId)}`,
    jsonInit('PATCH', { title }),
  )

export const deletePlaygroundConversation = (conversationId: string, userId: string) =>
  json<void>(`/conversations/${conversationId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })

export const listPlaygroundMessages = (conversationId: string, userId: string) =>
  json<PlaygroundMessage[]>(
    `/conversations/${conversationId}/messages?user_id=${encodeURIComponent(userId)}`,
  )

export const setPlaygroundActiveMessage = (
  conversationId: string,
  userId: string,
  messageId: string,
) =>
  json<PlaygroundConversation>(
    `/conversations/${conversationId}/active-message/${messageId}`,
    jsonInit('POST', { user_id: userId }),
  )

export const createPlaygroundBranch = (
  conversationId: string,
  userId: string,
  sourceMessageId: string,
  title?: string,
) =>
  json<PlaygroundConversation>(
    `/conversations/${conversationId}/branches`,
    jsonInit('POST', { user_id: userId, source_message_id: sourceMessageId, title }),
  )

export const editPlaygroundOpeningMessage = (
  conversationId: string,
  userId: string,
  messageId: string,
  content: string,
) =>
  json<PlaygroundMessage>(
    `/conversations/${conversationId}/opening-message`,
    jsonInit('PATCH', { user_id: userId, message_id: messageId, content }),
  )

export const getPlaygroundSummary = (conversationId: string, userId: string) =>
  json<PlaygroundSummary>(
    `/conversations/${conversationId}/summary?user_id=${encodeURIComponent(userId)}`,
  )

export const savePlaygroundSummary = (
  conversationId: string,
  userId: string,
  payload: Partial<PlaygroundSummary>,
) =>
  json<PlaygroundSummary>(
    `/conversations/${conversationId}/summary?user_id=${encodeURIComponent(userId)}`,
    jsonInit('PUT', payload),
  )

export const refreshPlaygroundSummary = (conversationId: string, userId: string) =>
  json<PlaygroundSummary>(
    `/conversations/${conversationId}/summary/refresh?user_id=${encodeURIComponent(userId)}`,
    { method: 'POST' },
  )

async function stream(
  path: string,
  payload: PlaygroundGenerationPayload,
  onEvent: (event: PlaygroundStreamEvent) => void,
  signal?: AbortSignal,
) {
  const response = await fetch(`${BASE}${path}`, {
    ...jsonInit('POST', payload),
    signal,
  })
  if (!response.ok || !response.body) {
    throw new Error((await response.json().catch(() => null))?.detail || '无法开始生成')
  }
  await consumePlaygroundSse(response, onEvent)
}

export const streamPlaygroundChat = (
  payload: PlaygroundGenerationPayload & { content: string },
  onEvent: (event: PlaygroundStreamEvent) => void,
  signal?: AbortSignal,
) => stream('/chat/stream', payload, onEvent, signal)

export const streamPlaygroundRetry = (
  payload: PlaygroundGenerationPayload & { message_id: string },
  onEvent: (event: PlaygroundStreamEvent) => void,
  signal?: AbortSignal,
) =>
  stream(
    `/conversations/${payload.conversation_id}/messages/${payload.message_id}/retry`,
    payload,
    onEvent,
    signal,
  )

export const streamPlaygroundEdit = (
  payload: PlaygroundGenerationPayload & { message_id: string; content: string },
  onEvent: (event: PlaygroundStreamEvent) => void,
  signal?: AbortSignal,
) =>
  stream(
    `/conversations/${payload.conversation_id}/messages/${payload.message_id}/edit`,
    payload,
    onEvent,
    signal,
  )

export type { ChatMessage, Conversation }

import type { AssistantMemory, AssistantProfile } from './chat-types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok)
    throw new Error(
      (await response.json().catch(() => null))?.detail || `请求失败 (${response.status})`,
    )
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

export const listAssistants = (userId: string) =>
  request<AssistantProfile[]>(`/assistants?user_id=${encodeURIComponent(userId)}`)
export const createAssistant = (
  payload: Pick<
    AssistantProfile,
    | 'user_id'
    | 'name'
    | 'system_prompt'
    | 'capability_ids'
    | 'avatar_data_url'
    | 'include_runtime_context'
    | 'memory_enabled'
    | 'memory_update_interval'
    | 'history_search_enabled'
    | 'history_similarity_threshold'
    | 'history_result_limit'
    | 'context_strategy'
    | 'compression_threshold_turns'
    | 'compression_threshold_tokens'
    | 'compression_keep_recent_turns'
  >,
) =>
  request<AssistantProfile>('/assistants', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
export const updateAssistant = (
  id: string,
  userId: string,
  payload: Partial<
    Pick<
      AssistantProfile,
      | 'name'
      | 'system_prompt'
      | 'capability_ids'
      | 'avatar_data_url'
      | 'include_runtime_context'
      | 'memory_enabled'
      | 'memory_update_interval'
      | 'history_search_enabled'
      | 'history_similarity_threshold'
      | 'history_result_limit'
      | 'context_strategy'
      | 'compression_threshold_turns'
      | 'compression_threshold_tokens'
      | 'compression_keep_recent_turns'
    >
  >,
) =>
  request<AssistantProfile>(`/assistants/${id}?user_id=${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
export const deleteAssistant = (id: string, userId: string) =>
  request<void>(`/assistants/${id}?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' })

export const getAssistantMemory = (id: string, userId: string) =>
  request<AssistantMemory>(`/assistants/${id}/memory?user_id=${encodeURIComponent(userId)}`)
export const saveAssistantMemory = (id: string, userId: string, summary: string) =>
  request<AssistantMemory>(`/assistants/${id}/memory?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ summary }),
  })
export const clearAssistantMemory = (id: string, userId: string) =>
  request<void>(`/assistants/${id}/memory?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })
export const refreshAssistantMemory = (id: string, userId: string) =>
  request<AssistantMemory>(
    `/assistants/${id}/memory/refresh?user_id=${encodeURIComponent(userId)}`,
    { method: 'POST' },
  )

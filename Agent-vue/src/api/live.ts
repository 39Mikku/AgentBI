import type {
  LiveConversation,
  LiveMessage,
  LivePreferences,
  LiveRole,
  LiveRoleMemory,
} from './live-types'

const BASE = '/api'

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) {
    const detail = (await response.json().catch(() => null))?.detail
    throw new Error(typeof detail === 'string' ? detail : `请求失败 (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function body(method: string, payload: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }
}

export function getLivePreferences(userId: string): Promise<LivePreferences> {
  return json(`/live/preferences?user_id=${encodeURIComponent(userId)}`)
}

export function saveLivePreferences(
  userId: string,
  preferences: Omit<LivePreferences, 'user_id'>,
): Promise<LivePreferences> {
  return json(`/live/preferences?user_id=${encodeURIComponent(userId)}`, body('PUT', preferences))
}

export function listLiveRoles(userId: string): Promise<LiveRole[]> {
  return json(`/live/roles?user_id=${encodeURIComponent(userId)}`)
}

export function createLiveRole(payload: Omit<LiveRole, 'id' | 'is_default' | 'created_at' | 'updated_at'>): Promise<LiveRole> {
  return json('/live/roles', body('POST', payload))
}

export function updateLiveRole(
  roleId: string,
  userId: string,
  payload: Partial<Pick<LiveRole, 'name' | 'instructions' | 'voice' | 'avatar_data_url' | 'memory_enabled'>>,
): Promise<LiveRole> {
  return json(`/live/roles/${roleId}?user_id=${encodeURIComponent(userId)}`, body('PUT', payload))
}

export function deleteLiveRole(roleId: string, userId: string): Promise<void> {
  return json(`/live/roles/${roleId}?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' })
}

export function getLiveRoleMemory(roleId: string, userId: string): Promise<LiveRoleMemory> {
  return json(`/live/roles/${roleId}/memory?user_id=${encodeURIComponent(userId)}`)
}

export function saveLiveRoleMemory(roleId: string, userId: string, content: string): Promise<LiveRoleMemory> {
  return json(`/live/roles/${roleId}/memory?user_id=${encodeURIComponent(userId)}`, body('PUT', { content }))
}

export function clearLiveRoleMemory(roleId: string, userId: string): Promise<void> {
  return json(`/live/roles/${roleId}/memory?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' })
}

export function refreshLiveRoleMemory(roleId: string, userId: string): Promise<LiveRoleMemory> {
  return json(`/live/roles/${roleId}/memory/refresh?user_id=${encodeURIComponent(userId)}`, { method: 'POST' })
}

export function listLiveConversations(userId: string, roleId: string): Promise<LiveConversation[]> {
  return json(`/live/conversations?user_id=${encodeURIComponent(userId)}&role_id=${encodeURIComponent(roleId)}`)
}

export function createLiveConversation(payload: { user_id: string; role_id: string; title?: string }): Promise<LiveConversation> {
  return json('/live/conversations', body('POST', payload))
}

export function updateLiveConversation(conversationId: string, userId: string, title: string): Promise<LiveConversation> {
  return json(`/live/conversations/${conversationId}?user_id=${encodeURIComponent(userId)}`, body('PUT', { title }))
}

export function deleteLiveConversation(conversationId: string, userId: string): Promise<void> {
  return json(`/live/conversations/${conversationId}?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' })
}

export function listLiveMessages(userId: string, conversationId: string): Promise<LiveMessage[]> {
  return json(`/live/conversations/${conversationId}/messages?user_id=${encodeURIComponent(userId)}`)
}

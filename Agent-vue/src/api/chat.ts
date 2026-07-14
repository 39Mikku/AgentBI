import type { ChatMessage, ChatPreferences, ChatStreamEvent, Conversation } from './chat-types'

const BASE = '/api'

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || `请求失败 (${response.status})`)
  return response.json() as Promise<T>
}

export const listConversations = (userId: string) => json<Conversation[]>(`/conversations?user_id=${encodeURIComponent(userId)}`)
export const createConversation = (payload: Partial<Conversation> & { user_id: string }) =>
  json<Conversation>('/conversations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
export const updateConversation = (id: string, userId: string, payload: Partial<Conversation>) =>
  json<Conversation>(`/conversations/${id}?user_id=${encodeURIComponent(userId)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
export const deleteConversation = (id: string, userId: string) =>
  fetch(`${BASE}/conversations/${id}?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' })
export const listMessages = (id: string, userId: string) => json<ChatMessage[]>(`/conversations/${id}/messages?user_id=${encodeURIComponent(userId)}`)

export async function streamChat(
  payload: { user_id: string; conversation_id: string; content: string } & Partial<ChatPreferences>,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
) {
  const response = await fetch(`${BASE}/chat/stream`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      ...payload, provider_id: payload.providerId, context_turns: payload.contextTurns,
    }), signal,
  })
  if (!response.ok || !response.body) throw new Error((await response.json().catch(() => null))?.detail || '无法开始生成')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''
    for (const frame of frames) {
      const name = frame.match(/^event: (.+)$/m)?.[1]
      const raw = frame.match(/^data: (.+)$/m)?.[1]
      if (name && raw) onEvent({ event: name, data: JSON.parse(raw) })
    }
  }
}

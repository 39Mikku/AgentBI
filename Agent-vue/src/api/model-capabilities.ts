import type { ModelCapability } from './chat-types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok)
    throw new Error((await response.json().catch(() => null))?.detail || '模型能力配置失败')
  return response.json() as Promise<T>
}

export const listModelCapabilities = (userId: string) =>
  request<ModelCapability[]>(`/model-capabilities?user_id=${encodeURIComponent(userId)}`)

export const saveModelCapability = (
  userId: string,
  providerId: string,
  model: string,
  supportsVision: boolean,
) =>
  request<ModelCapability>(`/model-capabilities?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider_id: providerId,
      model,
      supports_vision: supportsVision,
    }),
  })

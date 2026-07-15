import type { CapabilitySettings } from './chat-types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok)
    throw new Error(
      (await response.json().catch(() => null))?.detail || `能力配置请求失败 (${response.status})`,
    )
  return response.json() as Promise<T>
}

export const listCapabilitySettings = (userId: string) =>
  request<CapabilitySettings[]>(`/capabilities/settings?user_id=${encodeURIComponent(userId)}`)

export const saveCapabilitySettings = (
  userId: string,
  capabilityId: string,
  config: CapabilitySettings['config'],
) =>
  request<CapabilitySettings>(
    `/capabilities/${encodeURIComponent(capabilityId)}/settings?user_id=${encodeURIComponent(userId)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config }),
    },
  )

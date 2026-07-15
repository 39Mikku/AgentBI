import type { SubagentSettings } from './chat-types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok)
    throw new Error(
      (await response.json().catch(() => null))?.detail || `子代理配置请求失败 (${response.status})`,
    )
  return response.json() as Promise<T>
}

export const listSubagentSettings = (userId: string) =>
  request<SubagentSettings[]>(`/subagents/settings?user_id=${encodeURIComponent(userId)}`)

export const saveSubagentSettings = (
  userId: string,
  capabilityId: string,
  config: SubagentSettings['config'],
) =>
  request<SubagentSettings>(
    `/subagents/${encodeURIComponent(capabilityId)}/settings?user_id=${encodeURIComponent(userId)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config }),
    },
  )

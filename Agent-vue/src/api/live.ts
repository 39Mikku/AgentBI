import type { LivePreferences } from './live-types'

const BASE = '/api'

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) {
    const detail = (await response.json().catch(() => null))?.detail
    throw new Error(typeof detail === 'string' ? detail : `请求失败 (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function getLivePreferences(userId: string): Promise<LivePreferences> {
  return json(`/live/preferences?user_id=${encodeURIComponent(userId)}`)
}

export function saveLivePreferences(
  userId: string,
  preferences: Omit<LivePreferences, 'user_id'>,
): Promise<LivePreferences> {
  return json(`/live/preferences?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(preferences),
  })
}

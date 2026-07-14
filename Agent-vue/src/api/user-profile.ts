const BASE = '/api'

export interface UserProfile {
  user_id: string
  username: string
  email?: string | null
  avatar_data_url?: string | null
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || `请求失败 (${response.status})`)
  return response.json() as Promise<T>
}

export const getUserProfile = (userId: string) => json<UserProfile>(`/user-profile?user_id=${encodeURIComponent(userId)}`)

export const saveUserAvatar = (userId: string, avatarDataUrl: string) =>
  json<UserProfile>(`/user-profile/avatar?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ avatar_data_url: avatarDataUrl }),
  })

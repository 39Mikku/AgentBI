const BASE = '/api'

export interface HomeQuote {
  text: string
  speaker: string
}

export interface UserProfile {
  user_id: string
  username: string
  email?: string | null
  avatar_data_url?: string | null
  home_quotes?: HomeQuote[] | null
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || `请求失败 (${response.status})`)
  return response.json() as Promise<T>
}

export const getUserProfile = (userId: string) => json<UserProfile>(`/user-profile?user_id=${encodeURIComponent(userId)}`)

export const saveHomeQuotes = (userId: string, quotes: HomeQuote[] | null) =>
  json<UserProfile>(`/user-profile/quotes?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ home_quotes: quotes }),
  })

export const saveUserAvatar = (userId: string, avatarDataUrl: string) =>
  json<UserProfile>(`/user-profile/avatar?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ avatar_data_url: avatarDataUrl }),
  })

export const saveUserName = (userId: string, username: string) =>
  json<UserProfile>(`/user-profile?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username }),
  })

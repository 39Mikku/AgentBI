import type { StudioAsset } from './chat-types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok)
    throw new Error((await response.json().catch(() => null))?.detail || '附件请求失败')
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

export async function uploadAsset(userId: string, file: File): Promise<StudioAsset> {
  const body = new FormData()
  body.append('user_id', userId)
  body.append('file', file)
  return request<StudioAsset>('/assets', { method: 'POST', body })
}

export function listAssets(
  userId: string,
  filters: { kind?: string; source?: string; search?: string } = {},
): Promise<StudioAsset[]> {
  const params = new URLSearchParams({ user_id: userId })
  if (filters.kind) params.set('kind', filters.kind)
  if (filters.source) params.set('source', filters.source)
  if (filters.search) params.set('search', filters.search)
  return request<StudioAsset[]>(`/assets?${params}`)
}

export const deleteAsset = (userId: string, assetId: string) =>
  request<void>(`/assets/${encodeURIComponent(assetId)}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })

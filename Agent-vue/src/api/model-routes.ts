import type { ModelRoute, ModelRouteRole } from './chat-types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok)
    throw new Error((await response.json().catch(() => null))?.detail || '后台模型配置失败')
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

export const listModelRoutes = (userId: string) =>
  request<ModelRoute[]>(`/model-routes?user_id=${encodeURIComponent(userId)}`)

export const saveModelRoute = (
  userId: string,
  role: ModelRouteRole,
  providerId: string,
  model: string,
) =>
  request<ModelRoute>(`/model-routes/${role}?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider_id: providerId, model }),
  })

export const deleteModelRoute = (userId: string, role: ModelRouteRole) =>
  request<void>(`/model-routes/${role}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })

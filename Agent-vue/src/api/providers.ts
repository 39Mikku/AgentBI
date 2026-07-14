import type { ProviderProfile } from './chat-types'

const BASE = '/api'
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || '提供商请求失败')
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>
}
export const listProviders = () => request<ProviderProfile[]>('/providers')
export const createProvider = (payload: { name: string; base_url: string; api_key: string; default_model?: string }) => request<ProviderProfile>('/providers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
export const refreshModels = (id: string) => request<ProviderProfile>(`/providers/${id}/refresh-models`, { method: 'POST' })
export const deleteProvider = (id: string) => request<void>(`/providers/${id}`, { method: 'DELETE' })

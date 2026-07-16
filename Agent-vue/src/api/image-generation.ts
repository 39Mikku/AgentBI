import type {
  CodexImageOAuthStart,
  CodexImageOAuthStatus,
  GeneratedImage,
  GenerateImagePayload,
} from './image-generation-types'

const BASE = '/api/image-generation'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail || `图片生成请求失败 (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const generateImage = (payload: GenerateImagePayload) =>
  request<GeneratedImage>('/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const getCodexImageStatus = () =>
  request<CodexImageOAuthStatus>('/codex/status')

export const connectCodexImage = () =>
  request<CodexImageOAuthStart>('/codex/connect', { method: 'POST' })

export const disconnectCodexImage = () =>
  request<void>('/codex/connection', { method: 'DELETE' })


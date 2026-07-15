import type {
  AutoInputJob,
  AutoInputPayload,
  DirectorySelectionPayload,
  DirectorySelectionResult,
  FileTimeJob,
  FileTimePayload,
  FileTimePreview,
} from './toolbox-system-types'


const BASE = '/api/toolbox'

async function errorMessage(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null) as { detail?: string } | null
  return payload?.detail || `工具请求失败（HTTP ${response.status}）`
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.status === 204 ? (null as T) : response.json() as Promise<T>
}

const jsonRequest = (method: 'POST', body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const selectNativeDirectory = (payload: DirectorySelectionPayload = {}) =>
  requestJson<DirectorySelectionResult>('/system/select-directory', jsonRequest('POST', payload))

export const previewFileTime = (payload: FileTimePayload) =>
  requestJson<FileTimePreview>('/file-time/preview', jsonRequest('POST', payload))

export const startFileTimeJob = (payload: FileTimePayload) =>
  requestJson<FileTimeJob>('/file-time/jobs', jsonRequest('POST', payload))

export const getFileTimeJob = (jobId: string) =>
  requestJson<FileTimeJob>(`/file-time/jobs/${encodeURIComponent(jobId)}`)

export const startAutoInputJob = (payload: AutoInputPayload) =>
  requestJson<AutoInputJob>('/auto-input/jobs', jsonRequest('POST', payload))

export const getActiveAutoInputJob = () =>
  requestJson<AutoInputJob | null>('/auto-input/jobs/active')

export const getAutoInputJob = (jobId: string) =>
  requestJson<AutoInputJob>(`/auto-input/jobs/${encodeURIComponent(jobId)}`)

export const cancelAutoInputJob = (jobId: string) =>
  requestJson<AutoInputJob>(`/auto-input/jobs/${encodeURIComponent(jobId)}/cancel`, jsonRequest('POST', {}))


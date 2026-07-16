import type {
  MoegirlArtifactDocument,
  MoegirlArtifactDownload,
  MoegirlArtifactSummary,
  MoegirlFetchPayload,
  MoegirlFetchResult,
} from './toolbox-moegirl-types'


const BASE = '/api/toolbox/moegirl'

type ErrorDetail = string | Array<{ msg?: string }>

async function errorMessage(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null) as { detail?: ErrorDetail } | null
  if (typeof payload?.detail === 'string') return payload.detail
  if (Array.isArray(payload?.detail)) {
    const messages = payload.detail.flatMap((item) => item.msg ? [item.msg] : [])
    if (messages.length) return messages.join('；')
  }
  return `萌娘百科归档请求失败（HTTP ${response.status}）`
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>
}

function userQuery(userId: string): string {
  return `user_id=${encodeURIComponent(userId)}`
}

function downloadFilename(disposition: string | null, artifactId: string): string {
  if (disposition) {
    const encoded = disposition.match(/filename\*\s*=\s*(?:UTF-8'')?([^;]+)/i)?.[1]?.trim().replace(/^"|"$/g, '')
    if (encoded) {
      try {
        return decodeURIComponent(encoded).split(/[\\/]/).pop() || `moegirl-${artifactId}.md`
      } catch {
        // Continue to the ASCII filename fallback when filename* is malformed.
      }
    }
    const plain = disposition.match(/filename\s*=\s*(?:"([^"]+)"|([^;\s]+))/i)
    const value = (plain?.[1] || plain?.[2])?.split(/[\\/]/).pop()
    if (value) return value
  }
  return `moegirl-${artifactId}.md`
}

export const fetchMoegirlPage = (payload: MoegirlFetchPayload, signal?: AbortSignal) =>
  requestJson<MoegirlFetchResult>('/fetch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    ...(signal ? { signal } : {}),
  })

export const listMoegirlArtifacts = (userId: string, signal?: AbortSignal) =>
  requestJson<MoegirlArtifactSummary[]>(
    `/artifacts?${userQuery(userId)}`,
    signal ? { signal } : undefined,
  )

export const getMoegirlArtifact = (artifactId: string, userId: string, signal?: AbortSignal) =>
  requestJson<MoegirlArtifactDocument>(
    `/artifacts/${encodeURIComponent(artifactId)}?${userQuery(userId)}`,
    signal ? { signal } : undefined,
  )

export async function downloadMoegirlArtifact(
  artifactId: string,
  userId: string,
): Promise<MoegirlArtifactDownload> {
  const response = await fetch(
    `${BASE}/artifacts/${encodeURIComponent(artifactId)}/download?${userQuery(userId)}`,
  )
  if (!response.ok) throw new Error(await errorMessage(response))
  return {
    blob: await response.blob(),
    filename: downloadFilename(response.headers.get('Content-Disposition'), artifactId),
  }
}

export const deleteMoegirlArtifact = (artifactId: string, userId: string, signal?: AbortSignal) =>
  requestJson<void>(
    `/artifacts/${encodeURIComponent(artifactId)}?${userQuery(userId)}`,
    { method: 'DELETE', ...(signal ? { signal } : {}) },
  )

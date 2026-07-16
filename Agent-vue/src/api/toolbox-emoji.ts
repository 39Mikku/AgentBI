import type { StickerNamingPayload, StickerNamingResponse } from './toolbox-emoji-types'

const BASE = '/api/toolbox/emoji'

export async function nameStickers(payload: StickerNamingPayload): Promise<StickerNamingResponse> {
  const response = await fetch(`${BASE}/name`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail || `贴纸命名失败 (${response.status})`)
  }
  return response.json() as Promise<StickerNamingResponse>
}

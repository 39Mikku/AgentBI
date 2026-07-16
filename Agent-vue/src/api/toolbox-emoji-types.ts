export type StickerNamingStrategy = 'batch' | 'individual'

export interface StickerNamingImage {
  id: string
  data_url: string
}

export interface StickerNamingPayload {
  user_id: string
  strategy: StickerNamingStrategy
  images: StickerNamingImage[]
}

export interface StickerNameResult {
  id: string
  name: string
}

export interface StickerNamingResponse {
  names: StickerNameResult[]
  strategy: StickerNamingStrategy
  model: string
}

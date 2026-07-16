export type ImageMode = 'lite' | 'pro'
export type ImageQuality = 'low' | 'medium' | 'high'
export type ImageAspectRatio = 'square' | 'landscape' | 'portrait'

export interface GeneratedImage {
  id: string
  url: string
  relative_path?: string
  media_type?: string
  mode: ImageMode
  model: string
  aspect_ratio: ImageAspectRatio
  width?: number | null
  height?: number | null
  prompt?: string
}

export interface GenerateImagePayload {
  user_id: string
  prompt: string
  aspect_ratio: ImageAspectRatio
  provider_id?: string
  scope_id?: string
}

export interface CodexImageOAuthStatus {
  connected: boolean
  account_id?: string | null
  expires_at?: number | null
  pending: boolean
  error?: string | null
}

export interface CodexImageOAuthStart {
  authorization_url: string
  user_code: string
  expires_in: number
}


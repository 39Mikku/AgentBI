const VOICE_NAMES: Record<string, string> = {
  longanqian: '芊悦',
  longanlingxin: '灵心',
  longanlingxi: '灵犀',
  longanxiaoxin: '小新',
  longanlufeng: '鹿风',
}

export function roleInitials(name: string): string {
  const normalized = name.trim()
  if (!normalized) return 'AI'
  const words = normalized.split(/\s+/)
  if (words.length > 1) return words.slice(0, 2).map((word) => word[0]).join('').toUpperCase()
  return Array.from(normalized).slice(0, 2).join('').toUpperCase()
}

export function resolvedVoice(builtInVoice: string, customVoice: string): string {
  return customVoice.trim() || builtInVoice
}

function liveCatalogVoice(voice: string, catalog: TtsCustomVoice[]): TtsCustomVoice | undefined {
  return catalog.find((item) =>
    item.provider === 'bailian'
    && item.external_voice_id === voice
    && item.provider_metadata.usage === 'live',
  )
}

export function voiceLabel(voice: string, catalog: TtsCustomVoice[] = []): string {
  return VOICE_NAMES[voice] || liveCatalogVoice(voice, catalog)?.display_name || '自定义音色'
}

export function isLiveVoiceCompatible(
  voice: string,
  model: string,
  catalog: TtsCustomVoice[],
): boolean {
  const saved = liveCatalogVoice(voice, catalog)
  return !saved || saved.bound_model === model
}

export function hasRoleAvatar(avatar?: string | null): boolean {
  return Boolean(avatar?.trim())
}
import type { TtsCustomVoice } from '@/api/toolbox-tts-types'

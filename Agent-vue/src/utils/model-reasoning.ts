import type { ChatPreferences } from '@/api/chat-types'
import { isGeminiThinkingModel } from './gemini-thinking'

export type ReasoningLevel = ChatPreferences['thinkingLevel']
export type ReasoningChoice = { value: ReasoningLevel; label: string }

const DEEPSEEK_V4_THINKING_MODEL = /(?:^|\/)deepseek-v4-(?:flash|pro)(?:-|$)/i

export function isDeepSeekV4ThinkingModel(model?: string | null): boolean {
  return DEEPSEEK_V4_THINKING_MODEL.test((model || '').trim())
}

export function reasoningChoices(model?: string | null): ReasoningChoice[] {
  if (isDeepSeekV4ThinkingModel(model)) {
    return [
      { value: 'off', label: '关' },
      { value: 'low', label: '低' },
      { value: 'high', label: '高' },
    ]
  }
  if (isGeminiThinkingModel(model)) {
    return [
      { value: 'low', label: '低' },
      { value: 'medium', label: '中' },
      { value: 'high', label: '高' },
    ]
  }
  return []
}

export function normalizeReasoningLevel(
  model: string | null | undefined,
  level: ReasoningLevel,
): ReasoningLevel {
  if (isDeepSeekV4ThinkingModel(model)) return level === 'medium' ? 'low' : level
  if (isGeminiThinkingModel(model)) return level === 'off' ? 'medium' : level
  return level
}

import { describe, expect, it } from 'vitest'
import {
  isDeepSeekV4ThinkingModel,
  reasoningChoices,
  normalizeReasoningLevel,
} from './model-reasoning'

describe('model reasoning controls', () => {
  it('matches only DeepSeek V4 Flash and Pro models', () => {
    expect(isDeepSeekV4ThinkingModel('deepseek-v4-flash')).toBe(true)
    expect(isDeepSeekV4ThinkingModel('models/deepseek-v4-pro')).toBe(true)
    expect(isDeepSeekV4ThinkingModel('deepseek-reasoner')).toBe(false)
    expect(isDeepSeekV4ThinkingModel('deepseek-v3')).toBe(false)
  })

  it('provides model-specific choices', () => {
    expect(reasoningChoices('gemini-3.5-flash').map((item) => item.value)).toEqual([
      'low',
      'medium',
      'high',
    ])
    expect(reasoningChoices('deepseek-v4-pro').map((item) => item.value)).toEqual([
      'off',
      'low',
      'high',
    ])
    expect(reasoningChoices('deepseek-v3')).toEqual([])
  })

  it('normalizes persisted levels when the model family changes', () => {
    expect(normalizeReasoningLevel('deepseek-v4-pro', 'medium')).toBe('low')
    expect(normalizeReasoningLevel('gemini-3.5-flash', 'off')).toBe('medium')
    expect(normalizeReasoningLevel('deepseek-v4-pro', 'high')).toBe('high')
  })
})

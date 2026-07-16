import { describe, expect, it } from 'vitest'
import { isGeminiThinkingModel, normalizeReasoningMarkdown } from './gemini-thinking'

describe('Gemini thinking helpers', () => {
  it('matches Gemini 2.5 and 3 text models only', () => {
    expect(isGeminiThinkingModel('gemini-2.5-pro')).toBe(true)
    expect(isGeminiThinkingModel('models/gemini-3.5-flash')).toBe(true)
    expect(isGeminiThinkingModel('gemini-2.0-flash')).toBe(false)
    expect(isGeminiThinkingModel('gemini-3-pro-image-preview')).toBe(false)
    expect(isGeminiThinkingModel('deepseek-v4-pro')).toBe(false)
  })

  it('promotes standalone bold phase labels without changing inline emphasis', () => {
    expect(
      normalizeReasoningMarkdown(
        '**Analyzing Input**\n\nInspect the values with **extra care**.\n\n## Native heading',
      ),
    ).toBe('### Analyzing Input\n\nInspect the values with **extra care**.\n\n## Native heading')
  })
})

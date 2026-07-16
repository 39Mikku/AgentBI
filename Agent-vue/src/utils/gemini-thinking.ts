import { renderMarkdown } from './markdown'

const GEMINI_THINKING_MODEL = /(?:^|\/)gemini-(?:2\.5|3(?:\.\d+)?)(?:-|$)/i
const NON_TEXT_MARKERS = ['image', 'imagen', 'audio', 'tts', 'embedding']

export function isGeminiThinkingModel(model?: string | null): boolean {
  const normalized = (model || '').trim().toLowerCase()
  return (
    GEMINI_THINKING_MODEL.test(normalized) &&
    !NON_TEXT_MARKERS.some((marker) => normalized.includes(marker))
  )
}

export function normalizeReasoningMarkdown(source: string): string {
  return (source || '').replace(
    /^(\s*)\*\*([^*\n][^*\n]*?)\*\*[ \t]*$/gm,
    (_match, indent: string, title: string) => `${indent}### ${title.trim()}`,
  )
}

export function renderReasoningMarkdown(source: string): string {
  return renderMarkdown(normalizeReasoningMarkdown(source))
}

export type ToolEventType = 'tool_started' | 'tool_finished'

function parsedJson(content?: string): unknown {
  if (!content?.trim()) return null
  try {
    return JSON.parse(content)
  } catch {
    return null
  }
}

export function formatToolEventContent(content?: string) {
  const parsed = parsedJson(content)
  return parsed === null ? content || '' : JSON.stringify(parsed, null, 2)
}

export function toolEventResultCount(content?: string): number | null {
  const parsed = parsedJson(content)
  if (Array.isArray(parsed)) return parsed.length
  if (!parsed || typeof parsed !== 'object') return null
  for (const value of Object.values(parsed)) {
    if (Array.isArray(value)) return value.length
  }
  return null
}

export function toolEventSummary(tool: string | undefined, type: ToolEventType, content?: string) {
  const parts = [tool || '工具', type === 'tool_started' ? '执行中' : '已完成']
  const count = type === 'tool_finished' ? toolEventResultCount(content) : null
  if (count !== null) parts.push(`${count} 项结果`)
  return parts.join(' · ')
}

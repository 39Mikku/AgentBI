export type TimelineCardEvent = {
  type: 'card'
  kind: string
  payload: Record<string, unknown>
}

export function toTimelineCard(data: Record<string, unknown>): TimelineCardEvent | null {
  if (typeof data.kind !== 'string' || !data.kind.trim()) return null
  if (!data.payload || typeof data.payload !== 'object' || Array.isArray(data.payload)) return null
  return {
    type: 'card',
    kind: data.kind,
    payload: data.payload as Record<string, unknown>,
  }
}

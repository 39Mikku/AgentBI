export function historySliderToTurns(position: number): number {
  const clamped = Math.min(100, Math.max(0, position))
  if (clamped >= 100) return 0
  const normalized = clamped / 99
  return Math.min(50, Math.max(1, Math.round(1 + 49 * normalized * normalized)))
}

export function historyTurnsToSlider(turns: number): number {
  if (turns === 0) return 100
  const clamped = Math.min(50, Math.max(1, turns))
  return Math.round(Math.sqrt((clamped - 1) / 49) * 99)
}

export function historyTurnsLabel(turns: number): string {
  return turns === 0 ? '全部历史' : `最近 ${turns} 轮`
}

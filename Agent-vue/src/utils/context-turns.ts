export const CONTEXT_TURN_STEPS = [2, 4, 8, 16, 32, 64, 128, 0] as const

export function contextTurnsFromSlider(index: number): number {
  return CONTEXT_TURN_STEPS[index] ?? 8
}

export function contextTurnSliderIndex(contextTurns: number): number {
  if (contextTurns === 0) return CONTEXT_TURN_STEPS.length - 1
  const exactIndex = CONTEXT_TURN_STEPS.indexOf(contextTurns as typeof CONTEXT_TURN_STEPS[number])
  if (exactIndex !== -1) return exactIndex

  let nearestIndex = 0
  let nearestDistance = Number.POSITIVE_INFINITY
  CONTEXT_TURN_STEPS.slice(0, -1).forEach((step, index) => {
    const distance = Math.abs(step - contextTurns)
    if (distance < nearestDistance) {
      nearestIndex = index
      nearestDistance = distance
    }
  })
  return nearestIndex
}

export function contextTurnLabel(contextTurns: number): string {
  return contextTurns === 0 ? '不截断' : `${contextTurns} 轮`
}

export function initialQuoteIndex(length: number, random: () => number = Math.random): number {
  if (length <= 0) return -1
  const value = Math.min(Math.max(random(), 0), 0.999999999)
  return Math.floor(value * length)
}

export function nextQuoteIndex(current: number, length: number): number {
  if (length <= 0) return -1
  if (current < 0 || current >= length) return 0
  return (current + 1) % length
}

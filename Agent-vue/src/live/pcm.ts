export function floatToInt16(input: Float32Array): Int16Array {
  return Int16Array.from(input, (sample) =>
    sample < 0 ? Math.max(-1, sample) * 32768 : Math.min(1, sample) * 32767,
  )
}

export function resampleFloat32(
  input: Float32Array,
  sourceRate: number,
  targetRate: number,
): Float32Array {
  if (sourceRate <= 0 || targetRate <= 0) throw new Error('sample rate must be positive')
  if (sourceRate === targetRate) return input.slice()
  if (!input.length) return new Float32Array()

  const outputLength = Math.max(1, Math.round((input.length * targetRate) / sourceRate))
  const output = new Float32Array(outputLength)
  const sourceStep = sourceRate / targetRate
  for (let index = 0; index < outputLength; index += 1) {
    const sourcePosition = index * sourceStep
    const leftIndex = Math.min(Math.floor(sourcePosition), input.length - 1)
    const rightIndex = Math.min(leftIndex + 1, input.length - 1)
    const mix = sourcePosition - leftIndex
    const left = input[leftIndex] ?? 0
    const right = input[rightIndex] ?? left
    output[index] = left + (right - left) * mix
  }
  return output
}

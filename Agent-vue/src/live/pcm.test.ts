import { describe, expect, it } from 'vitest'

import { floatToInt16, resampleFloat32 } from './pcm'

describe('PCM conversion', () => {
  it('converts and clamps float samples to signed 16 bit PCM', () => {
    expect([...floatToInt16(new Float32Array([-2, -1, -0.5, 0, 0.5, 1, 2]))]).toEqual([
      -32768, -32768, -16384, 0, 16383, 32767, 32767,
    ])
  })

  it('keeps samples stable when the source already uses the target rate', () => {
    const input = new Float32Array([0, 0.25, -0.5, 1])
    const output = resampleFloat32(input, 16000, 16000)

    expect([...output]).toEqual([...input])
    expect(output).not.toBe(input)
  })

  it('downsamples deterministic source positions from 48kHz to 16kHz', () => {
    const output = resampleFloat32(
      new Float32Array([0, 0.5, 1, -1, -0.5, 0]),
      48000,
      16000,
    )

    expect(output).toHaveLength(2)
    expect([...output]).toEqual([0, -1])
  })

  it('rejects invalid sample rates', () => {
    expect(() => resampleFloat32(new Float32Array([0]), 0, 16000)).toThrow('sample rate')
    expect(() => resampleFloat32(new Float32Array([0]), 48000, -1)).toThrow('sample rate')
  })
})

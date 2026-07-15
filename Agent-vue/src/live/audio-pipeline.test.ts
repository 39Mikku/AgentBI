import { describe, expect, it, vi } from 'vitest'

import { MicrophoneCapture } from './MicrophoneCapture'
import { PcmStreamPlayer } from './PcmStreamPlayer'

function audioHarness(sampleRate = 48000) {
  const port = {
    onmessage: null as ((event: MessageEvent<Float32Array>) => void) | null,
    postMessage: vi.fn(),
  }
  const node = { port, connect: vi.fn(), disconnect: vi.fn() }
  const source = { connect: vi.fn(), disconnect: vi.fn() }
  const gain = { gain: { value: 1 }, connect: vi.fn(), disconnect: vi.fn() }
  const context = {
    sampleRate,
    destination: {},
    audioWorklet: { addModule: vi.fn().mockResolvedValue(undefined) },
    createMediaStreamSource: vi.fn(() => source),
    createGain: vi.fn(() => gain),
    resume: vi.fn().mockResolvedValue(undefined),
    close: vi.fn().mockResolvedValue(undefined),
  }
  return { port, node, source, gain, context }
}

describe('MicrophoneCapture', () => {
  it('forwards PCM while active, suppresses it while muted, and releases resources', async () => {
    const harness = audioHarness()
    const stopTrack = vi.fn()
    const stream = { getTracks: () => [{ stop: stopTrack }] }
    const onPcm = vi.fn()
    const capture = new MicrophoneCapture({
      getUserMedia: vi.fn().mockResolvedValue(stream),
      createAudioContext: () => harness.context,
      createWorkletNode: () => harness.node,
    })

    await capture.start(onPcm)
    harness.port.onmessage?.({ data: new Float32Array([0, 0.5, -0.5]) } as MessageEvent<Float32Array>)
    expect(onPcm).toHaveBeenCalledTimes(1)

    capture.setMuted(true)
    harness.port.onmessage?.({ data: new Float32Array([0.25]) } as MessageEvent<Float32Array>)
    expect(onPcm).toHaveBeenCalledTimes(1)

    await capture.stop()
    expect(stopTrack).toHaveBeenCalledOnce()
    expect(harness.context.close).toHaveBeenCalledOnce()
  })
})

describe('PcmStreamPlayer', () => {
  it('queues binary PCM, clears immediately, and closes its audio context', async () => {
    const harness = audioHarness(24000)
    const player = new PcmStreamPlayer({
      createAudioContext: () => harness.context,
      createWorkletNode: () => harness.node,
    })

    await player.start()
    player.enqueue(new Uint8Array([1, 2, 3, 4]).buffer)
    player.clear()
    await player.stop()

    expect(harness.port.postMessage.mock.calls[0]?.[0]).toMatchObject({ type: 'enqueue' })
    expect(harness.port.postMessage.mock.calls[1]?.[0]).toEqual({ type: 'clear' })
    expect(harness.context.close).toHaveBeenCalledOnce()
  })
})

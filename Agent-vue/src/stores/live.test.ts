import { describe, expect, it, vi } from 'vitest'

import type { LiveServerEvent } from '@/api/live-types'
import { createLiveRuntime } from './live'

function runtimeHarness() {
  let onPcm: ((pcm: ArrayBuffer) => void) | null = null
  let callbacks:
    | {
        onEvent(event: LiveServerEvent): void
        onAudio(pcm: ArrayBuffer): void
        onClose(): void
        onError(): void
      }
    | undefined
  const socket = {
    connect: vi.fn().mockResolvedValue(undefined),
    sendAudio: vi.fn(),
    close: vi.fn(),
  }
  const microphone = {
    start: vi.fn(async (callback: (pcm: ArrayBuffer) => void) => {
      onPcm = callback
    }),
    setMuted: vi.fn(),
    stop: vi.fn().mockResolvedValue(undefined),
  }
  const player = {
    start: vi.fn().mockResolvedValue(undefined),
    enqueue: vi.fn(),
    clear: vi.fn(),
    stop: vi.fn().mockResolvedValue(undefined),
  }
  const dependencies = {
    loadPreferences: vi.fn().mockResolvedValue({
      user_id: 'alice',
      model: 'qwen-audio-3.0-realtime-flash' as const,
      voice: 'longanqian' as const,
      instructions: '自然交流。',
    }),
    savePreferences: vi.fn(async (_userId, preferences) => ({ user_id: 'alice', ...preferences })),
    createSocket: vi.fn((value) => {
      callbacks = value
      return socket
    }),
    microphone,
    player,
  }
  return {
    dependencies,
    socket,
    microphone,
    player,
    emit: (event: LiveServerEvent) => callbacks?.onEvent(event),
    emitAudio: (pcm: ArrayBuffer) => callbacks?.onAudio(pcm),
    emitMic: (pcm: ArrayBuffer) => onPcm?.(pcm),
  }
}

describe('Live runtime', () => {
  it('loads settings and sends microphone frames only after the session is ready', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)
    await live.loadPreferences('alice')
    await live.startCall('alice')

    const pcm = new Uint8Array([1, 2]).buffer
    harness.emitMic(pcm)
    expect(harness.socket.sendAudio).not.toHaveBeenCalled()

    harness.emit({ type: 'session.ready' })
    harness.emitMic(pcm)
    expect(harness.socket.sendAudio).toHaveBeenCalledWith(pcm)
    expect(live.state.phase).toBe('listening')
  })

  it('mutes uplink audio without closing and clears playback on interruption', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)
    await live.loadPreferences('alice')
    await live.startCall('alice')
    harness.emit({ type: 'session.ready' })

    live.toggleMute()
    harness.emitMic(new Uint8Array([1, 2]).buffer)
    expect(harness.microphone.setMuted).toHaveBeenCalledWith(true)
    expect(harness.socket.sendAudio).not.toHaveBeenCalled()
    expect(harness.socket.close).not.toHaveBeenCalled()

    harness.emit({ type: 'response.interrupted' })
    expect(harness.player.clear).toHaveBeenCalled()
  })

  it('plays incoming PCM and releases every resource when ending a call', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)
    await live.loadPreferences('alice')
    await live.startCall('alice')
    const pcm = new Uint8Array([3, 4]).buffer
    harness.emitAudio(pcm)
    await live.endCall()

    expect(harness.player.enqueue).toHaveBeenCalledWith(pcm)
    expect(harness.socket.close).toHaveBeenCalledOnce()
    expect(harness.microphone.stop).toHaveBeenCalledOnce()
    expect(harness.player.stop).toHaveBeenCalledOnce()
    expect(live.state.phase).toBe('idle')
  })
})

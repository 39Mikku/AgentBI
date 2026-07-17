import { describe, expect, it, vi } from 'vitest'

import { PlaygroundTtsPlayer } from './tts-player'


function fakeAudio() {
  return {
    currentTime: 0,
    onended: null as (() => void) | null,
    onerror: null as (() => void) | null,
    pause: vi.fn(),
    play: vi.fn().mockResolvedValue(undefined),
  }
}


describe('PlaygroundTtsPlayer', () => {
  it('revokes generated audio when the active story changes', () => {
    const revokeObjectURL = vi.fn()
    const player = new PlaygroundTtsPlayer({
      revokeObjectURL,
      createObjectURL: vi.fn(() => 'blob:unused'),
      createAudio: fakeAudio,
    })

    player.remember('message-1', 'blob:one')
    player.stopAndClear()

    expect(revokeObjectURL).toHaveBeenCalledWith('blob:one')
    expect(player.status('message-1')).toBe('idle')
  })

  it('synthesizes once and reuses the temporary URL', async () => {
    const audio = fakeAudio()
    const createAudio = vi.fn(() => audio)
    const createObjectURL = vi.fn(() => 'blob:voice')
    const synthesize = vi.fn().mockResolvedValue(new Blob(['voice']))
    const player = new PlaygroundTtsPlayer({
      revokeObjectURL: vi.fn(),
      createObjectURL,
      createAudio,
    })

    await player.synthesizeAndPlay('message-1', synthesize)
    await player.synthesizeAndPlay('message-1', synthesize)

    expect(synthesize).toHaveBeenCalledTimes(1)
    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(createAudio).toHaveBeenCalledTimes(2)
    expect(audio.play).toHaveBeenCalledTimes(2)
    expect(player.status('message-1')).toBe('playing')
  })

  it('keeps synthesis failures local to the message', async () => {
    const player = new PlaygroundTtsPlayer({
      revokeObjectURL: vi.fn(),
      createObjectURL: vi.fn(),
      createAudio: fakeAudio,
    })

    await expect(player.synthesizeAndPlay('message-1', async () => {
      throw new Error('音色不可用')
    })).rejects.toThrow('音色不可用')

    expect(player.status('message-1')).toBe('error')
    expect(player.error('message-1')).toBe('音色不可用')
  })
})

import { it } from 'vitest'
import assert from 'node:assert/strict'
import { createMusicPlayer, musicStreamUrl } from '../src/utils/music-player.ts'

it('legacy regression assertions', async () => {

  class FakeAudio {
    src = ''
    paused = true
    currentTime = 0
    listeners = new Map<string, () => void>()

    async play() {
      this.paused = false
    }

    pause() {
      this.paused = true
    }

    addEventListener(name: string, listener: () => void) {
      this.listeners.set(name, listener)
    }

    emit(name: string) {
      this.listeners.get(name)?.()
    }
  }

  const first = { id: '1', name: 'First', artists: ['A'], available: true }
  const second = { id: '2 / special', name: 'Second', artists: ['B'], available: true }
  const audio = new FakeAudio()
  const player = createMusicPlayer(audio)

  await player.play(first)
  assert.equal(player.state.currentTrack?.id, '1')
  assert.equal(player.state.playing, true)
  assert.equal(audio.src, '/api/music/tracks/1/stream')

  await player.toggle(first)
  assert.equal(player.state.playing, false)

  await player.toggle(first)
  assert.equal(player.state.playing, true)

  await player.play(second)
  assert.equal(player.state.currentTrack?.id, '2 / special')
  assert.equal(audio.src, '/api/music/tracks/2%20%2F%20special/stream')

  audio.emit('error')
  assert.equal(player.state.playing, false)
  assert.match(player.state.error, /播放/)

  assert.equal(musicStreamUrl('9'), '/api/music/tracks/9/stream')

})

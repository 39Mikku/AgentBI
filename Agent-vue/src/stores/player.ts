import { reactive } from 'vue'
import { defineStore } from 'pinia'
import {
  createMusicPlayer,
  type AudioPort,
  type MusicPlayerState,
  type MusicTrack,
} from '@/utils/music-player'

export const usePlayerStore = defineStore('player', () => {
  const state = reactive<MusicPlayerState>({ currentTrack: null, playing: false, error: '' })
  let controller: ReturnType<typeof createMusicPlayer> | null = null

  function getController() {
    if (!controller) {
      const audio = new Audio()
      audio.preload = 'none'
      controller = createMusicPlayer(audio as AudioPort, undefined, state)
    }
    return controller
  }

  async function play(track: MusicTrack) {
    await getController().play(track)
  }

  function pause() {
    getController().pause()
  }

  async function toggle(track: MusicTrack) {
    await getController().toggle(track)
  }

  return { state, play, pause, toggle }
})

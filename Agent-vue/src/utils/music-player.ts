export type MusicTrack = {
  id: string
  name: string
  artists: string[]
  album?: string
  cover_url?: string | null
  duration_ms?: number | null
  available: boolean
  unavailable_reason?: string | null
}

export type MusicPlayerState = {
  currentTrack: MusicTrack | null
  playing: boolean
  error: string
}

export type AudioPort = {
  src: string
  paused: boolean
  currentTime: number
  play(): Promise<void>
  pause(): void
  addEventListener(name: string, listener: () => void): void
}

export function musicStreamUrl(trackId: string) {
  return `/api/music/tracks/${encodeURIComponent(trackId)}/stream`
}

export function createMusicPlayer(
  audio: AudioPort,
  buildUrl = musicStreamUrl,
  state: MusicPlayerState = { currentTrack: null, playing: false, error: '' },
) {
  audio.addEventListener('ended', () => {
    state.playing = false
  })
  audio.addEventListener('error', () => {
    state.playing = false
    state.error = '歌曲播放失败，可能是版权、Cookie 或音质限制。'
  })

  async function play(track: MusicTrack) {
    if (!track.available) {
      state.error = track.unavailable_reason || '这首歌当前不可播放。'
      state.playing = false
      return
    }
    state.error = ''
    if (state.currentTrack?.id !== track.id) {
      audio.pause()
      audio.currentTime = 0
      audio.src = buildUrl(track.id)
      state.currentTrack = track
    }
    try {
      await audio.play()
      state.playing = true
    } catch {
      state.playing = false
      state.error = '浏览器未能开始播放，请再点击一次。'
    }
  }

  function pause() {
    audio.pause()
    state.playing = false
  }

  async function toggle(track: MusicTrack) {
    if (state.currentTrack?.id === track.id && state.playing) pause()
    else await play(track)
  }

  return { state, play, pause, toggle }
}

import { musicStreamUrl } from '@/utils/music-player'

export type MusicStatus = {
  enabled: boolean
  ready: boolean
  cookie_configured: boolean
}

export async function getMusicStatus(): Promise<MusicStatus> {
  const response = await fetch('/api/music/status')
  if (!response.ok) throw new Error('无法读取音乐服务状态')
  return response.json() as Promise<MusicStatus>
}

export { musicStreamUrl }

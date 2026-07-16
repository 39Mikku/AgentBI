import type { VideoGenerationStatus } from '@/api/video-generation'

export function isVideoJobTerminal(status: VideoGenerationStatus): boolean {
  return status === 'completed' || status === 'failed'
}

export function normalizeVideoProgress(progress: number | undefined): number {
  if (!Number.isFinite(progress)) return 0
  return Math.min(100, Math.max(0, Math.round(progress as number)))
}

export function videoPollDelay(status: VideoGenerationStatus): number | null {
  return isVideoJobTerminal(status) ? null : 3000
}

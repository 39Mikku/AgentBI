import type { VideoGenerationStatus } from '@/api/video-generation'

export type VideoModel = 'agnes-video-v2.0' | 'doubao-seedance-1-0-pro-250528'

const AGNES_RATIOS = ['16:9', '9:16', '1:1', '4:3', '3:4'] as const
const SEEDANCE_RATIOS = [...AGNES_RATIOS, '21:9', 'adaptive'] as const

export function videoDurationOptions(model: string): number[] {
  return model === 'doubao-seedance-1-0-pro-250528'
    ? [5, 10]
    : [3, 5, 10, 18]
}

export function videoAspectRatioOptions(model: string): string[] {
  return model === 'doubao-seedance-1-0-pro-250528'
    ? [...SEEDANCE_RATIOS]
    : [...AGNES_RATIOS]
}

export function videoResolutionOptions(model: string): string[] {
  return model === 'doubao-seedance-1-0-pro-250528' ? ['480p', '720p'] : ['720p']
}

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

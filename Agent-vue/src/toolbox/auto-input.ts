import type { AutoInputStatus } from '@/api/toolbox-system-types'


export interface CharacterProgress {
  typed_characters: number
  total_characters: number
}

export function autoInputProgress(job: CharacterProgress): number {
  if (job.total_characters <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((job.typed_characters / job.total_characters) * 100)))
}

export const isAutoInputActive = (status: AutoInputStatus) =>
  status === 'countdown' || status === 'running'

export const normalizeTextFile = (text: string) => text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')


import type { FileTimeOperation } from '@/api/toolbox-system-types'


export interface ProgressCounts {
  processed_files: number
  total_files: number
}

export const requiresOutput = (operation: FileTimeOperation) =>
  operation === 'filename_to_creation' || operation === 'move_by_creation_range'

export const requiresDateRange = (operation: FileTimeOperation) =>
  operation === 'move_by_creation_range'

export function fileTimeProgress(job: ProgressCounts): number {
  if (job.total_files <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((job.processed_files / job.total_files) * 100)))
}


export type FileTimeOperation =
  | 'creation_from_modified'
  | 'modified_from_creation'
  | 'filename_to_creation'
  | 'move_by_creation_range'

export interface DirectorySelectionPayload {
  title?: string
  initial_directory?: string | null
}

export interface DirectorySelectionResult {
  path: string | null
  cancelled: boolean
}

export interface FileTimePayload {
  operation: FileTimeOperation
  input_directory: string
  output_directory?: string | null
  start_date?: string | null
  end_date?: string | null
}

export interface FileTimePreview {
  operation: FileTimeOperation
  total_files: number
  update_count: number
  move_count: number
  skip_count: number
  examples: string[]
}

export type FileTimeJobStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface FileTimeJob {
  id: string
  operation: FileTimeOperation
  status: FileTimeJobStatus
  total_files: number
  processed_files: number
  updated_count: number
  moved_count: number
  skipped_count: number
  failed_count: number
  errors: string[]
  started_at: string | null
  completed_at: string | null
}

export interface AutoInputPayload {
  text: string
  delay_seconds: number
  countdown_seconds: number
}

export type AutoInputStatus = 'countdown' | 'running' | 'completed' | 'cancelled' | 'failed'

export interface AutoInputJob {
  id: string
  status: AutoInputStatus
  delay_seconds: number
  countdown_seconds: number
  countdown_remaining: number
  total_characters: number
  typed_characters: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  error: string | null
}


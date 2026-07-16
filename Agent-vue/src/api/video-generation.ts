export type VideoGenerationStatus = 'queued' | 'in_progress' | 'completed' | 'failed'

export interface VideoGenerationJob {
  id: string
  user_id: string
  conversation_id?: string | null
  message_id?: string | null
  prompt: string
  aspect_ratio: '16:9' | '9:16' | '1:1' | '4:3' | '3:4'
  duration_seconds: 3 | 5 | 10 | 18
  status: VideoGenerationStatus
  progress: number
  provider_video_id?: string | null
  asset_id?: string | null
  video_url?: string | null
  error?: string | null
  created_at?: string | null
  updated_at?: string | null
}

const BASE = '/api'

export async function getVideoGenerationJob(jobId: string, userId: string): Promise<VideoGenerationJob> {
  const response = await fetch(
    `${BASE}/video-generation/jobs/${encodeURIComponent(jobId)}?user_id=${encodeURIComponent(userId)}`,
  )
  if (!response.ok)
    throw new Error((await response.json().catch(() => null))?.detail || '视频任务状态获取失败')
  return response.json() as Promise<VideoGenerationJob>
}

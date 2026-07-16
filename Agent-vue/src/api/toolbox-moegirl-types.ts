export interface MoegirlArtifactSummary {
  id: string
  requested_name: string
  title: string
  source_url: string
  fetched_at: string
  updated_at: string
  character_count: number
  content_sha256: string
}

export interface MoegirlArtifactDocument extends MoegirlArtifactSummary {
  markdown: string
}

export interface MoegirlFetchPayload {
  user_id: string
  name: string
}

interface MoegirlFetchResultBase {
  title: string
  source_url: string
  markdown: string
  message: string
}

export interface MoegirlSavedFetchResult extends MoegirlFetchResultBase {
  kind: 'saved'
  artifact: MoegirlArtifactSummary
}

export interface MoegirlDisambiguationFetchResult extends MoegirlFetchResultBase {
  kind: 'disambiguation'
  artifact: null
}

export type MoegirlFetchResult = MoegirlSavedFetchResult | MoegirlDisambiguationFetchResult

export interface MoegirlArtifactDownload {
  blob: Blob
  filename: string
}

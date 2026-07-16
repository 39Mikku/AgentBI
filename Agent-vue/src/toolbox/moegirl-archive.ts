import type {
  MoegirlArtifactSummary,
  MoegirlFetchResult,
} from '@/api/toolbox-moegirl-types'


export interface MoegirlHistoryState {
  history: MoegirlArtifactSummary[]
  selectedId: string | null
}

export interface ArchiveFetchState {
  fetching: boolean
  opening: boolean
  deleting: boolean
  refining?: boolean
}

export interface ArchiveMutationState extends ArchiveFetchState {
  historyLoading: boolean
}

export function archiveDeleteUnavailable(state: ArchiveMutationState): boolean {
  return state.historyLoading || state.fetching || state.opening || state.deleting || Boolean(state.refining)
}

export function archiveFetchUnavailable(state: ArchiveFetchState): boolean {
  return state.fetching || state.opening || state.deleting || Boolean(state.refining)
}

export function beginArchiveRequest(currentGeneration: number): number {
  return currentGeneration + 1
}

export function acceptArchiveResponse(
  requestGeneration: number,
  currentGeneration: number,
): boolean {
  return requestGeneration === currentGeneration
}

export function applyFetchResult(
  history: MoegirlArtifactSummary[],
  result: MoegirlFetchResult,
): MoegirlArtifactSummary[] {
  if (result.kind === 'disambiguation') return history
  return [result.artifact, ...history.filter((item) => item.id !== result.artifact.id)]
}

export function selectFallbackArtifact(
  history: MoegirlArtifactSummary[],
): MoegirlArtifactSummary | null {
  return history[0] ?? null
}

export function removeArtifact(
  history: MoegirlArtifactSummary[],
  selectedId: string | null,
  deletedId: string,
): MoegirlHistoryState {
  const deletedIndex = history.findIndex((item) => item.id === deletedId)
  const nextHistory = history.filter((item) => item.id !== deletedId)
  if (selectedId !== deletedId) return { history: nextHistory, selectedId }

  const adjacent = deletedIndex >= 0
    ? nextHistory[Math.min(deletedIndex, nextHistory.length - 1)]
    : selectFallbackArtifact(nextHistory)
  return { history: nextHistory, selectedId: adjacent?.id ?? null }
}

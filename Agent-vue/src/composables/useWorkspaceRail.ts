import { ref, type Ref } from 'vue'

const STORAGE_KEY = 'agentbi.workspace-rail-collapsed'

export interface WorkspaceRailStorage {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

function browserStorage(): WorkspaceRailStorage | undefined {
  return typeof window === 'undefined' ? undefined : window.localStorage
}

export function readWorkspaceRailCollapsed(
  storage: WorkspaceRailStorage | undefined = browserStorage(),
  storageKey = STORAGE_KEY,
): boolean {
  try {
    return storage?.getItem(storageKey) === 'true'
  } catch {
    return false
  }
}

export function useWorkspaceRail(
  storage: WorkspaceRailStorage | undefined = browserStorage(),
  storageKey = STORAGE_KEY,
): { railCollapsed: Ref<boolean>; toggleRail: () => void } {
  const railCollapsed = ref(readWorkspaceRailCollapsed(storage, storageKey))

  function toggleRail() {
    railCollapsed.value = !railCollapsed.value
    try {
      storage?.setItem(storageKey, String(railCollapsed.value))
    } catch {
      // The UI state remains usable when privacy settings block localStorage.
    }
  }

  return { railCollapsed, toggleRail }
}

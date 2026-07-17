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
): boolean {
  try {
    return storage?.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

export function useWorkspaceRail(
  storage: WorkspaceRailStorage | undefined = browserStorage(),
): { railCollapsed: Ref<boolean>; toggleRail: () => void } {
  const railCollapsed = ref(readWorkspaceRailCollapsed(storage))

  function toggleRail() {
    railCollapsed.value = !railCollapsed.value
    try {
      storage?.setItem(STORAGE_KEY, String(railCollapsed.value))
    } catch {
      // The UI state remains usable when privacy settings block localStorage.
    }
  }

  return { railCollapsed, toggleRail }
}

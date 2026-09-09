import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { UserProfile } from '@/api/user-profile'

export interface WorkspaceResponse {
  profile: UserProfile | null
  profiles: UserProfile[]
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const profile = ref<UserProfile | null>(null)
  const profiles = ref<UserProfile[]>([])
  const loading = ref(false)
  const error = ref('')
  const ready = computed(() => profile.value !== null)
  const userId = computed(() => profile.value?.user_id || '')

  async function initialize(selectedId?: string) {
    loading.value = true
    error.value = ''
    try {
      const response = await fetch('/api/workspace', selectedId ? {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: selectedId }),
      } : undefined)
      if (!response.ok) {
        throw new Error((await response.json().catch(() => null))?.detail || '工作台初始化失败')
      }
      const data = await response.json() as WorkspaceResponse
      profiles.value = data.profiles
      profile.value = data.profile
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '连接失败，请确认后端已启动'
    } finally {
      loading.value = false
    }
  }

  function setProfile(value: UserProfile) {
    profile.value = value
  }

  return { profile, profiles, loading, error, ready, userId, initialize, setProfile }
})

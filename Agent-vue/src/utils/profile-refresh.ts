export interface CachedProfile {
  user_id: string
  avatar_data_url?: string | null
}

export function shouldRefreshUserProfile(profile: CachedProfile | null, userId: string): boolean {
  return profile?.user_id !== userId || !profile.avatar_data_url
}

<script setup lang="ts">
import { computed } from 'vue'
import MusicTrackCard from './MusicTrackCard.vue'
import MusicTrackListCard from './MusicTrackListCard.vue'
import type { MusicTrack } from '@/utils/music-player'

const props = defineProps<{ kind?: string; payload?: Record<string, unknown> }>()
const title = computed(() => (typeof props.payload?.title === 'string' ? props.payload.title : undefined))
const tracks = computed<MusicTrack[]>(() => {
  const items = Array.isArray(props.payload?.tracks) ? props.payload.tracks : []
  return items
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    .filter((item) => typeof item.id === 'string' && typeof item.name === 'string')
    .map((item) => ({
      id: item.id as string,
      name: item.name as string,
      artists: Array.isArray(item.artists) ? item.artists.filter((name): name is string => typeof name === 'string') : [],
      album: typeof item.album === 'string' ? item.album : '',
      cover_url: typeof item.cover_url === 'string' ? item.cover_url : null,
      duration_ms: typeof item.duration_ms === 'number' ? item.duration_ms : null,
      available: item.available !== false,
      unavailable_reason: typeof item.unavailable_reason === 'string' ? item.unavailable_reason : null,
    }))
})
</script>

<template>
  <MusicTrackListCard v-if="kind === 'music.track-list'" :title="title" :tracks="tracks" />
  <MusicTrackCard v-else-if="kind === 'music.track' && tracks[0]" :track="tracks[0]" />
  <div v-else class="unknown-card"><span>EXTENSION CARD</span><b>{{ kind || 'unknown' }}</b></div>
</template>

<style scoped>
.unknown-card{display:flex;justify-content:space-between;margin:12px 0;padding:11px 13px;border:1px dashed #9a978f;color:#7b7871;font:8px 'DM Mono',monospace}.unknown-card b{font-weight:500}
</style>

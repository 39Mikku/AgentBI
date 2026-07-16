<script setup lang="ts">
import { computed } from 'vue'
import MusicTrackCard from './MusicTrackCard.vue'
import MusicTrackListCard from './MusicTrackListCard.vue'
import BilibiliVideoCard from './BilibiliVideoCard.vue'
import BilibiliVideoListCard from './BilibiliVideoListCard.vue'
import ImageGenerationCard from './ImageGenerationCard.vue'
import type { MusicTrack } from '@/utils/music-player'
import { isValidBvid, type BilibiliVideo } from '@/utils/bilibili-player'

const props = defineProps<{ kind?: string; payload?: Record<string, unknown> }>()
const emit = defineEmits<{ playBilibili: [video: BilibiliVideo] }>()
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
const videos = computed<BilibiliVideo[]>(() => {
  const items = Array.isArray(props.payload?.videos) ? props.payload.videos : []
  return items
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    .filter((item) => typeof item.bvid === 'string' && isValidBvid(item.bvid))
    .map((item) => ({
      bvid: item.bvid as string,
      title: typeof item.title === 'string' ? item.title : '未命名视频',
      author: typeof item.author === 'string' ? item.author : '',
      cover_url: typeof item.cover_url === 'string' ? item.cover_url : null,
      duration_seconds: typeof item.duration_seconds === 'number' ? item.duration_seconds : 0,
      play_count: typeof item.play_count === 'number' ? item.play_count : 0,
      published_at: typeof item.published_at === 'number' ? item.published_at : null,
      description: typeof item.description === 'string' ? item.description : '',
      url: typeof item.url === 'string' ? item.url : undefined,
    }))
})
const image = computed(() => ({
  url: typeof props.payload?.url === 'string' ? props.payload.url : '',
  prompt: typeof props.payload?.prompt === 'string' ? props.payload.prompt : undefined,
  mode: typeof props.payload?.mode === 'string' ? props.payload.mode : undefined,
  model: typeof props.payload?.model === 'string' ? props.payload.model : undefined,
  aspectRatio: typeof props.payload?.aspect_ratio === 'string' ? props.payload.aspect_ratio : undefined,
  width: typeof props.payload?.width === 'number' ? props.payload.width : null,
  height: typeof props.payload?.height === 'number' ? props.payload.height : null,
  deleted: props.payload?.deleted === true,
}))
</script>

<template>
  <MusicTrackListCard v-if="kind === 'music.track-list'" :title="title" :tracks="tracks" />
  <MusicTrackCard v-else-if="kind === 'music.track' && tracks[0]" :track="tracks[0]" />
  <BilibiliVideoListCard
    v-else-if="kind === 'bilibili.video-list'"
    :title="title"
    :videos="videos"
    @play="emit('playBilibili', $event)"
  />
  <BilibiliVideoCard
    v-else-if="kind === 'bilibili.video' && videos[0]"
    :video="videos[0]"
    @play="emit('playBilibili', $event)"
  />
  <ImageGenerationCard
    v-else-if="kind === 'image.generated' && (image.url || image.deleted)"
    :url="image.url"
    :prompt="image.prompt"
    :mode="image.mode"
    :model="image.model"
    :aspect-ratio="image.aspectRatio"
    :width="image.width"
    :height="image.height"
    :deleted="image.deleted"
  />
  <div v-else class="unknown-card"><span>EXTENSION CARD</span><b>{{ kind || 'unknown' }}</b></div>
</template>

<style scoped>
.unknown-card{display:flex;justify-content:space-between;margin:12px 0;padding:11px 13px;border:1px dashed #9a978f;color:#7b7871;font:8px 'DM Mono',monospace}.unknown-card b{font-weight:500}
</style>

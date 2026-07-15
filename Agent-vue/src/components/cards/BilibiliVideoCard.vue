<script setup lang="ts">
import { computed } from 'vue'
import { bilibiliVideoUrl, type BilibiliVideo } from '@/utils/bilibili-player'

const props = defineProps<{ video: BilibiliVideo; index?: number }>()
const emit = defineEmits<{ play: [video: BilibiliVideo] }>()

const duration = computed(() => {
  const total = Math.max(0, Math.round(props.video.duration_seconds || 0))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  return hours
    ? `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
    : `${minutes}:${String(seconds).padStart(2, '0')}`
})

const playCount = computed(() =>
  new Intl.NumberFormat('zh-CN', { notation: 'compact', maximumFractionDigits: 1 }).format(
    props.video.play_count || 0,
  ),
)
</script>

<template>
  <article class="video-card">
    <button class="video-main" type="button" @click="emit('play', video)">
      <span class="cover">
        <img
          v-if="video.cover_url"
          :src="video.cover_url"
          alt=""
          loading="lazy"
          referrerpolicy="no-referrer"
        />
        <span v-else class="cover-fallback">BILI</span>
        <i class="play-mark" aria-hidden="true">▶</i>
        <time>{{ duration }}</time>
      </span>
      <span class="video-copy">
        <small><b v-if="index">{{ String(index).padStart(2, '0') }}</b>BILIBILI VIDEO</small>
        <strong>{{ video.title }}</strong>
        <span>{{ video.author || '未知 UP 主' }}</span>
        <em>{{ playCount }} 播放 · {{ video.bvid }}</em>
      </span>
    </button>
    <a
      class="external-link"
      :href="video.url || bilibiliVideoUrl(video.bvid)"
      target="_blank"
      rel="noopener noreferrer"
      title="在哔哩哔哩打开"
      >↗</a
    >
  </article>
</template>

<style scoped>
.video-card{position:relative;border-top:1px solid #c9c6be;background:transparent;transition:background .2s,transform .2s}.video-card:first-child{border-top:0}.video-card:hover{z-index:1;background:#fff;transform:translateX(2px)}.video-main{display:grid;grid-template-columns:164px minmax(0,1fr);gap:14px;width:100%;border:0;background:transparent;padding:11px 44px 11px 11px;text-align:left;cursor:pointer}.cover{position:relative;display:block;overflow:hidden;width:164px;aspect-ratio:16/9;background:#181818;color:#fb7299}.cover:after{position:absolute;inset:0;background:linear-gradient(130deg,transparent 45%,rgb(0 0 0/.52));content:''}.cover img{width:100%;height:100%;object-fit:cover;transition:transform .35s cubic-bezier(.2,.8,.2,1)}.video-main:hover .cover img{transform:scale(1.045)}.cover-fallback{display:grid;width:100%;height:100%;place-items:center;font:700 22px 'DM Mono',monospace;letter-spacing:.15em}.play-mark{position:absolute;z-index:2;left:10px;bottom:9px;display:grid;width:29px;height:29px;place-items:center;border:1px solid rgb(255 255 255/.78);border-radius:50%;background:rgb(17 17 17/.62);color:#fff;font:9px sans-serif;font-style:normal;backdrop-filter:blur(6px)}.cover time{position:absolute;z-index:2;right:8px;bottom:7px;padding:3px 5px;background:rgb(0 0 0/.7);color:#fff;font:8px 'DM Mono',monospace}.video-copy{display:flex;min-width:0;flex-direction:column;align-items:flex-start;justify-content:center}.video-copy small{display:flex;align-items:center;gap:8px;color:#9c6d7c;font:8px 'DM Mono',monospace;letter-spacing:.14em}.video-copy small b{display:grid;width:22px;height:17px;place-items:center;background:#fb7299;color:#fff;font-weight:500}.video-copy strong{display:-webkit-box;overflow:hidden;margin-top:8px;color:#171716;font:700 14px/1.36 Manrope,sans-serif;letter-spacing:-.025em;-webkit-box-orient:vertical;-webkit-line-clamp:2}.video-copy span{margin-top:7px;color:#54514d;font:9px 'DM Mono',monospace}.video-copy em{margin-top:5px;color:#99958d;font:8px 'DM Mono',monospace;font-style:normal}.external-link{position:absolute;right:12px;top:50%;display:grid;width:27px;height:27px;place-items:center;transform:translateY(-50%);border:1px solid #b6b2aa;border-radius:50%;color:#34322f;text-decoration:none;font:12px 'DM Mono',monospace;transition:.18s}.external-link:hover{border-color:#fb7299;background:#fb7299;color:#fff;transform:translateY(-50%) rotate(8deg)}@media(max-width:640px){.video-main{grid-template-columns:112px minmax(0,1fr);gap:10px;padding-left:8px}.cover{width:112px}.video-copy strong{margin-top:5px;font-size:12px}.video-copy em{display:none}.play-mark{width:24px;height:24px;left:7px;bottom:6px}}
</style>

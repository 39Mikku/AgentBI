<script setup lang="ts">
import { computed } from 'vue'
import { usePlayerStore } from '@/stores/player'
import type { MusicTrack } from '@/utils/music-player'

const props = defineProps<{ track: MusicTrack; index?: number }>()
const player = usePlayerStore()
const active = computed(() => player.state.currentTrack?.id === props.track.id)
const duration = computed(() => {
  if (!props.track.duration_ms) return ''
  const total = Math.round(props.track.duration_ms / 1000)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
})
</script>

<template>
  <article class="track" :class="{ active, unavailable: !track.available }">
    <span v-if="index" class="track-index">{{ String(index).padStart(2, '0') }}</span>
    <div class="cover">
      <img v-if="track.cover_url" :src="track.cover_url" alt="" loading="lazy" />
      <span v-else>♪</span>
      <i v-if="active && player.state.playing" class="equalizer"><b></b><b></b><b></b></i>
    </div>
    <div class="track-copy">
      <strong>{{ track.name }}</strong>
      <small>{{ track.artists.join(' / ') || '未知音乐人' }}</small>
      <em>{{ track.album || '网易云音乐' }}</em>
    </div>
    <time v-if="duration">{{ duration }}</time>
    <button
      :disabled="!track.available"
      :title="track.unavailable_reason || (active && player.state.playing ? '暂停' : '播放')"
      @click="player.toggle(track)"
    >
      {{ !track.available ? '×' : active && player.state.playing ? 'Ⅱ' : '▶' }}
    </button>
  </article>
</template>

<style scoped>
.track{position:relative;display:grid;grid-template-columns:auto 52px minmax(0,1fr) auto auto;align-items:center;gap:12px;padding:11px 12px;border-top:1px solid #c9c6be;transition:background .18s,transform .18s}.track:first-child{border-top:0}.track:hover{background:#fff;transform:translateX(2px)}.track-index{color:#908d85;font:9px 'DM Mono',monospace}.cover{position:relative;width:52px;height:52px;overflow:hidden;background:#1a1a19;color:#d9ff36;display:grid;place-items:center;font:22px Georgia}.cover img{width:100%;height:100%;object-fit:cover}.track-copy{display:grid;min-width:0}.track-copy strong{overflow:hidden;color:#171716;font:700 13px/1.25 Manrope,sans-serif;text-overflow:ellipsis;white-space:nowrap}.track-copy small,.track-copy em{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.track-copy small{margin-top:4px;color:#56544f;font:9px 'DM Mono',monospace}.track-copy em{margin-top:3px;color:#9a968d;font:8px 'DM Mono',monospace;font-style:normal}.track time{color:#8a877f;font:9px 'DM Mono',monospace}.track button{width:32px;height:32px;border:1px solid #191918;border-radius:50%;background:transparent;color:#191918;cursor:pointer;font-size:10px;transition:.18s}.track button:hover:not(:disabled),.track.active button{background:#191918;color:#d9ff36;transform:rotate(-6deg)}.track button:disabled{border-color:#aaa;color:#aaa;cursor:not-allowed}.track.unavailable{filter:grayscale(1);opacity:.58}.equalizer{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:2px;background:rgb(15 15 14/.66)}.equalizer b{width:2px;height:15px;background:#d9ff36;animation:meter .8s ease-in-out infinite alternate}.equalizer b:nth-child(2){height:9px;animation-delay:-.35s}.equalizer b:nth-child(3){height:19px;animation-delay:-.6s}@keyframes meter{to{height:5px}}@media(max-width:620px){.track{grid-template-columns:44px minmax(0,1fr) auto;padding-inline:8px}.track-index,.track time{display:none}.cover{width:44px;height:44px}}
</style>

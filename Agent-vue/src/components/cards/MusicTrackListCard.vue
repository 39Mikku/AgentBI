<script setup lang="ts">
import MusicTrackCard from './MusicTrackCard.vue'
import type { MusicTrack } from '@/utils/music-player'

defineProps<{ title?: string; tracks: MusicTrack[] }>()
</script>

<template>
  <section class="music-list-card">
    <header>
      <div><span>NETEASE / QUEUE</span><h3>{{ title || '音乐候选' }}</h3></div>
      <b>{{ String(tracks.length).padStart(2, '0') }}</b>
    </header>
    <div class="tracks">
      <MusicTrackCard v-for="(track, index) in tracks" :key="track.id" :track="track" :index="index + 1" />
    </div>
  </section>
</template>

<style scoped>
.music-list-card{position:relative;margin:15px 0 18px;border:1px solid #191918;background:#ece9e1;box-shadow:5px 5px 0 #191918;overflow:hidden}.music-list-card:before{position:absolute;right:-35px;top:-48px;width:120px;height:120px;border:22px solid #d9ff36;border-radius:50%;content:'';opacity:.72;pointer-events:none}.music-list-card header{position:relative;display:flex;align-items:end;justify-content:space-between;padding:18px 18px 13px;border-bottom:2px solid #191918}.music-list-card header span{color:#77736c;font:8px 'DM Mono',monospace;letter-spacing:.16em}.music-list-card h3{margin:4px 0 0;color:#171716;font:700 19px/1 Manrope,sans-serif;letter-spacing:-.05em}.music-list-card header b{z-index:1;color:#171716;font:700 28px/1 'DM Mono',monospace}.tracks{padding:5px 9px 9px}
</style>

<script setup lang="ts">
import BilibiliVideoCard from './BilibiliVideoCard.vue'
import type { BilibiliVideo } from '@/utils/bilibili-player'

defineProps<{ title?: string; videos: BilibiliVideo[] }>()
defineEmits<{ play: [video: BilibiliVideo] }>()
</script>

<template>
  <section class="bilibili-list-card">
    <header>
      <div><span>VIDEO SIGNAL / BILIBILI</span><h3>{{ title || '视频候选' }}</h3></div>
      <b>{{ String(videos.length).padStart(2, '0') }}</b>
    </header>
    <div class="videos">
      <BilibiliVideoCard
        v-for="(video, index) in videos"
        :key="video.bvid"
        :video="video"
        :index="index + 1"
        @play="$emit('play', $event)"
      />
    </div>
  </section>
</template>

<style scoped>
.bilibili-list-card{position:relative;margin:15px 0 18px;overflow:hidden;border:1px solid #191918;background:#ece9e1;box-shadow:5px 5px 0 #191918}.bilibili-list-card:before{position:absolute;right:-29px;top:-54px;width:126px;height:126px;border:23px solid #fb7299;border-radius:50%;content:'';opacity:.68;pointer-events:none}.bilibili-list-card header{position:relative;display:flex;align-items:end;justify-content:space-between;padding:18px 18px 13px;border-bottom:2px solid #191918}.bilibili-list-card header span{color:#8c767c;font:8px 'DM Mono',monospace;letter-spacing:.16em}.bilibili-list-card h3{margin:4px 0 0;color:#171716;font:700 19px/1 Manrope,sans-serif;letter-spacing:-.05em}.bilibili-list-card header b{z-index:1;color:#171716;font:700 28px/1 'DM Mono',monospace}.videos{padding:5px 9px 9px}
</style>


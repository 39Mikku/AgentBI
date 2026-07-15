<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  bilibiliVideoUrl,
  buildBilibiliPlayerUrl,
  type BilibiliVideo,
} from '@/utils/bilibili-player'

const props = defineProps<{ video: BilibiliVideo | null }>()
const emit = defineEmits<{ close: [] }>()
const loading = ref(true)
const playerUrl = computed(() => (props.video ? buildBilibiliPlayerUrl(props.video.bvid) : ''))
const officialUrl = computed(() => (props.video ? bilibiliVideoUrl(props.video.bvid) : '#'))

watch(
  () => props.video?.bvid,
  () => {
    loading.value = true
  },
)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.video) emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="cinema">
      <div v-if="video" class="player-backdrop" role="dialog" aria-modal="true" @click.self="$emit('close')">
        <section class="player-shell">
          <header>
            <div class="signal"><i></i><span>NOW SCREENING</span></div>
            <div class="title"><strong>{{ video.title }}</strong><small>{{ video.author }} · {{ video.bvid }}</small></div>
            <a :href="officialUrl" target="_blank" rel="noopener noreferrer">在 B 站打开 ↗</a>
            <button type="button" aria-label="关闭播放器" @click="$emit('close')">×</button>
          </header>
          <div class="screen">
            <div v-if="loading" class="screen-loading"><i></i><span>CONNECTING TO BILIBILI</span></div>
            <iframe
              :key="video.bvid"
              :src="playerUrl"
              :title="`播放 ${video.title}`"
              allow="autoplay; fullscreen; encrypted-media; picture-in-picture"
              allowfullscreen
              referrerpolicy="no-referrer-when-downgrade"
              @load="loading = false"
            ></iframe>
          </div>
          <footer><span>OFFICIAL EMBED PLAYER</span><small>播放能力与清晰度由哔哩哔哩提供</small></footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.player-backdrop{position:fixed;z-index:1000;inset:0;display:grid;place-items:center;padding:clamp(14px,4vw,54px);background:rgb(13 13 13/.82);backdrop-filter:blur(15px)}.player-shell{width:min(1180px,100%);overflow:hidden;border:1px solid #55524d;background:#171717;color:#f3f1eb;box-shadow:0 30px 90px rgb(0 0 0/.5),9px 9px 0 #fb7299}.player-shell header{display:grid;grid-template-columns:auto minmax(0,1fr) auto auto;align-items:center;gap:18px;padding:14px 16px;border-bottom:1px solid #393836}.signal{display:flex;align-items:center;gap:8px;color:#fb7299;font:8px 'DM Mono',monospace;letter-spacing:.15em}.signal i{width:7px;height:7px;border-radius:50%;background:#fb7299;box-shadow:0 0 0 4px rgb(251 114 153/.13),0 0 16px #fb7299}.title{display:grid;min-width:0}.title strong,.title small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.title strong{font:700 13px Manrope,sans-serif}.title small{margin-top:3px;color:#817e78;font:8px 'DM Mono',monospace}.player-shell header a{color:#d1cec7;font:9px 'DM Mono',monospace;text-decoration:none}.player-shell header a:hover{color:#fb7299}.player-shell header button{display:grid;width:30px;height:30px;place-items:center;border:1px solid #56534e;border-radius:50%;background:transparent;color:#eee;font:20px/1 Manrope;cursor:pointer}.player-shell header button:hover{border-color:#fb7299;background:#fb7299;color:#111}.screen{position:relative;aspect-ratio:16/9;background:#080808}.screen iframe{position:absolute;inset:0;width:100%;height:100%;border:0}.screen-loading{position:absolute;z-index:1;inset:0;display:grid;place-content:center;justify-items:center;gap:14px;background:#0d0d0d;color:#88857f;font:8px 'DM Mono',monospace;letter-spacing:.16em}.screen-loading i{width:27px;height:27px;border:2px solid #3c3a37;border-right-color:#fb7299;border-radius:50%;animation:screen-spin .75s linear infinite}.player-shell footer{display:flex;justify-content:space-between;padding:10px 15px;color:#fb7299;font:7px 'DM Mono',monospace;letter-spacing:.12em}.player-shell footer small{color:#68655f;font:inherit;letter-spacing:0}.cinema-enter-active,.cinema-leave-active{transition:opacity .24s ease}.cinema-enter-active .player-shell,.cinema-leave-active .player-shell{transition:transform .3s cubic-bezier(.2,.9,.2,1),opacity .2s}.cinema-enter-from,.cinema-leave-to{opacity:0}.cinema-enter-from .player-shell{opacity:0;transform:translateY(22px) scale(.985)}.cinema-leave-to .player-shell{opacity:0;transform:scale(.985)}@keyframes screen-spin{to{transform:rotate(360deg)}}@media(max-width:700px){.player-backdrop{padding:0}.player-shell{width:100%;box-shadow:none}.player-shell header{grid-template-columns:minmax(0,1fr) auto}.signal,.player-shell header>a{display:none}.title{grid-column:1}.screen{aspect-ratio:16/10}.player-shell footer small{display:none}}
</style>


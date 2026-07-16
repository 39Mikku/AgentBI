<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getVideoGenerationJob, type VideoGenerationJob, type VideoGenerationStatus } from '@/api/video-generation'
import { useAuthStore } from '@/stores/auth'
import { assetContentUrl } from '@/utils/chat-attachments'
import { normalizeVideoProgress, videoPollDelay } from '@/utils/video-generation'

const props = defineProps<{
  jobId: string
  prompt?: string
  status?: VideoGenerationStatus
  progress?: number
  aspectRatio?: string
  durationSeconds?: number
  provider?: string
  model?: string
}>()

const auth = useAuthStore()
const userId = computed(() => auth.email || 'local-user')
const job = ref<VideoGenerationJob | null>(null)
const requestError = ref('')
let timer: number | null = null

const status = computed<VideoGenerationStatus>(() => job.value?.status || props.status || 'queued')
const progress = computed(() => normalizeVideoProgress(job.value?.progress ?? props.progress))
const prompt = computed(() => job.value?.prompt || props.prompt || '视频生成任务')
const ratio = computed(() => job.value?.aspect_ratio || props.aspectRatio || '16:9')
const duration = computed(() => job.value?.duration_seconds || props.durationSeconds || 5)
const provider = computed(() => job.value?.provider || props.provider || 'agnes')
const model = computed(() => job.value?.model || props.model || 'agnes-video-v2.0')
const isVolcengine = computed(() => provider.value === 'volcengine')
const providerLabel = computed(() => isVolcengine.value ? 'SEEDANCE VIDEO / ARK' : 'AGNES VIDEO / ASYNC')
const videoUrl = computed(() => job.value?.asset_id ? assetContentUrl(job.value.asset_id, userId.value) : '')
const statusLabel = computed(() => ({
  queued: isVolcengine.value ? '等待方舟调度' : '等待 Agnes 接单',
  in_progress: isVolcengine.value ? 'Seedance 正在生成' : 'Agnes 正在生成',
  completed: '生成完成',
  failed: '生成失败',
}[status.value]))

async function refresh() {
  if (!props.jobId) return
  requestError.value = ''
  try {
    job.value = await getVideoGenerationJob(props.jobId, userId.value)
  } catch (reason) {
    requestError.value = reason instanceof Error ? reason.message : '任务状态获取失败'
  }
  const delay = videoPollDelay(job.value?.status || props.status || 'queued')
  if (delay !== null) timer = window.setTimeout(refresh, delay)
}

onMounted(refresh)
onBeforeUnmount(() => {
  if (timer) window.clearTimeout(timer)
})
</script>

<template>
  <article class="video-card" :class="[status, { indeterminate: isVolcengine && status !== 'completed' && status !== 'failed' }]">
    <header>
      <div><span>{{ providerLabel }}</span><b>{{ statusLabel }}</b></div>
      <i>{{ duration }}S · {{ ratio }}</i>
    </header>

    <div v-if="status === 'completed' && videoUrl" class="video-stage">
      <video :src="videoUrl" controls playsinline preload="metadata"></video>
      <a :href="videoUrl" :download="`${provider}-${jobId}.mp4`">下载 MP4 ↓</a>
    </div>
    <div v-else-if="status === 'failed'" class="failed-stage">
      <strong>任务未能完成</strong>
      <p>{{ job?.error || requestError || '视频提供商返回了失败状态，请让模型重新发起生成。' }}</p>
    </div>
    <div v-else class="progress-stage" aria-live="polite">
      <div class="orb"><span>{{ isVolcengine ? 'RUN' : progress }}</span><small v-if="!isVolcengine">%</small></div>
      <div class="progress-copy">
        <b>{{ status === 'queued' ? '排队中' : '渲染中' }}</b>
        <div><i :style="isVolcengine ? undefined : { width: `${Math.max(progress, status === 'queued' ? 4 : 1)}%` }"></i></div>
        <small>页面可自由切换，后台会继续生成、下载并归档。</small>
      </div>
    </div>

    <footer>
      <p>{{ prompt }}</p>
      <span>{{ model }}<template v-if="job?.generate_audio"> · AUDIO</template></span>
    </footer>
    <button v-if="requestError && status !== 'failed'" class="retry" type="button" @click="refresh">状态同步失败 · 重试</button>
  </article>
</template>

<style scoped>
.video-card{--acid:#d9ff36;position:relative;margin:12px 0;border:1px solid #aaa69d;background:#171716;color:#eeece6;overflow:hidden}.video-card>header{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid #383735}.video-card>header div{display:flex;align-items:center;gap:12px}.video-card>header span,.video-card>header i,.video-card footer span{color:#77736d;font:7px 'DM Mono';font-style:normal;letter-spacing:.12em}.video-card>header b{font:500 9px 'DM Mono';color:var(--acid)}.progress-stage{min-height:184px;display:grid;grid-template-columns:92px minmax(0,1fr);align-items:center;gap:27px;padding:24px;background:radial-gradient(circle at 11% 45%,rgba(217,255,54,.11),transparent 23%),repeating-linear-gradient(90deg,transparent,transparent 31px,rgba(255,255,255,.018) 32px)}.orb{width:80px;height:80px;display:flex;align-items:baseline;justify-content:center;border:1px solid #55524c;border-radius:50%;box-shadow:inset 0 0 0 8px #20201e,0 0 34px rgba(217,255,54,.08)}.orb span{font:600 27px Manrope}.orb small{color:var(--acid);font:8px 'DM Mono'}.progress-copy>b{font:600 20px Manrope}.progress-copy>div{height:3px;margin:14px 0 10px;background:#343331;overflow:hidden}.progress-copy>div i{display:block;height:100%;background:var(--acid);box-shadow:0 0 12px var(--acid);transition:width .6s ease}.progress-copy>small{color:#77736d;font:8px/1.5 'DM Mono'}.in_progress .orb{animation:breathe 1.8s ease-in-out infinite}.video-stage{position:relative;background:#090909}.video-stage video{display:block;width:100%;max-height:520px;aspect-ratio:16/9;object-fit:contain}.video-stage a{position:absolute;right:10px;bottom:10px;padding:8px 10px;background:rgba(15,15,15,.86);border:1px solid #5b5852;color:var(--acid);text-decoration:none;font:8px 'DM Mono'}.failed-stage{min-height:150px;display:grid;align-content:center;gap:8px;padding:25px;background:repeating-linear-gradient(135deg,#181716,#181716 12px,#1e1c1a 12px,#1e1c1a 24px)}.failed-stage strong{color:#ff806f;font-size:17px}.failed-stage p{max-width:650px;margin:0;color:#99948a;font:9px/1.6 'DM Mono'}.video-card footer{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:15px;padding:12px 14px;border-top:1px solid #383735}.video-card footer p{margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#aaa69d;font-size:9px}.retry{width:100%;border:0;border-top:1px solid #403e39;background:#211d1b;color:#e69375;padding:8px;font:8px 'DM Mono';cursor:pointer}@keyframes breathe{50%{box-shadow:inset 0 0 0 8px #20201e,0 0 42px rgba(217,255,54,.2)}}@media(max-width:560px){.progress-stage{grid-template-columns:1fr;gap:14px}.orb{width:66px;height:66px}.video-card footer{grid-template-columns:1fr}.video-card footer span{display:none}}
.indeterminate .progress-copy>div i{width:34%;animation:videoScan 1.35s ease-in-out infinite}.indeterminate .orb span{color:var(--acid);font:700 14px 'DM Mono';letter-spacing:.13em}@keyframes videoScan{0%{transform:translateX(-115%)}100%{transform:translateX(300%)}}
</style>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  cancelAutoInputJob,
  getActiveAutoInputJob,
  getAutoInputJob,
  startAutoInputJob,
} from '@/api/toolbox-system'
import type { AutoInputJob } from '@/api/toolbox-system-types'
import { autoInputProgress, isAutoInputActive, normalizeTextFile } from '@/toolbox/auto-input'


const router = useRouter()
const text = ref('')
const delaySeconds = ref(0.05)
const countdownSeconds = ref(5)
const job = ref<AutoInputJob | null>(null)
const error = ref('')
const starting = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
let pollTimer: number | undefined

const active = computed(() => job.value ? isAutoInputActive(job.value.status) : false)
const progress = computed(() => job.value ? autoInputProgress(job.value) : 0)
const statusCopy = computed(() => {
  if (!job.value) return 'IDLE'
  return {
    countdown: `T-${job.value.countdown_remaining}`,
    running: 'TYPING',
    completed: 'COMPLETE',
    cancelled: 'CANCELLED',
    failed: 'FAILED',
  }[job.value.status]
})

function stopPolling() {
  if (pollTimer !== undefined) window.clearInterval(pollTimer)
  pollTimer = undefined
}

function poll(jobId: string) {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    try {
      job.value = await getAutoInputJob(jobId)
      if (!isAutoInputActive(job.value.status)) stopPolling()
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : '读取任务状态失败'
      stopPolling()
    }
  }, 250)
}

async function restoreActive() {
  try {
    const restored = await getActiveAutoInputJob()
    if (restored) {
      job.value = restored
      poll(restored.id)
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '读取活动任务失败'
  }
}

async function startTyping() {
  if (!text.value.trim() || active.value || starting.value) return
  starting.value = true
  error.value = ''
  try {
    job.value = await startAutoInputJob({
      text: text.value,
      delay_seconds: delaySeconds.value,
      countdown_seconds: countdownSeconds.value,
    })
    poll(job.value.id)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '自动输入启动失败'
  } finally {
    starting.value = false
  }
}

async function cancelTyping() {
  if (!job.value || !active.value) return
  try {
    job.value = await cancelAutoInputJob(job.value.id)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '取消任务失败'
  }
}

async function loadTextFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    text.value = normalizeTextFile(await file.text())
    error.value = ''
  } catch {
    error.value = '文本文件读取失败，请确认文件为 UTF-8 编码'
  } finally {
    input.value = ''
  }
}

onMounted(restoreActive)
onBeforeUnmount(stopPolling)
</script>

<template>
  <main class="auto-type-page">
    <div class="scanlines" aria-hidden="true"></div>
    <header class="topline">
      <button class="brand" @click="router.push('/toolbox')"><i></i>AGENTBI <span>/ TOOLBOX</span></button>
      <div class="utility"><span>UTILITY 03</span><strong>AUTO TYPE</strong><b :class="{ live: active }">{{ statusCopy }}</b></div>
      <button class="back" @click="router.push('/toolbox')">返回工具箱 ↗</button>
    </header>

    <section class="workbench">
      <aside class="control-panel">
        <header><span>INPUT SEQUENCER</span><strong>把文字交给键盘。</strong><p>启动后，在倒计时结束前切换到目标窗口并将光标放入输入框。</p></header>

        <div class="control-section">
          <div class="section-label"><b>01</b><span>速度 / SPEED</span><output>{{ delaySeconds.toFixed(2) }} s</output></div>
          <input v-model.number="delaySeconds" type="range" min="0" max="2" step="0.01" :disabled="active">
          <div class="ticks"><span>即刻</span><span>1 秒</span><span>2 秒</span></div>
        </div>

        <div class="control-section">
          <div class="section-label"><b>02</b><span>切换窗口倒计时</span><output>{{ countdownSeconds }} s</output></div>
          <input v-model.number="countdownSeconds" type="range" min="1" max="30" step="1" :disabled="active">
          <div class="ticks"><span>1 秒</span><span>15 秒</span><span>30 秒</span></div>
        </div>

        <div class="file-loader">
          <input ref="fileInput" type="file" accept=".txt,text/plain" hidden @change="loadTextFile">
          <button :disabled="active" @click="fileInput?.click()"><span>TXT</span><div><strong>载入文本文件</strong><small>仅在浏览器内读取，不上传文件</small></div><b>＋</b></button>
        </div>

        <div v-if="error" class="error-line">{{ error }}</div>

        <div class="launch-zone">
          <button v-if="!active" class="launch" :disabled="!text.trim() || starting" @click="startTyping"><span>{{ starting ? 'ARMING…' : 'START' }}</span><strong>{{ starting ? '正在启动' : '开始自动输入' }}</strong><i>↗</i></button>
          <button v-else class="cancel" @click="cancelTyping"><span>EMERGENCY STOP</span><strong>中止输入</strong><i>×</i></button>
          <p>输入期间不要操作键盘或鼠标。任务只作用于当前获得焦点的窗口。</p>
        </div>
      </aside>

      <section class="editor-deck">
        <header>
          <div><span>MASTER TEXT</span><strong>字符序列编辑器</strong></div>
          <div class="counter"><b>{{ text.length.toLocaleString() }}</b><span>/ 100,000 CHARS</span></div>
        </header>
        <div class="editor-shell" :class="{ active }">
          <textarea v-model="text" :disabled="active" maxlength="100000" spellcheck="false" placeholder="在这里粘贴或编写要输入的文本……"></textarea>
          <div class="cursor-mark" aria-hidden="true"></div>

          <transition name="veil">
            <div v-if="active" class="progress-veil">
              <div class="target-ring"><i></i><b></b><span>{{ job?.status === 'countdown' ? job.countdown_remaining : `${progress}%` }}</span></div>
              <small>{{ job?.status === 'countdown' ? 'SWITCH WINDOW NOW' : 'KEYBOARD STREAM ACTIVE' }}</small>
              <strong>{{ job?.status === 'countdown' ? '现在切换到目标窗口' : '正在逐字输入' }}</strong>
              <p>{{ job?.typed_characters || 0 }} / {{ job?.total_characters || 0 }} CHARACTERS</p>
            </div>
          </transition>
        </div>

        <footer class="status-rail">
          <div><span>CHANNEL</span><strong>{{ statusCopy }}</strong></div>
          <i><b :style="{ width: `${progress}%` }"></b></i>
          <div><span>DELAY</span><strong>{{ delaySeconds.toFixed(2) }} SEC</strong></div>
        </footer>
      </section>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@500;600;700&display=swap');
*{box-sizing:border-box}.auto-type-page{--ink:#10110f;--panel:#171816;--line:#35362f;--paper:#ecebe3;--cyan:#8fffe4;--coral:#ff674a;position:relative;min-height:100vh;overflow-x:hidden;background:var(--ink);color:var(--paper);padding:0 clamp(18px,4vw,62px) 48px;font-family:Manrope,sans-serif}.scanlines{position:fixed;inset:0;pointer-events:none;opacity:.08;background:repeating-linear-gradient(0deg,transparent 0 3px,#b5ffe7 4px)}button{font:inherit}.topline{height:78px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;border-bottom:1px solid var(--line)}.topline button{border:0;background:none;color:inherit;cursor:pointer}.brand{justify-self:start;display:flex;align-items:center;gap:9px;font:700 10px 'DM Mono';letter-spacing:.13em}.brand i{width:15px;height:15px;border:1px solid var(--cyan);box-shadow:4px 4px 0 -2px var(--cyan)}.brand span,.back{color:#71736b}.utility{display:flex;align-items:center;gap:15px;font-family:'DM Mono'}.utility span{color:#64665f;font-size:8px;letter-spacing:.15em}.utility strong{font-size:11px;letter-spacing:.16em}.utility b{padding:5px 8px;background:#252620;color:#8a8c83;font-size:7px;letter-spacing:.1em}.utility b.live{background:var(--cyan);color:var(--ink)}.back{justify-self:end;font:8px 'DM Mono';letter-spacing:.08em}.workbench{display:grid;grid-template-columns:minmax(310px,.62fr) minmax(0,1.38fr);min-height:calc(100vh - 126px);max-width:1500px;margin:28px auto 0;border:1px solid var(--line)}.control-panel{padding:30px;background:#151613;border-right:1px solid var(--line)}.control-panel>header span{color:var(--cyan);font:8px 'DM Mono';letter-spacing:.15em}.control-panel>header strong{display:block;margin-top:21px;font-size:28px;letter-spacing:-.04em}.control-panel>header p{margin:12px 0 0;max-width:350px;color:#777970;font-size:9px;line-height:1.7}.control-section{margin-top:33px;padding-top:17px;border-top:1px solid #30322c}.section-label{display:grid;grid-template-columns:28px 1fr auto;align-items:center;gap:9px}.section-label b{display:grid;place-items:center;width:25px;height:25px;border:1px solid #3d3f38;color:#6f7169;font:7px 'DM Mono'}.section-label span{font-size:10px}.section-label output{color:var(--cyan);font:10px 'DM Mono'}.control-section input[type=range]{width:100%;height:3px;margin:21px 0 8px;appearance:none;background:#3b3d36;accent-color:var(--cyan)}.control-section input[type=range]::-webkit-slider-thumb{appearance:none;width:13px;height:13px;border:3px solid var(--ink);background:var(--cyan);box-shadow:0 0 0 1px var(--cyan);cursor:pointer}.ticks{display:flex;justify-content:space-between;color:#5e6058;font:7px 'DM Mono'}.file-loader{margin-top:29px}.file-loader button{display:grid;grid-template-columns:34px 1fr auto;align-items:center;gap:12px;width:100%;padding:13px;border:1px solid #363832;background:#1c1d1a;color:var(--paper);text-align:left;cursor:pointer}.file-loader button>span{display:grid;place-items:center;height:34px;border:1px solid #474941;color:var(--cyan);font:7px 'DM Mono'}.file-loader button div{display:grid;gap:3px}.file-loader strong{font-size:10px}.file-loader small{color:#686a62;font-size:8px}.file-loader button>b{color:var(--cyan);font:19px 'DM Mono'}.error-line{margin-top:15px;padding:10px;border-left:2px solid var(--coral);background:#261915;color:#ff9b87;font-size:9px;line-height:1.5}.launch-zone{margin-top:31px}.launch-zone>button{position:relative;width:100%;padding:17px;text-align:left;cursor:pointer}.launch{border:1px solid var(--cyan);background:var(--cyan);color:var(--ink)}.cancel{border:1px solid var(--coral);background:var(--coral);color:#160e0c}.launch-zone button span{display:block;font:7px 'DM Mono';letter-spacing:.14em}.launch-zone button strong{display:block;margin-top:7px;font-size:15px}.launch-zone button i{position:absolute;right:17px;top:50%;transform:translateY(-50%);font:22px 'DM Mono';font-style:normal}.launch-zone button:disabled{opacity:.3;cursor:not-allowed}.launch-zone>p{color:#5f615a;font-size:8px;line-height:1.55}.editor-deck{min-width:0;padding:28px;background:#e8e7df;color:#151612}.editor-deck>header{display:flex;justify-content:space-between;align-items:end;padding-bottom:22px;border-bottom:1px solid #c7c6be}.editor-deck>header div:first-child{display:grid;gap:5px}.editor-deck>header span{color:#77786f;font:7px 'DM Mono';letter-spacing:.14em}.editor-deck>header strong{font-size:18px}.counter{display:flex;align-items:baseline;gap:7px}.counter b{font:19px 'DM Mono'}.editor-shell{position:relative;min-height:560px;margin-top:22px;border:1px solid #c6c5bc;background:#efeee7;overflow:hidden}.editor-shell:before{content:'';position:absolute;left:46px;top:0;bottom:0;width:1px;background:#d2d1c8}.editor-shell textarea{position:absolute;inset:0;width:100%;height:100%;resize:none;border:0;outline:0;background:transparent;color:#171813;padding:31px 35px 31px 69px;font:13px/1.85 'DM Mono';caret-color:#ff4e30}.editor-shell textarea::placeholder{color:#aaa9a0}.cursor-mark{position:absolute;right:18px;top:18px;width:9px;height:22px;background:var(--coral);animation:blink 1s steps(1) infinite}.progress-veil{position:absolute;inset:0;z-index:3;display:grid;place-content:center;justify-items:center;background:rgba(15,17,14,.94);color:var(--paper);text-align:center}.target-ring{position:relative;display:grid;place-items:center;width:178px;height:178px;margin-bottom:28px;border:1px solid #4b5148;border-radius:50%}.target-ring:before,.target-ring:after{content:'';position:absolute;background:#4b5148}.target-ring:before{width:210px;height:1px}.target-ring:after{width:1px;height:210px}.target-ring i{position:absolute;inset:14px;border:1px dashed var(--cyan);border-radius:50%;animation:spin 8s linear infinite}.target-ring b{position:absolute;inset:35px;border:1px solid #485148;border-radius:50%}.target-ring span{position:relative;z-index:1;color:var(--cyan);font:33px 'DM Mono'}.progress-veil>small{color:var(--cyan);font:7px 'DM Mono';letter-spacing:.18em}.progress-veil>strong{margin-top:9px;font-size:18px}.progress-veil>p{color:#777f76;font:8px 'DM Mono';letter-spacing:.1em}.status-rail{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:18px;margin-top:18px}.status-rail div{display:grid;gap:3px}.status-rail span{color:#85867d;font:7px 'DM Mono';letter-spacing:.12em}.status-rail strong{font:9px 'DM Mono'}.status-rail>i{height:3px;background:#cac9c0}.status-rail>i b{display:block;height:100%;background:#151612;transition:width .2s}.veil-enter-active,.veil-leave-active{transition:opacity .25s}.veil-enter-from,.veil-leave-to{opacity:0}@keyframes blink{50%{opacity:0}}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:920px){.topline{grid-template-columns:1fr auto}.utility{display:none}.workbench{grid-template-columns:1fr}.control-panel{border-right:0;border-bottom:1px solid var(--line)}.editor-shell{min-height:440px}}@media(max-width:580px){.auto-type-page{padding-inline:12px}.back{font-size:0}.back:after{content:'↗';font-size:12px}.workbench{margin-top:14px}.control-panel,.editor-deck{padding:18px}.editor-deck>header{align-items:start}.counter{display:grid;text-align:right}.editor-shell textarea{padding-left:45px}.editor-shell:before{left:27px}.status-rail{grid-template-columns:1fr}.status-rail>i{grid-row:1;grid-column:1}.status-rail div:last-child{text-align:right}}
</style>

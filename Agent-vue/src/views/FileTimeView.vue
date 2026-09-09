<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import {
  getFileTimeJob,
  previewFileTime,
  selectNativeDirectory,
  startFileTimeJob,
} from '@/api/toolbox-system'
import type {
  FileTimeJob,
  FileTimeOperation,
  FileTimePayload,
  FileTimePreview,
} from '@/api/toolbox-system-types'
import { fileTimeProgress, requiresDateRange, requiresOutput } from '@/toolbox/file-time'


const router = useRouter()
const operations: Array<{ id: FileTimeOperation; index: string; title: string; note: string }> = [
  { id: 'creation_from_modified', index: '01', title: '创建时间 ← 修改时间', note: '用最后修改时间覆盖 Windows 创建时间' },
  { id: 'modified_from_creation', index: '02', title: '修改时间 ← 创建时间', note: '让最后修改时间回到文件创建时刻' },
  { id: 'filename_to_creation', index: '03', title: '从文件名恢复时间', note: '识别日期；无法识别的文件移至输出目录' },
  { id: 'move_by_creation_range', index: '04', title: '按创建日期移动', note: '筛选日期区间并保留原目录结构' },
]

const operation = ref<FileTimeOperation>('creation_from_modified')
const inputDirectory = ref('')
const outputDirectory = ref('')
const startDate = ref('')
const endDate = ref('')
const preview = ref<FileTimePreview | null>(null)
const job = ref<FileTimeJob | null>(null)
const busy = ref<'input' | 'output' | 'preview' | 'execute' | ''>('')
const error = ref('')
let pollTimer: number | undefined

const needsOutput = computed(() => requiresOutput(operation.value))
const needsDates = computed(() => requiresDateRange(operation.value))
const canPreview = computed(() => Boolean(
  inputDirectory.value.trim()
  && (!needsOutput.value || outputDirectory.value.trim())
  && (!needsDates.value || (startDate.value && endDate.value)),
))
const progress = computed(() => job.value ? fileTimeProgress(job.value) : 0)
const isRunning = computed(() => job.value?.status === 'queued' || job.value?.status === 'running')

const payload = (): FileTimePayload => ({
  operation: operation.value,
  input_directory: inputDirectory.value.trim(),
  output_directory: needsOutput.value ? outputDirectory.value.trim() : null,
  start_date: needsDates.value ? startDate.value : null,
  end_date: needsDates.value ? endDate.value : null,
})

watch([operation, inputDirectory, outputDirectory, startDate, endDate], () => {
  preview.value = null
  error.value = ''
})

async function chooseDirectory(target: 'input' | 'output') {
  busy.value = target
  error.value = ''
  try {
    const current = target === 'input' ? inputDirectory.value : outputDirectory.value
    const result = await selectNativeDirectory({
      title: target === 'input' ? '选择输入目录' : '选择输出目录',
      initial_directory: current || null,
    })
    if (!result.cancelled && result.path) {
      if (target === 'input') inputDirectory.value = result.path
      else outputDirectory.value = result.path
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '无法选择目录'
  } finally {
    busy.value = ''
  }
}

async function scanPreview() {
  if (!canPreview.value || isRunning.value) return
  busy.value = 'preview'
  error.value = ''
  job.value = null
  try {
    preview.value = await previewFileTime(payload())
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '扫描失败'
  } finally {
    busy.value = ''
  }
}

function stopPolling() {
  if (pollTimer !== undefined) window.clearInterval(pollTimer)
  pollTimer = undefined
}

function pollJob(jobId: string) {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    try {
      job.value = await getFileTimeJob(jobId)
      if (job.value.status === 'completed' || job.value.status === 'failed') stopPolling()
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : '读取任务状态失败'
      stopPolling()
    }
  }, 500)
}

async function execute() {
  if (!preview.value || isRunning.value) return
  busy.value = 'execute'
  error.value = ''
  try {
    job.value = await startFileTimeJob(payload())
    pollJob(job.value.id)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '任务启动失败'
  } finally {
    busy.value = ''
  }
}

onBeforeUnmount(stopPolling)
</script>

<template>
  <main class="file-time-page">
    <div class="noise" aria-hidden="true"></div>
    <header class="topline">
      <button class="brand" @click="router.push('/toolbox')"><i></i>AGENTBI <span>/ TOOLBOX</span></button>
      <div class="utility"><span>UTILITY 02</span><strong>FILE TIME</strong><b :class="{ live: isRunning }">{{ isRunning ? 'PROCESSING' : 'LOCAL READY' }}</b></div>
      <button class="back" @click="router.push('/toolbox')">返回工具箱 ↗</button>
    </header>

    <section class="workspace">
      <aside class="control-rack">
        <div class="section-title"><span>01</span><div><small>OPERATION</small><strong>选择动作</strong></div></div>
        <div class="operation-list">
          <button v-for="item in operations" :key="item.id" :class="{ active: operation === item.id }" :disabled="isRunning" @click="operation = item.id">
            <span>{{ item.index }}</span><div><strong>{{ item.title }}</strong><small>{{ item.note }}</small></div><i></i>
          </button>
        </div>

        <div class="section-title path-title"><span>02</span><div><small>PATH MATRIX</small><strong>目录映射</strong></div></div>
        <label class="path-field">
          <span>输入目录</span>
          <div><input v-model="inputDirectory" :disabled="isRunning" placeholder="选择或粘贴本地目录路径"><button :disabled="isRunning || Boolean(busy)" @click.prevent="chooseDirectory('input')">{{ busy === 'input' ? '打开中' : '选择' }}</button></div>
        </label>
        <label v-if="needsOutput" class="path-field">
          <span>输出目录</span>
          <div><input v-model="outputDirectory" :disabled="isRunning" placeholder="未识别或筛选出的文件将移动到这里"><button :disabled="isRunning || Boolean(busy)" @click.prevent="chooseDirectory('output')">{{ busy === 'output' ? '打开中' : '选择' }}</button></div>
        </label>
        <div v-if="needsDates" class="date-grid">
          <label><span>开始日期</span><input v-model="startDate" type="date" :disabled="isRunning"></label>
          <label><span>结束日期</span><input v-model="endDate" type="date" :disabled="isRunning"></label>
        </div>

        <p v-if="error" class="error-line">{{ error }}</p>
        <div class="action-row">
          <button class="scan" :disabled="!canPreview || Boolean(busy) || isRunning" @click="scanPreview">{{ busy === 'preview' ? '正在扫描…' : '扫描预览' }}</button>
          <button class="execute" :disabled="!preview || Boolean(busy) || isRunning" @click="execute">{{ busy === 'execute' ? '启动中…' : '确认执行' }}</button>
        </div>
      </aside>

      <section class="report-deck">
        <header>
          <div><span>SCAN / EXECUTION REPORT</span><strong>{{ preview ? '目录已建立索引' : '等待扫描目录' }}</strong></div>
          <code>{{ operation.toUpperCase() }}</code>
        </header>

        <div v-if="!preview && !job" class="empty-state">
          <div class="clock-graphic" aria-hidden="true"><i></i><b></b><span v-for="n in 12" :key="n" :style="{ transform: `rotate(${n * 30}deg)` }"></span></div>
          <p>选择动作和目录后进行扫描。<br>预览只读取文件信息，不会修改任何内容。</p>
        </div>

        <template v-else>
          <div class="metric-grid">
            <article><span>TOTAL</span><strong>{{ job?.total_files ?? preview?.total_files ?? 0 }}</strong><small>扫描文件</small></article>
            <article><span>UPDATE</span><strong>{{ job?.updated_count ?? preview?.update_count ?? 0 }}</strong><small>更新时间</small></article>
            <article><span>MOVE</span><strong>{{ job?.moved_count ?? preview?.move_count ?? 0 }}</strong><small>移动文件</small></article>
            <article :class="{ alert: (job?.failed_count ?? 0) > 0 }"><span>{{ job ? 'FAILED' : 'SKIP' }}</span><strong>{{ job?.failed_count ?? preview?.skip_count ?? 0 }}</strong><small>{{ job ? '处理失败' : '预计跳过' }}</small></article>
          </div>

          <div v-if="job" class="progress-module">
            <div><span>{{ job.status.toUpperCase() }}</span><strong>{{ progress }}%</strong></div>
            <i><b :style="{ width: `${progress}%` }"></b></i>
            <small>{{ job.processed_files }} / {{ job.total_files }} FILES</small>
          </div>

          <div class="path-report">
            <div class="report-title"><span>{{ job?.errors.length ? 'ERROR LOG' : 'SAMPLE PATHS' }}</span><b>{{ job?.errors.length || preview?.examples.length || 0 }}</b></div>
            <ol v-if="job?.errors.length"><li v-for="(item, index) in job.errors" :key="item"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ item }}</li></ol>
            <ol v-else><li v-for="(item, index) in preview?.examples || []" :key="item"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ item }}</li></ol>
          </div>
        </template>
      </section>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@500;600;700&display=swap');
*{box-sizing:border-box}.file-time-page{--ink:#11120f;--panel:#181916;--line:#35372f;--paper:#e9e8df;--acid:#d8ff3e;--orange:#ff7043;position:relative;min-height:100vh;overflow-x:hidden;background:var(--ink);color:var(--paper);padding:0 clamp(18px,4vw,62px) 48px;font-family:Manrope,sans-serif}.noise{position:fixed;inset:0;pointer-events:none;opacity:.07;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 160 160' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='.8' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}.topline{height:78px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;border-bottom:1px solid var(--line)}button{font:inherit}.topline button{border:0;background:none;color:inherit;cursor:pointer}.brand{justify-self:start;display:flex;align-items:center;gap:9px;font:700 var(--control-font-size) 'DM Mono';letter-spacing:.13em}.brand i{width:15px;height:15px;border:1px solid var(--acid);box-shadow:4px 4px 0 -2px var(--acid)}.brand span,.back{color:#777970}.utility{display:flex;align-items:center;gap:15px;font-family:'DM Mono'}.utility span{color:#64665e;font-size:8px;letter-spacing:.15em}.utility strong{font-size:11px;letter-spacing:.16em}.utility b{padding:5px 8px;background:#252720;color:#8a8d82;font-size:7px;letter-spacing:.1em}.utility b.live{background:var(--acid);color:var(--ink)}.back{justify-self:end;font:var(--control-font-size) 'DM Mono';letter-spacing:.08em}.workspace{display:grid;grid-template-columns:minmax(350px,.72fr) minmax(0,1.28fr);min-height:calc(100vh - 126px);max-width:1500px;margin:28px auto 0;border:1px solid var(--line)}.control-rack{padding:27px;background:#151613;border-right:1px solid var(--line)}.section-title{display:flex;align-items:center;gap:12px;margin-bottom:15px}.section-title>span{display:grid;place-items:center;width:28px;height:28px;border:1px solid #46483f;color:var(--acid);font:8px 'DM Mono'}.section-title div{display:grid;gap:2px}.section-title small,.path-field>span,.date-grid span{color:#6f7169;font:7px 'DM Mono';letter-spacing:.13em}.section-title strong{font-size:13px}.operation-list{display:grid;gap:5px}.operation-list button{display:grid;grid-template-columns:28px 1fr 8px;align-items:center;gap:10px;width:100%;padding:13px;border:1px solid #2d2f29;background:#1b1c19;color:#b0b2a9;text-align:left;cursor:pointer;transition:.2s}.operation-list button:hover{border-color:#56594d}.operation-list button.active{border-color:var(--acid);background:#20231a;color:var(--paper)}.operation-list button>span{font:var(--control-font-size) 'DM Mono';color:#65675f}.operation-list button div{display:grid;gap:4px}.operation-list button strong{font-size:var(--control-font-size)}.operation-list button small{color:#696b64;font-size:var(--control-font-size);line-height:1.35}.operation-list button i{width:6px;height:6px;border:1px solid #5c5e56;border-radius:50%}.operation-list button.active i{border-color:var(--acid);background:var(--acid);box-shadow:0 0 12px var(--acid)}.path-title{margin-top:30px}.path-field{display:grid;gap:7px;margin-bottom:12px}.path-field>div{display:grid;grid-template-columns:1fr auto;border:1px solid #34362f;background:#0e0f0d}.path-field input,.date-grid input{min-width:0;border:0;outline:0;background:transparent;color:var(--paper);padding:11px;font:9px 'DM Mono'}.path-field button{border:0;border-left:1px solid #34362f;background:#252820;color:var(--acid);padding:0 14px;cursor:pointer;font:var(--control-font-size) 'DM Mono'}.date-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.date-grid label{display:grid;gap:7px}.date-grid input{border:1px solid #34362f;color-scheme:dark}.error-line{margin:15px 0 0;padding:10px;border-left:2px solid var(--orange);background:#251915;color:#ff9a79;font-size:9px;line-height:1.5}.action-row{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:22px}.action-row button{padding:13px;border:1px solid #3b3d36;cursor:pointer;font:var(--control-font-size) 'DM Mono';letter-spacing:.08em}.action-row button:disabled{opacity:.32;cursor:not-allowed}.scan{background:transparent;color:var(--paper)}.execute{background:var(--acid);border-color:var(--acid)!important;color:var(--ink)}.report-deck{min-width:0;padding:28px;background:#ebeae2;color:#141511}.report-deck>header{display:flex;justify-content:space-between;gap:20px;padding-bottom:23px;border-bottom:1px solid #c7c6bd}.report-deck>header div{display:grid;gap:5px}.report-deck>header span,.report-deck>header code{color:#797970;font:7px 'DM Mono';letter-spacing:.14em}.report-deck>header strong{font-size:18px}.report-deck>header code{align-self:start;padding:7px 9px;border:1px solid #c9c8bf;max-width:44%;overflow:hidden;text-overflow:ellipsis}.empty-state{min-height:560px;display:grid;place-content:center;justify-items:center;gap:35px}.empty-state p{text-align:center;color:#77786f;font:10px/1.8 'DM Mono'}.clock-graphic{position:relative;width:190px;height:190px;border:1px solid #b9b8af;border-radius:50%;box-shadow:inset 0 0 0 19px #e2e1d8}.clock-graphic>span{position:absolute;left:94px;top:6px;width:1px;height:9px;background:#7d7e74;transform-origin:0 89px}.clock-graphic i,.clock-graphic b{position:absolute;left:94px;top:94px;width:1px;background:#151611;transform-origin:bottom}.clock-graphic i{height:58px;transform:translateY(-58px) rotate(43deg)}.clock-graphic b{height:42px;transform:translateY(-42px) rotate(132deg);width:3px}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin-top:26px;background:#c8c7bd;border:1px solid #c8c7bd}.metric-grid article{padding:18px;background:#e6e5dc}.metric-grid article.alert{background:#ffded3}.metric-grid span{font:7px 'DM Mono';letter-spacing:.13em;color:#77786f}.metric-grid strong{display:block;margin:13px 0 3px;font:700 clamp(26px,4vw,48px)/1 Manrope;letter-spacing:-.06em}.metric-grid small{color:#85867d;font-size:8px}.progress-module{margin-top:22px;padding:18px;background:#151611;color:#e6e5dd}.progress-module>div{display:flex;justify-content:space-between;align-items:center}.progress-module span,.progress-module small{font:7px 'DM Mono';letter-spacing:.13em;color:#888a80}.progress-module strong{color:var(--acid);font:20px 'DM Mono'}.progress-module>i{display:block;height:3px;margin:14px 0 9px;background:#3c3e36}.progress-module>i b{display:block;height:100%;background:var(--acid);transition:width .35s}.path-report{margin-top:22px;border-top:1px solid #c7c6bd}.report-title{display:flex;justify-content:space-between;padding:15px 0;color:#74756d;font:8px 'DM Mono';letter-spacing:.12em}.report-title b{color:#161711}.path-report ol{list-style:none;padding:0;margin:0;max-height:330px;overflow:auto;border-bottom:1px solid #cecdc4}.path-report li{display:grid;grid-template-columns:34px 1fr;gap:9px;padding:10px 0;border-top:1px solid #d2d1c8;font:9px 'DM Mono';overflow-wrap:anywhere}.path-report li span{color:#94958c}@media(max-width:920px){.topline{grid-template-columns:1fr auto}.utility{display:none}.workspace{grid-template-columns:1fr}.control-rack{border-right:0;border-bottom:1px solid var(--line)}.empty-state{min-height:340px}}@media(max-width:580px){.file-time-page{padding-inline:12px}.back{font-size:0}.back:after{content:'↗';font-size:12px}.workspace{margin-top:14px}.control-rack,.report-deck{padding:18px}.date-grid,.action-row{grid-template-columns:1fr}.metric-grid{grid-template-columns:1fr 1fr}.metric-grid strong{font-size:30px}}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  deleteMoegirlArtifact,
  downloadMoegirlArtifact,
  fetchMoegirlPage,
  getMoegirlArtifact,
  listMoegirlArtifacts,
  refineMoegirlArtifact,
} from '@/api/toolbox-moegirl'
import type {
  MoegirlArtifactDocument,
  MoegirlArtifactSummary,
  MoegirlFetchResult,
} from '@/api/toolbox-moegirl-types'
import { useWorkspaceStore } from '@/stores/workspace'
import {
  acceptArchiveResponse,
  applyFetchResult,
  archiveDeleteUnavailable,
  archiveFetchUnavailable,
  beginArchiveRequest,
  removeArtifact,
  selectFallbackArtifact,
} from '@/toolbox/moegirl-archive'
import { renderMarkdown } from '@/utils/markdown'


interface PreviewState {
  kind: 'saved' | 'disambiguation'
  artifactId: string | null
  title: string
  sourceUrl: string
  markdown: string
  message: string
}

type StateRequestKind = 'history' | 'fetch' | 'open' | 'delete' | 'refine'

interface StateRequest {
  generation: number
  signal: AbortSignal
}

const router = useRouter()
const workspace = useWorkspaceStore()
const userId = computed(() => workspace.userId)

const name = ref('')
const history = ref<MoegirlArtifactSummary[]>([])
const selectedId = ref<string | null>(null)
const preview = ref<PreviewState | null>(null)
const historyLoading = ref(false)
const fetching = ref(false)
const opening = ref(false)
const downloading = ref(false)
const deleting = ref(false)
const refining = ref(false)
const error = ref('')
const notice = ref('')

let archiveGeneration = 0
let stateController: AbortController | null = null

const normalizedName = computed(() => name.value.trim())
const selectedArtifact = computed(() =>
  history.value.find((item) => item.id === selectedId.value) ?? null,
)
const canUseSavedActions = computed(() =>
  preview.value?.kind === 'saved' && Boolean(selectedArtifact.value),
)
const stateBusy = computed(() =>
  historyLoading.value || fetching.value || opening.value || deleting.value || refining.value,
)
const fetchUnavailable = computed(() => archiveFetchUnavailable({
  fetching: fetching.value,
  opening: opening.value,
  deleting: deleting.value,
  refining: refining.value,
}))
const deleteUnavailable = computed(() => archiveDeleteUnavailable({
  historyLoading: historyLoading.value,
  fetching: fetching.value,
  opening: opening.value,
  deleting: deleting.value,
  refining: refining.value,
}))

function readableError(value: unknown): string {
  return value instanceof Error ? value.message : '操作失败，请稍后重试'
}

function documentPreview(document: MoegirlArtifactDocument): PreviewState {
  return {
    kind: 'saved',
    artifactId: document.id,
    title: document.title,
    sourceUrl: document.source_url,
    markdown: document.markdown,
    message: '已从本地归档打开',
  }
}

function resultPreview(result: MoegirlFetchResult): PreviewState {
  return {
    kind: result.kind,
    artifactId: result.artifact?.id ?? null,
    title: result.title,
    sourceUrl: result.source_url,
    markdown: result.markdown,
    message: result.message,
  }
}

function resetFeedback() {
  error.value = ''
  notice.value = ''
}

function beginStateOperation(kind: StateRequestKind): StateRequest {
  stateController?.abort()
  archiveGeneration = beginArchiveRequest(archiveGeneration)
  stateController = new AbortController()
  historyLoading.value = kind === 'history'
  fetching.value = kind === 'fetch'
  opening.value = kind === 'open'
  deleting.value = kind === 'delete'
  refining.value = kind === 'refine'
  return { generation: archiveGeneration, signal: stateController.signal }
}

function requestAccepted(request: StateRequest): boolean {
  return acceptArchiveResponse(request.generation, archiveGeneration)
}

function finishStateOperation(request: StateRequest) {
  if (!requestAccepted(request)) return
  stateController = null
  historyLoading.value = false
  fetching.value = false
  opening.value = false
  deleting.value = false
  refining.value = false
}

function isAbortError(value: unknown): boolean {
  return value instanceof DOMException && value.name === 'AbortError'
}

async function openArtifact(
  artifactId: string,
  options: { preserveFeedback?: boolean } = {},
) {
  if (stateBusy.value) return
  if (!options.preserveFeedback) resetFeedback()
  const request = beginStateOperation('open')
  try {
    const document = await getMoegirlArtifact(artifactId, userId.value, request.signal)
    if (!requestAccepted(request)) return
    selectedId.value = document.id
    preview.value = documentPreview(document)
  } catch (value) {
    if (requestAccepted(request) && !isAbortError(value)) error.value = readableError(value)
  } finally {
    finishStateOperation(request)
  }
}

async function loadHistory() {
  if (stateBusy.value) return
  resetFeedback()
  const request = beginStateOperation('history')
  let fallbackId: string | null = null
  try {
    const items = await listMoegirlArtifacts(userId.value, request.signal)
    if (!requestAccepted(request)) return
    history.value = items
    const current = items.find((item) => item.id === selectedId.value)
    const currentPreviewIsConsistent = current && preview.value?.artifactId === current.id
    const preserveDisambiguation = preview.value?.kind === 'disambiguation' && !selectedId.value
    if (!currentPreviewIsConsistent && !preserveDisambiguation) {
      const fallback = current ?? selectFallbackArtifact(items)
      selectedId.value = null
      preview.value = null
      fallbackId = fallback?.id ?? null
    }
  } catch (value) {
    if (requestAccepted(request) && !isAbortError(value)) error.value = readableError(value)
  } finally {
    finishStateOperation(request)
  }
  if (fallbackId && acceptArchiveResponse(request.generation, archiveGeneration)) {
    await openArtifact(fallbackId)
  }
}

async function runFetch(requestedName = normalizedName.value) {
  if (fetchUnavailable.value) return
  const requestName = requestedName.trim()
  resetFeedback()
  if (!requestName) {
    error.value = '请输入萌娘百科页面名称'
    return
  }
  if (requestName.length > 200) {
    error.value = '页面名称不能超过 200 个字符'
    return
  }

  const request = beginStateOperation('fetch')
  try {
    const result = await fetchMoegirlPage(
      { user_id: userId.value, name: requestName },
      request.signal,
    )
    if (!requestAccepted(request)) return
    history.value = applyFetchResult(history.value, result)
    selectedId.value = result.artifact?.id ?? null
    preview.value = resultPreview(result)
    notice.value = result.message
  } catch (value) {
    if (requestAccepted(request) && !isAbortError(value)) error.value = readableError(value)
  } finally {
    finishStateOperation(request)
  }
}

async function refreshSelected() {
  if (!selectedArtifact.value || stateBusy.value) return
  name.value = selectedArtifact.value.requested_name
  await runFetch(selectedArtifact.value.requested_name)
}

async function downloadSelected() {
  if (!selectedArtifact.value || downloading.value || stateBusy.value) return
  resetFeedback()
  downloading.value = true
  try {
    const result = await downloadMoegirlArtifact(selectedArtifact.value.id, userId.value)
    const url = URL.createObjectURL(result.blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = result.filename
    anchor.click()
    URL.revokeObjectURL(url)
    notice.value = `已准备下载：${result.filename}`
  } catch (value) {
    error.value = readableError(value)
  } finally {
    downloading.value = false
  }
}

async function refineSelected() {
  const artifact = selectedArtifact.value
  if (!artifact || stateBusy.value) return

  resetFeedback()
  const request = beginStateOperation('refine')
  try {
    const document = await refineMoegirlArtifact(artifact.id, userId.value, request.signal)
    if (!requestAccepted(request)) return
    history.value = [document, ...history.value.filter((item) => item.id !== document.id)]
    selectedId.value = document.id
    preview.value = documentPreview(document)
    notice.value = `AI 精炼完成：${document.title}`
  } catch (value) {
    if (requestAccepted(request) && !isAbortError(value)) error.value = readableError(value)
  } finally {
    finishStateOperation(request)
  }
}

async function deleteSelected() {
  const artifact = selectedArtifact.value
  if (!artifact || deleteUnavailable.value) return
  if (!window.confirm(`删除本地归档「${artifact.title}」？此操作无法撤销。`)) return

  resetFeedback()
  const request = beginStateOperation('delete')
  let fallbackId: string | null = null
  let deleted = false
  try {
    await deleteMoegirlArtifact(artifact.id, userId.value, request.signal)
    if (!requestAccepted(request)) return
    const next = removeArtifact(history.value, selectedId.value, artifact.id)
    history.value = next.history
    selectedId.value = next.selectedId
    preview.value = null
    notice.value = `已删除「${artifact.title}」`
    fallbackId = next.selectedId
    deleted = true
  } catch (value) {
    if (requestAccepted(request) && !isAbortError(value)) error.value = readableError(value)
  } finally {
    finishStateOperation(request)
  }
  if (deleted && fallbackId && acceptArchiveResponse(request.generation, archiveGeneration)) {
    await openArtifact(fallbackId, { preserveFeedback: true })
  }
}

onMounted(() => {
  void loadHistory()
})
</script>

<template>
  <main class="archive-page">
    <div class="grain" aria-hidden="true"></div>

    <header class="archive-nav">
      <button class="wordmark" type="button" @click="router.push('/toolbox')">
        <i></i>AGENTBI <span>/ MOE ARCHIVE</span>
      </button>
      <div class="nav-meta">
        <span>LOCAL KNOWLEDGE UNIT</span>
        <button type="button" @click="router.push('/toolbox')">← TOOLBOX</button>
      </div>
    </header>

    <section class="archive-heading">
      <div>
        <p>04 / KNOWLEDGE · MOEGIRLPEDIA</p>
        <h1>MOE<br><em>ARCHIVE</em></h1>
      </div>
      <aside>
        <b>网页正文 → Markdown</b>
        <span>规则清洗 · AI 精炼可选 · 本地持久化</span>
        <span class="user-stamp">USER / {{ userId }}</span>
      </aside>
    </section>

    <section class="workbench" :aria-busy="stateBusy">
      <aside class="control-rail">
        <form class="fetch-form" @submit.prevent="runFetch()">
          <label for="moegirl-page-name">PAGE NAME / 页面名称</label>
          <div class="input-line">
            <span>→</span>
            <input
              id="moegirl-page-name"
              v-model="name"
              maxlength="200"
              autocomplete="off"
              placeholder="例如：雷电芽衣"
            >
          </div>
          <button class="fetch-button" type="submit" :disabled="fetchUnavailable || !normalizedName">
            <span>{{ fetching ? 'FETCHING PAGE' : 'FETCH & ARCHIVE' }}</span>
            <b>{{ fetching ? '···' : '↗' }}</b>
          </button>
          <div v-if="fetching" class="fetch-progress" role="progressbar" aria-label="正在抓取页面">
            <i></i>
          </div>
        </form>

        <div class="feedback" aria-live="polite">
          <p v-if="error" class="error-message"><b>ERROR</b>{{ error }}</p>
          <p v-else-if="notice" class="notice-message"><b>STATUS</b>{{ notice }}</p>
          <p v-else><b>READY</b>输入精确页面名，不需要粘贴 URL。</p>
        </div>

        <section class="history-panel">
          <header>
            <div><span>LOCAL INDEX</span><strong>SAVED / {{ String(history.length).padStart(2, '0') }}</strong></div>
            <button type="button" :disabled="stateBusy" title="重新加载本地归档" @click="loadHistory">↻</button>
          </header>

          <div v-if="historyLoading" class="history-loading">
            <i v-for="n in 3" :key="n"></i>
            <span>READING LOCAL INDEX…</span>
          </div>
          <div v-else-if="history.length === 0" class="history-empty">
            <b>∅</b>
            <span>NO LOCAL RECORDS</span>
            <p>第一次抓取普通条目后，归档会出现在这里。</p>
          </div>
          <ol v-else class="history-list">
            <li v-for="(artifact, index) in history" :key="artifact.id">
              <button
                type="button"
                :class="{ selected: artifact.id === selectedId }"
                :disabled="stateBusy"
                @click="openArtifact(artifact.id)"
              >
                <span class="history-index">{{ String(index + 1).padStart(2, '0') }}</span>
                <span class="history-copy">
                  <strong>{{ artifact.title }}</strong>
                  <small>{{ new Date(artifact.updated_at).toLocaleString('zh-CN') }}</small>
                </span>
                <span class="history-count">{{ artifact.character_count.toLocaleString('zh-CN') }}<small>CHAR</small></span>
              </button>
            </li>
          </ol>
        </section>
      </aside>

      <article class="preview-workspace">
        <div v-if="opening || refining" class="preview-loader">
          <i></i><span>{{ refining ? 'AI REFINING ARCHIVE' : 'OPENING ARCHIVE' }}</span>
        </div>

        <template v-if="preview">
          <header class="preview-header">
            <div class="preview-kicker">
              <span :class="['state-badge', preview.kind]">
                {{ preview.kind === 'saved' ? '● SAVED LOCALLY' : '△ DISAMBIGUATION / NOT SAVED' }}
              </span>
              <span v-if="preview.kind === 'disambiguation'" class="warning-copy">
                名称指向消歧义页，请从预览中选择更精确的条目名重新抓取。
              </span>
            </div>
            <div class="title-row">
              <div>
                <span>PREVIEW / MARKDOWN</span>
                <h2>{{ preview.title }}</h2>
                <a :href="preview.sourceUrl" target="_blank" rel="noreferrer">SOURCE ↗ {{ preview.sourceUrl }}</a>
              </div>
              <div class="preview-actions">
                <button type="button" :disabled="!canUseSavedActions || stateBusy" @click="refreshSelected">
                  <i>↻</i><span>{{ fetching ? 'REFRESHING' : 'REFRESH' }}</span>
                </button>
                <button type="button" :disabled="!canUseSavedActions || stateBusy" @click="refineSelected">
                  <i>✦</i><span>{{ refining ? 'REFINING' : 'AI REFINE' }}</span>
                </button>
                <button type="button" :disabled="!canUseSavedActions || downloading || stateBusy" @click="downloadSelected">
                  <i>↓</i><span>{{ downloading ? 'PREPARING' : 'DOWNLOAD .MD' }}</span>
                </button>
                <button class="danger" type="button" :disabled="!canUseSavedActions || deleteUnavailable" @click="deleteSelected">
                  <i>×</i><span>{{ deleting ? 'DELETING' : 'DELETE' }}</span>
                </button>
              </div>
            </div>
          </header>

          <div class="document-shell">
            <div class="document-rule"><span>BEGIN CLEAN ARTICLE</span><i></i><b>{{ preview.markdown.length.toLocaleString('zh-CN') }} RAW CHAR</b></div>
            <div class="markdown-body" v-html="renderMarkdown(preview.markdown)"></div>
          </div>
        </template>

        <div v-else class="preview-empty">
          <div class="empty-mark" aria-hidden="true"><span>M</span><i></i></div>
          <p>WORKSPACE / EMPTY</p>
          <h2>抓取一页，<br>留下可读的本地副本。</h2>
          <span>普通页面会保存；消歧义页面只作临时预览。</span>
        </div>
      </article>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@500;600;700&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');

*{box-sizing:border-box}.archive-page{--ink:#11110f;--paper:#efede6;--paper-2:#d9d7cf;--acid:#d9ff36;--muted:#77746d;--rule:#34342f;--danger:#ff684c;position:relative;min-height:100vh;overflow-x:hidden;background:var(--ink);color:var(--paper);padding:0 clamp(18px,4.5vw,70px) 64px;font-family:Manrope,sans-serif}.grain{position:fixed;z-index:10;inset:0;pointer-events:none;opacity:.1;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.24'/%3E%3C/svg%3E")}.archive-nav{height:74px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--rule)}button{font:inherit}.archive-nav button{border:0;background:transparent;color:inherit;cursor:pointer}.wordmark{display:flex;align-items:center;gap:9px;font:700 11px 'DM Mono';letter-spacing:.14em}.wordmark i{width:17px;height:17px;border:1px solid var(--acid);position:relative}.wordmark i:after{content:'';position:absolute;width:5px;height:5px;right:-3px;bottom:-3px;background:var(--acid)}.wordmark span{color:#686760;font-weight:400}.nav-meta{display:flex;align-items:center;gap:25px;color:#696861;font:8px 'DM Mono';letter-spacing:.11em}.nav-meta button{padding:9px 0}.nav-meta button:hover{color:var(--acid)}.archive-heading{display:grid;grid-template-columns:1fr auto;align-items:end;gap:40px;padding:47px 0 35px}.archive-heading p{margin:0 0 12px;color:var(--acid);font:9px 'DM Mono';letter-spacing:.17em}.archive-heading h1{margin:0;font:700 clamp(51px,7vw,96px)/.73 Manrope;letter-spacing:-.085em}.archive-heading h1 em{color:#6c6a63;font:600 italic .85em 'Playfair Display';letter-spacing:-.055em}.archive-heading aside{display:grid;gap:8px;min-width:290px;padding-bottom:3px;border-left:1px solid var(--rule);padding-left:22px;color:#77746d;font:8px 'DM Mono';letter-spacing:.08em}.archive-heading aside b{color:var(--paper);font:600 11px Manrope;letter-spacing:0}.user-stamp{color:var(--acid);overflow:hidden;text-overflow:ellipsis;max-width:310px}.workbench{display:grid;grid-template-columns:minmax(290px,370px) minmax(0,1fr);min-height:690px;max-width:1550px;margin:auto;border:1px solid #41403a;background:#41403a;gap:1px}.control-rail{min-width:0;background:#1a1a18}.fetch-form{padding:25px;border-bottom:1px solid #373732}.fetch-form label{display:block;margin-bottom:14px;color:#a5a299;font:8px 'DM Mono';letter-spacing:.15em}.input-line{display:flex;align-items:center;gap:10px;border-bottom:1px solid #77766e}.input-line>span{color:var(--acid);font:12px 'DM Mono'}.input-line input{width:100%;height:47px;border:0;outline:0;background:transparent;color:var(--paper);font:500 17px Manrope}.input-line input::placeholder{color:#575750}.input-line:focus-within{border-color:var(--acid)}.fetch-button{width:100%;height:50px;margin-top:18px;display:flex;align-items:center;justify-content:space-between;border:1px solid var(--acid);background:var(--acid);color:#11110f;padding:0 15px;cursor:pointer;font:500 9px 'DM Mono';letter-spacing:.12em;transition:background .18s,color .18s}.fetch-button:hover:not(:disabled){background:transparent;color:var(--acid)}.fetch-button b{font-size:16px}.fetch-button:disabled{cursor:not-allowed;filter:grayscale(1);opacity:.35}.fetch-progress{height:3px;margin-top:9px;overflow:hidden;background:#32332d}.fetch-progress i{display:block;width:40%;height:100%;background:var(--acid);animation:scan 1s ease-in-out infinite}.feedback{min-height:73px;padding:14px 25px;border-bottom:1px solid #373732}.feedback p{display:grid;grid-template-columns:52px 1fr;gap:9px;margin:0;color:#817f77;font:8px/1.6 'DM Mono';letter-spacing:.04em}.feedback b{color:var(--acid);font-weight:500}.feedback .error-message,.feedback .error-message b{color:var(--danger)}.history-panel>header{height:66px;display:flex;align-items:center;justify-content:space-between;padding:0 20px 0 25px;border-bottom:1px solid #373732}.history-panel>header div{display:grid;gap:4px}.history-panel>header span{color:#65645e;font:7px 'DM Mono';letter-spacing:.13em}.history-panel>header strong{font:500 10px 'DM Mono';letter-spacing:.12em}.history-panel>header button{width:31px;height:31px;border:1px solid #41413b;background:transparent;color:#a7a49c;cursor:pointer}.history-panel>header button:hover:not(:disabled){border-color:var(--acid);color:var(--acid)}.history-list{list-style:none;padding:0;margin:0;max-height:480px;overflow:auto}.history-list li{border-bottom:1px solid #30302c}.history-list button{width:100%;display:grid;grid-template-columns:28px minmax(0,1fr) auto;align-items:center;gap:8px;padding:17px 18px 17px 22px;border:0;border-left:3px solid transparent;background:transparent;color:inherit;text-align:left;cursor:pointer}.history-list button:hover{background:#21211e}.history-list button.selected{border-left-color:var(--acid);background:#292a24}.history-index{color:#5d5c56;font:8px 'DM Mono'}.history-copy{min-width:0;display:grid;gap:6px}.history-copy strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}.history-copy small{color:#69675f;font:7px 'DM Mono';letter-spacing:.04em}.history-count{display:grid;justify-items:end;color:#bbb8ae;font:9px 'DM Mono'}.history-count small{font-size:6px;color:#5d5c56}.history-loading,.history-empty{min-height:250px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:30px;text-align:center}.history-loading i{display:block;width:86%;height:1px;margin:9px;background:#383832;position:relative;overflow:hidden}.history-loading i:after{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent,var(--acid),transparent);animation:scan 1.4s ease-in-out infinite}.history-loading span,.history-empty span{margin-top:19px;color:#67665f;font:7px 'DM Mono';letter-spacing:.15em}.history-empty b{color:#4f4f49;font:400 52px 'DM Mono'}.history-empty p{max-width:190px;color:#5f5e58;font-size:9px;line-height:1.65}.preview-workspace{position:relative;min-width:0;background:var(--paper);color:var(--ink)}.preview-loader{position:absolute;z-index:3;top:14px;right:17px;display:flex;align-items:center;gap:7px;padding:7px 9px;background:var(--ink);color:var(--acid);font:7px 'DM Mono';letter-spacing:.1em}.preview-loader i{width:5px;height:5px;background:var(--acid);animation:blink .8s steps(1) infinite}.preview-header{padding:27px clamp(24px,4vw,58px) 24px;background:var(--paper-2);border-bottom:1px solid #b7b4aa}.preview-kicker{min-height:29px;display:flex;align-items:center;gap:13px}.state-badge{display:inline-flex;padding:6px 9px;border:1px solid #8f8e85;font:7px 'DM Mono';letter-spacing:.11em}.state-badge.saved{background:var(--ink);border-color:var(--ink);color:var(--acid)}.state-badge.disambiguation{background:var(--danger);border-color:var(--danger);color:var(--ink)}.warning-copy{font-size:9px;color:#5f3a31}.title-row{display:flex;align-items:flex-end;justify-content:space-between;gap:30px;margin-top:25px}.title-row>div:first-child{min-width:0}.title-row>div>span{color:#77746c;font:7px 'DM Mono';letter-spacing:.15em}.title-row h2{margin:7px 0 9px;font:700 clamp(32px,4vw,58px)/.95 Manrope;letter-spacing:-.065em;overflow-wrap:anywhere}.title-row a{display:block;max-width:680px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#77746c;font:7px 'DM Mono';letter-spacing:.04em}.title-row a:hover{color:#111}.preview-actions{display:flex;flex-shrink:0;gap:1px;background:#aaa79e;border:1px solid #aaa79e}.preview-actions button{min-width:76px;height:58px;display:grid;place-content:center;gap:3px;border:0;background:var(--paper);cursor:pointer}.preview-actions button:hover:not(:disabled){background:var(--acid)}.preview-actions button:disabled{cursor:not-allowed;opacity:.35}.preview-actions i{font:400 17px 'DM Mono';font-style:normal}.preview-actions span{font:7px 'DM Mono';letter-spacing:.08em}.preview-actions .danger:hover:not(:disabled){background:var(--danger)}.document-shell{padding:21px clamp(24px,4vw,58px) 65px}.document-rule{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:13px;color:#77746c;font:6px 'DM Mono';letter-spacing:.13em}.document-rule i{height:1px;background:#c4c1b8}.markdown-body{max-width:820px;margin:45px auto 0;color:#2b2a27;font-size:14px;line-height:1.85;overflow-wrap:anywhere}.markdown-body :deep(h1),.markdown-body :deep(h2),.markdown-body :deep(h3){font-family:Manrope,sans-serif;letter-spacing:-.035em;line-height:1.15}.markdown-body :deep(h1){margin:0 0 30px;font-size:36px}.markdown-body :deep(h2){margin:42px 0 17px;padding-bottom:10px;border-bottom:1px solid #bdbab1;font-size:25px}.markdown-body :deep(h3){margin:30px 0 13px;font-size:18px}.markdown-body :deep(a){color:#475300;text-decoration-color:#9bae1d}.markdown-body :deep(blockquote){margin:24px 0;padding:15px 20px;border-left:4px solid var(--acid);background:#e4e2da}.markdown-body :deep(code){padding:2px 5px;background:#d9d7cf;font:12px 'DM Mono'}.markdown-body :deep(pre){overflow:auto;padding:18px;background:#181816;color:#e9e7de}.markdown-body :deep(pre code){padding:0;background:transparent;color:inherit}.markdown-body :deep(table){width:100%;border-collapse:collapse;font-size:12px}.markdown-body :deep(th),.markdown-body :deep(td){padding:9px;border:1px solid #bdbab1;text-align:left}.markdown-body :deep(th){background:#d9d7cf}.markdown-body :deep(img){max-width:100%}.preview-empty{height:100%;min-height:688px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:50px;text-align:center;background:linear-gradient(135deg,transparent 49.8%,#dbd9d0 50%,transparent 50.2%)}.empty-mark{position:relative;width:100px;height:100px;display:grid;place-items:center;border:1px solid #aaa79e;transform:rotate(45deg)}.empty-mark span{font:700 44px Manrope;transform:rotate(-45deg)}.empty-mark i{position:absolute;right:-7px;bottom:-7px;width:14px;height:14px;background:var(--acid)}.preview-empty>p{margin:36px 0 13px;color:#77746c;font:7px 'DM Mono';letter-spacing:.16em}.preview-empty h2{margin:0;font:600 clamp(27px,3.4vw,46px)/1.05 'Playfair Display';letter-spacing:-.04em}.preview-empty>span{margin-top:18px;color:#77746c;font-size:9px}@keyframes scan{0%{transform:translateX(-110%)}100%{transform:translateX(260%)}}@keyframes blink{50%{opacity:0}}@media(max-width:950px){.workbench{grid-template-columns:300px minmax(0,1fr)}.title-row{align-items:flex-start;flex-direction:column}.preview-actions{width:100%}.preview-actions button{flex:1}.archive-heading aside{min-width:0}}@media(max-width:740px){.archive-page{padding-inline:14px}.nav-meta>span{display:none}.archive-heading{grid-template-columns:1fr;padding-top:38px}.archive-heading aside{border-left:0;border-top:1px solid var(--rule);padding:15px 0 0}.workbench{grid-template-columns:1fr}.control-rail{min-height:auto}.history-list{max-height:310px}.preview-workspace{min-height:620px}.preview-empty{min-height:620px}.preview-header{padding-inline:20px}.document-shell{padding-inline:20px}.preview-kicker{align-items:flex-start;flex-direction:column}.warning-copy{line-height:1.55}}@media(max-width:430px){.archive-nav{height:64px}.wordmark span{display:none}.archive-heading h1{font-size:55px}.fetch-form,.feedback{padding-inline:18px}.history-list button{padding-inline:15px}.title-row h2{font-size:31px}.preview-actions button{min-width:0}.document-rule b{display:none}.document-rule{grid-template-columns:auto 1fr}.markdown-body{margin-top:30px;font-size:13px}}@media(prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important}}
@media(min-width:741px){.workbench{height:max(520px,calc(100dvh - 350px));min-height:0;max-height:none}.control-rail{display:flex;min-height:0;flex-direction:column;overflow:hidden}.fetch-form,.feedback{flex:0 0 auto}.history-panel{display:flex;min-height:0;flex:1;flex-direction:column}.history-panel>header{flex:0 0 auto}.history-list{min-height:0;max-height:none;flex:1;overflow-y:auto}.history-loading,.history-empty{min-height:0;flex:1}.preview-workspace{display:flex;min-height:0;flex-direction:column;overflow:hidden}.preview-header{flex:0 0 auto}.document-shell{min-height:0;flex:1;overflow-y:auto}.preview-empty{min-height:0;flex:1}}
@media(max-width:740px){.workbench{height:auto;min-height:0;max-height:none}.control-rail{display:block;overflow:visible}.history-panel{display:block}.history-list{max-height:none;overflow:visible}.preview-workspace{display:block;min-height:0;overflow:visible}.document-shell{overflow:visible}}
</style>

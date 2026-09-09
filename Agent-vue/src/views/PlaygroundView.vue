<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useWorkspaceStore } from '@/stores/workspace'
import { usePlaygroundStore } from '@/stores/playground'
import { useWorkspaceRail } from '@/composables/useWorkspaceRail'
import { assetContentUrl } from '@/utils/chat-attachments'
import type { PlaygroundMessage } from '@/api/playground-types'
import { synthesizeTts } from '@/api/toolbox-tts'
import { PlaygroundTtsPlayer, type PlaygroundTtsStatus } from '@/playground/tts-player'
import PlaygroundNarrative from '@/components/playground/PlaygroundNarrative.vue'
import PlaygroundSidebar from '@/components/playground/PlaygroundSidebar.vue'
import PlaygroundStatusPanel from '@/components/playground/PlaygroundStatusPanel.vue'


const workspace = useWorkspaceStore()
const store = usePlaygroundStore()
const router = useRouter()
const userId = computed(() => workspace.userId)
const { railCollapsed, toggleRail } = useWorkspaceRail(
  undefined,
  'agentbi.playground-rail-collapsed',
)
const input = ref('')
const scrollHost = ref<HTMLElement | null>(null)
const summaryOpen = ref(false)
const summaryEditing = ref(false)
const summaryDraft = ref('')
const ttsStates = ref<Record<string, { status: PlaygroundTtsStatus; error?: string }>>({})
const ttsPlayer = new PlaygroundTtsPlayer({
  createObjectURL: (blob) => URL.createObjectURL(blob),
  revokeObjectURL: (url) => URL.revokeObjectURL(url),
  createAudio: (url) => new Audio(url),
  onChange: (messageId, status, error) => {
    ttsStates.value = {
      ...ttsStates.value,
      [messageId]: { status, ...(error ? { error } : {}) },
    }
  },
})
const sceneStyle = computed(() => {
  const id = store.activeProfile?.background_attachment_id
  return id
    ? { '--scene-background': `url("${assetContentUrl(id, userId.value)}")` }
    : {}
})
const profileAvatar = computed(() => {
  const id = store.activeProfile?.avatar_attachment_id
  return id ? assetContentUrl(id, userId.value) : ''
})
const latestState = computed(() => {
  for (let index = store.messages.length - 1; index >= 0; index -= 1) {
    const snapshot = store.messages[index]?.metadata.state_snapshot
    if (snapshot) return snapshot
  }
  return null
})
const showStatus = computed(
  () => Boolean(store.activeProfile?.settings.state.enabled && latestState.value),
)

async function send() {
  const content = input.value.trim()
  if (!content) return
  input.value = ''
  await store.send(userId.value, content)
}

function keydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    void send()
  }
}

function editMessage(message: PlaygroundMessage) {
  const content = window.prompt(
    message.role === 'assistant' ? '编辑开场消息' : '编辑用户消息',
    message.content,
  )
  if (content === null) return
  if (message.role === 'assistant') void store.editOpening(message.id, content, userId.value)
  else void store.edit(userId.value, message.id, content)
}

function showSummary(editing = false) {
  summaryDraft.value = store.summary?.content || ''
  summaryEditing.value = editing
  summaryOpen.value = true
}

async function saveSummary() {
  await store.saveSummary(summaryDraft.value, userId.value)
  summaryEditing.value = false
}

async function playMessage(message: PlaygroundMessage) {
  const profile = store.activeProfile
  const settings = profile?.settings.tts
  if (!profile || profile.profile_type !== 'character' || !settings?.enabled) return
  if (!settings.provider || !settings.model || !settings.voice_id) {
    ttsStates.value = {
      ...ttsStates.value,
      [message.id]: { status: 'error', error: '请先在角色资料中选择语音供应商、模型和音色。' },
    }
    return
  }
  try {
    await ttsPlayer.synthesizeAndPlay(message.id, async () => {
      const response = await synthesizeTts({
        user_id: userId.value,
        provider: settings.provider!,
        model: settings.model!,
        voice_id: settings.voice_id!,
        text: message.content,
        audio_format: settings.audio_format,
        parameters: settings.parameters,
      })
      return response.blob
    })
  } catch {
    // The player exposes synthesis/playback errors beside this message.
  }
}

watch(
  () => [store.messages.length, store.messages.at(-1)?.content],
  async () => {
    await nextTick()
    if (scrollHost.value) scrollHost.value.scrollTop = scrollHost.value.scrollHeight
  },
)

watch(
  () => [store.activeProfileId, store.activeConversationId],
  ([profileId, conversationId], [previousProfileId, previousConversationId]) => {
    if (profileId === previousProfileId && conversationId === previousConversationId) return
    ttsPlayer.stopAndClear()
    ttsStates.value = {}
  },
)

let generatedConversationId = ''
watch(
  () => [store.activeConversationId, store.activeGenerating] as const,
  async ([conversationId, generating], [previousConversationId, wasGenerating]) => {
    if (generating) generatedConversationId = conversationId
    if (
      !wasGenerating || generating || conversationId !== previousConversationId ||
      generatedConversationId !== conversationId
    ) return
    generatedConversationId = ''
    await nextTick()
    const profile = store.activeProfile
    if (
      !profile || profile.profile_type !== 'character' ||
      !profile.settings.tts.enabled || !profile.settings.tts.auto_play
    ) return
    const message = [...store.messages].reverse().find(
      (item) => item.role === 'assistant' && item.status === 'complete' && item.content.trim(),
    )
    if (message) void playMessage(message)
  },
)

onMounted(() => void store.load(userId.value))
onBeforeUnmount(() => ttsPlayer.stopAndClear())
</script>

<template>
  <main class="playground-view" :class="{ 'rail-collapsed': railCollapsed }">
    <PlaygroundSidebar :user-id="userId" :collapsed="railCollapsed" @toggle="toggleRail" />
    <section class="scene" :style="sceneStyle">
      <div class="scene-background"></div><div class="scene-scrim"></div><div class="scene-grain"></div>
      <header class="scene-topbar">
        <div><span>PLAYGROUND / {{ store.mode === 'character' ? 'CHARACTER' : 'WORLD' }}</span><strong>{{ store.activeProfile?.name || '未选择资料' }}</strong></div>
        <div v-if="store.activeConversation"><small>{{ store.activeConversation.title }}</small><i v-if="store.activeGenerating"></i></div>
        <button @click="router.push('/playground/manage')">资料管理 ↗</button>
      </header>

      <div v-if="store.activeProfile && store.activeConversation" ref="scrollHost" class="scene-scroll" :class="{ 'with-status': showStatus }">
        <div v-if="store.activeProfile.profile_type === 'character' && profileAvatar" class="scene-portrait"><img :src="profileAvatar" alt="" /><i></i></div>
        <PlaygroundNarrative :messages="store.messages" :profile="store.activeProfile" :summary="store.summary" :generating="store.activeGenerating" :tts-states="ttsStates" @retry="store.retry(userId, $event)" @edit="editMessage" @branch="store.branch($event, userId)" @version="store.selectVersion($event, userId)" @play="playMessage" @option="store.chooseOption($event, userId)" @summary-view="showSummary(false)" @summary-edit="showSummary(true)" @summary-refresh="store.refreshSummary(userId)" />
      </div>

      <div v-else class="scene-empty">
        <span>{{ store.activeProfile ? 'NO ACTIVE STORY' : 'NO ROLE SELECTED' }}</span><h1>{{ store.activeProfile ? '让故事，发生在此刻。' : '先定义一个人，或一整个世界。' }}</h1><p>{{ store.activeProfile ? '新会话会从资料中保存的开场消息开始。' : 'Playground 使用独立的角色、世界书和会话列表。' }}</p><button v-if="store.activeProfile" @click="store.createConversation(userId)">开始新故事 <b>↗</b></button><button v-else @click="router.push('/playground/manage')">创建角色或世界 <b>↗</b></button>
      </div>

      <PlaygroundStatusPanel v-if="showStatus && store.activeProfile && latestState" class="scene-status" :settings="store.activeProfile.settings.state" :snapshot="latestState" />

      <form v-if="store.activeProfile && store.activeConversation" class="story-composer" @submit.prevent="send">
        <div class="composer-meta"><span>{{ store.activeProfile.profile_type === 'character' ? 'YOUR NEXT ACTION' : 'WRITE INTO THE WORLD' }}</span><b v-if="store.activeGenerating">生成中 · 可切换其他会话</b><b v-else>ENTER 发送 · SHIFT+ENTER 换行</b></div>
        <textarea v-model="input" rows="2" :disabled="store.activeGenerating" :placeholder="store.activeProfile.profile_type === 'character' ? '回应角色，或描述你的行动…' : '描述接下来发生的事…'" @keydown="keydown"></textarea>
        <button v-if="store.activeGenerating" type="button" class="stop" @click="store.stop()">停止</button><button v-else type="submit" :disabled="!input.trim()">推进 <i>↗</i></button>
      </form>

      <Transition name="sync"><div v-if="store.syncMessage" class="sync-indicator"><i></i><span>{{ store.syncMessage }}</span></div></Transition>
      <p v-if="store.error" class="scene-error">{{ store.error }}</p>
    </section>

    <div v-if="summaryOpen" class="summary-dialog" @click.self="summaryOpen = false">
      <section><header><div><span>CONVERSATION SUMMARY</span><h2>长会话精炼记录</h2></div><button @click="summaryOpen = false">×</button></header><textarea v-if="summaryEditing" v-model="summaryDraft" rows="20"></textarea><div v-else class="summary-text">{{ summaryDraft || '尚未生成总结。' }}</div><footer><span>{{ store.summary?.status === 'running' ? '后台正在更新' : store.summary?.updated_at ? `更新于 ${new Date(store.summary.updated_at).toLocaleString()}` : '尚未更新' }}</span><button v-if="summaryEditing" @click="saveSummary">保存总结</button><button v-else @click="summaryEditing = true">编辑</button><button @click="store.refreshSummary(userId)">重新生成</button></footer></section>
    </div>
  </main>
</template>

<style scoped>
.playground-view{--scene-acid:#d7ff3f;display:grid;grid-template-columns:292px minmax(0,1fr);height:100vh;overflow:hidden;background:#0d100e;color:#e4e9e4;font-family:var(--font-sans);transition:grid-template-columns .25s}.playground-view.rail-collapsed{grid-template-columns:72px minmax(0,1fr)}.scene{--scene-background:none;position:relative;min-width:0;height:100vh;overflow:hidden;background:#171b18}.scene-background,.scene-scrim,.scene-grain{position:absolute;inset:0;pointer-events:none}.scene-background{background-image:var(--scene-background);background-size:cover;background-position:center;filter:saturate(.72) contrast(1.08);transform:scale(1.015)}.scene-scrim{background:linear-gradient(90deg,rgba(8,11,9,.93) 0%,rgba(8,11,9,.74) 42%,rgba(8,11,9,.68) 70%,rgba(8,11,9,.86) 100%),linear-gradient(0deg,rgba(7,9,8,.94),transparent 35%,rgba(7,9,8,.52))}.scene-grain{opacity:.11;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.88' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.5'/%3E%3C/svg%3E")}.scene-topbar{position:absolute;z-index:5;left:0;right:0;top:0;height:72px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 25px;border-bottom:1px solid rgba(255,255,255,.1);background:linear-gradient(#0b0e0ce8,#0b0e0ca8,transparent)}.scene-topbar>div:first-child{display:grid;gap:4px}.scene-topbar span{color:var(--scene-acid);font:6px var(--font-mono);letter-spacing:.15em}.scene-topbar strong{font-size:11px}.scene-topbar>div:nth-child(2){display:flex;align-items:center;gap:9px;color:#7b847d;font:7px var(--font-mono)}.scene-topbar>div:nth-child(2) i{width:5px;height:5px;border-radius:50%;background:var(--scene-acid);box-shadow:0 0 8px var(--scene-acid);animation:pulse 1s infinite}.scene-topbar>button{justify-self:end;border:0;background:none;color:#737c75;font:7px var(--font-mono);cursor:pointer}.scene-scroll{position:absolute;z-index:2;inset:72px 0 0;overflow-y:auto;scroll-behavior:smooth;scrollbar-width:thin;scrollbar-color:#3e4740 transparent}.scene-scroll.with-status{padding-right:310px}.scene-portrait{position:fixed;z-index:0;right:44px;top:105px;width:120px;height:120px;opacity:.82}.with-status .scene-portrait{right:335px}.scene-portrait img{width:100%;height:100%;object-fit:cover;filter:saturate(.75)}.scene-portrait i{position:absolute;inset:-8px;border:1px solid rgba(215,255,63,.3);clip-path:polygon(0 0,35% 0,35% 1px,1px 1px,1px 35%,0 35%,0 0,100% 0,100% 35%,99% 35%,99% 1px,65% 1px,65% 0,100% 0,100% 100%,65% 100%,65% 99%,99% 99%,99% 65%,100% 65%,100% 100%,0 100%,0 65%,1px 65%,1px 99%,35% 99%,35% 100%,0 100%)}.scene-status{position:absolute;z-index:6;right:18px;top:90px}.story-composer{position:absolute;z-index:8;left:50%;bottom:22px;width:min(760px,calc(100% - 70px));transform:translateX(-50%);display:grid;grid-template-columns:1fr auto;border:1px solid rgba(255,255,255,.17);background:rgba(12,15,13,.88);backdrop-filter:blur(18px);box-shadow:0 25px 70px #0009}.with-status~.story-composer{width:min(700px,calc(100% - 380px));left:calc(50% - 140px)}.composer-meta{grid-column:1/-1;display:flex;justify-content:space-between;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.08)}.composer-meta span{color:var(--scene-acid);font:6px var(--font-mono);letter-spacing:.13em}.composer-meta b{color:#59625b;font:6px var(--font-mono);font-weight:400}.story-composer textarea{resize:none;border:0;outline:0;background:transparent;color:#e3e8e3;padding:14px;font:11px/1.6 var(--font-sans)}.story-composer>button{min-width:88px;border:0;border-left:1px solid rgba(255,255,255,.1);background:var(--scene-acid);color:#11140f;font:700 8px var(--font-mono);cursor:pointer}.story-composer>button i{display:block;margin-top:4px;font-size:14px;font-style:normal}.story-composer>button.stop{background:#d46f5e;color:#160e0c}.story-composer>button:disabled{opacity:.25}.scene-empty{position:absolute;z-index:3;left:50%;top:50%;width:min(640px,calc(100% - 40px));transform:translate(-50%,-50%);text-align:center}.scene-empty>span{color:var(--scene-acid);font:7px var(--font-mono);letter-spacing:.18em}.scene-empty h1{margin:17px 0 10px;font:500 clamp(38px,5vw,68px)/.95 'Playfair Display',serif;letter-spacing:-.06em}.scene-empty p{color:#758078;font-size:10px}.scene-empty button{min-width:210px;margin-top:24px;border:1px solid var(--scene-acid);background:var(--scene-acid);color:#11140f;padding:14px;text-align:left;font:700 8px var(--font-mono);cursor:pointer}.scene-empty button b{float:right;font-size:14px}.sync-indicator{position:absolute;z-index:20;left:50%;top:86px;display:flex;align-items:center;gap:9px;transform:translateX(-50%);padding:9px 13px;border:1px solid rgba(255,255,255,.12);background:#111512e8;color:#828c84;font:7px var(--font-mono)}.sync-indicator i{width:11px;height:11px;border:1px solid #49524b;border-right-color:var(--scene-acid);border-radius:50%;animation:spin .7s linear infinite}.scene-error{position:absolute;z-index:20;left:50%;bottom:145px;transform:translateX(-50%);margin:0;padding:8px 12px;border-left:2px solid #ff7c68;background:#231613;color:#ff9b89;font:8px var(--font-mono)}.summary-dialog{position:fixed;z-index:50;inset:0;display:grid;place-items:center;padding:20px;background:#080a08c9;backdrop-filter:blur(10px)}.summary-dialog>section{width:min(760px,100%);max-height:85vh;overflow:auto;border:1px solid #414942;background:#151916;color:#e5eae5}.summary-dialog header{display:flex;justify-content:space-between;padding:22px;border-bottom:1px solid #343b36}.summary-dialog header span{color:var(--scene-acid);font:6px var(--font-mono);letter-spacing:.15em}.summary-dialog h2{margin:7px 0 0;font-size:20px}.summary-dialog header button{border:0;background:none;color:#737c75;font-size:20px;cursor:pointer}.summary-dialog textarea,.summary-text{box-sizing:border-box;width:100%;min-height:400px;border:0;outline:0;background:#101310;color:#cdd4ce;padding:24px;white-space:pre-wrap;font:11px/1.8 var(--font-mono)}.summary-dialog footer{display:flex;align-items:center;justify-content:flex-end;gap:7px;padding:12px 18px;border-top:1px solid #343b36}.summary-dialog footer span{margin-right:auto;color:#626b64;font:6px var(--font-mono)}.summary-dialog footer button{border:1px solid #404842;background:none;color:#929c94;padding:8px 10px;font:7px var(--font-mono);cursor:pointer}.summary-dialog footer button:hover{border-color:var(--scene-acid);color:var(--scene-acid)}.sync-enter-active,.sync-leave-active{transition:.2s}.sync-enter-from,.sync-leave-to{opacity:0;transform:translate(-50%,-8px)}@keyframes spin{to{transform:rotate(360deg)}}@keyframes pulse{50%{opacity:.3}}@media(max-width:1100px){.scene-scroll.with-status{padding-right:0;padding-bottom:300px}.scene-status{left:20px;right:20px;top:auto;bottom:145px}.with-status~.story-composer{left:50%;width:min(760px,calc(100% - 70px))}.with-status .scene-portrait{right:35px}}@media(max-width:760px){.playground-view,.playground-view.rail-collapsed{grid-template-columns:58px minmax(0,1fr)}.scene-topbar{grid-template-columns:1fr auto;padding:0 13px}.scene-topbar>div:nth-child(2){display:none}.scene-scroll.with-status{padding-bottom:340px}.scene-portrait{right:18px;width:78px;height:78px}.story-composer,.with-status~.story-composer{left:50%;width:calc(100% - 20px);bottom:10px}.composer-meta b{display:none}.scene-status{left:10px;right:10px;bottom:125px}.scene-topbar>button{font-size:0}.scene-topbar>button:after{content:'↗';font-size:10px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation-duration:.01ms!important;transition-duration:.01ms!important}}
</style>
